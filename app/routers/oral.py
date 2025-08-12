from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app import models
from sqlalchemy import select
from typing import Optional, Dict, Any
import os
import magic
from pathlib import Path
from app.database import get_db
from app.auth.router import get_current_user
from app.models_story import OralHistory
from app.schemas_story import OralHistoryOut
from app.services.storage import save_upload
from app.tasks.oral_worker import run_oral_processing_in_background
import logging
import time
from fastapi.security import HTTPBearer

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

router = APIRouter(
    prefix="/oral-histories",
    tags=["oral-histories"],
    responses={
        429: {"description": "Too many requests"},
        413: {"description": "File too large"},
        415: {"description": "Unsupported media type"}
    }
)

# Allowed MIME types with their common file extensions
ALLOWED_AUDIO_TYPES = {
    'audio/wav': ['.wav'],
    'audio/mpeg': ['.mp3', '.mpga'],
    'audio/ogg': ['.ogg', '.oga'],
    'audio/webm': ['.webm'],
    'audio/x-wav': ['.wav'],
    'audio/x-m4a': ['.m4a'],
    'audio/x-aac': ['.aac']
}

# Maximum file size (100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024
# Rate limiting (requests per minute per IP)
RATE_LIMIT = 10
RATE_LIMIT_WINDOW = 60  # seconds

# In-memory rate limiting (replace with Redis in production)
rate_limits: Dict[str, Dict[str, Any]] = {}

def check_rate_limit(request: Request) -> None:
    """Check if the request is within rate limits."""
    client_ip = request.client.host
    current_time = time.time()
    
    if client_ip not in rate_limits:
        rate_limits[client_ip] = {
            'count': 1,
            'reset_time': current_time + RATE_LIMIT_WINDOW
        }
    else:
        # Reset counter if window has passed
        if current_time > rate_limits[client_ip]['reset_time']:
            rate_limits[client_ip] = {
                'count': 1,
                'reset_time': current_time + RATE_LIMIT_WINDOW
            }
        else:
            rate_limits[client_ip]['count'] += 1
    
    # Check if rate limit exceeded
    if rate_limits[client_ip]['count'] > RATE_LIMIT:
        remaining = int(rate_limits[client_ip]['reset_time'] - current_time)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Too many requests",
                "retry_after": remaining,
                "limit": RATE_LIMIT,
                "window_seconds": RATE_LIMIT_WINDOW
            },
            headers={"Retry-After": str(remaining)}
        )

def validate_file_type(file: UploadFile) -> None:
    """Validate the file type using python-magic."""
    try:
        # Read first 2048 bytes for magic number detection
        file_content = file.file.read(2048)
        file.file.seek(0)  # Reset file pointer
        
        # Get MIME type using python-magic
        mime = magic.Magic(mime=True)
        detected_type = mime.from_buffer(file_content)
        
        # Check if detected type is in allowed types
        if detected_type not in ALLOWED_AUDIO_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"File type {detected_type} is not supported. Supported types: {', '.join(ALLOWED_AUDIO_TYPES.keys())}"
            )
            
        # Check file extension matches detected type
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_AUDIO_TYPES.get(detected_type, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension {file_ext} does not match detected type {detected_type}"
            )
            
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Error validating file type: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not validate file type"
        ) from e

@router.post(
    "/upload", 
    response_model=OralHistoryOut,
    status_code=status.HTTP_201_CREATED,
    description="Upload an audio file to be processed as an oral history. The file will be processed in the background.",
    responses={
        201: {"description": "Successfully uploaded and processing started"},
        400: {"description": "Invalid file or request data"},
        401: {"description": "Not authenticated"},
        413: {"description": "File too large"},
        415: {"description": "Unsupported media type"},
        429: {"description": "Rate limit exceeded"}
    }
)
async def upload_oral_history(
    request: Request,
    background_tasks: BackgroundTasks,
    title: str = Form(..., description="Title for the oral history", min_length=1, max_length=255),
    story_id: Optional[int] = Form(None, description="Optional ID of the story this oral history is associated with"),
    file: UploadFile = File(..., description="Audio file to upload (MP3, WAV, OGG, etc.)"),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Upload an audio file to be processed as an oral history.
    
    The file will be processed in the background and should be in one of the supported formats:
    - WAV, MP3, OGG, WebM, M4A, AAC
    
    Maximum file size is 100MB.
    """
    # Rate limiting
    check_rate_limit(request)
    
    # Validate file size
    file.file.seek(0, 2)  # Move to end of file
    file_size = file.file.tell()
    file.file.seek(0)  # Reset file pointer
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024 * 1024):.1f}MB"
        )
    
    # Validate file type using magic numbers
    validate_file_type(file)
    
    # Sanitize filename
    filename = Path(file.filename).name  # Remove any path components
    
    # Save the uploaded file
    try:
        file_path = await save_upload(file, "oral_histories")
    except Exception as e:
        logger.error(f"Error saving file {filename}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error saving file. Please try again later."
        )
    
    # Save the uploaded file
    try:
        abs_path, rel_path = save_upload(file, "oral_histories")
    except Exception as e:
        logger.error(f"Error saving file {file.filename}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error saving file. Please try again later."
        )

    # Create the oral history record
    item = OralHistory(
        user_id=current_user.id,
        story_id=story_id,
        title=title,
        file_path=rel_path,
        status="pending",
        file_size_bytes=file_size,
        mime_type=file.content_type
    )

    try:
        async with db.begin():
            db.add(item)
        await db.refresh(item)
    except Exception as e:
        logger.error(f"Error creating oral history record: {str(e)}", exc_info=True)
        # Clean up the orphaned file
        try:
            os.remove(abs_path)
        except OSError:
            pass # Ignore if file cannot be removed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create oral history record."
        )

    # Enqueue background processing
    background_tasks.add_task(run_oral_processing_in_background, item.id)

    return item

@router.get("/", response_model=list[OralHistoryOut])
async def list_oral_histories(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = await db.execute(select(OralHistory).where(OralHistory.user_id == user.id).order_by(OralHistory.created_at.desc()))
    return [row for row in q.scalars().all()]

@router.get("/{oral_id}", response_model=OralHistoryOut)
async def get_oral_history(oral_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = await db.execute(select(OralHistory).where(OralHistory.id == oral_id).where(OralHistory.user_id == user.id))
    item = q.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return item
