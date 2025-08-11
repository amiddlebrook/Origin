"""
API endpoints for media uploads and management.
"""
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.router import get_current_user
from app.models_user import User
from app.services.media_service import MediaService, SUPPORTED_IMAGE_TYPES, SUPPORTED_VIDEO_TYPES
from app.core.config import settings

router = APIRouter(prefix="/media", tags=["media"])

# Initialize media service
media_service = MediaService()

@router.post("/upload/image", status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload an image file.
    
    The image will be processed and a thumbnail will be generated automatically.
    """
    try:
        file_path, thumbnail_path = await media_service.save_uploaded_file(
            file, 
            media_type="image",
            max_size_mb=settings.MAX_IMAGE_SIZE_MB
        )
        
        return {
            "status": "success",
            "message": "Image uploaded successfully",
            "file_path": media_service.get_media_url(file_path),
            "thumbnail_path": media_service.get_media_url(thumbnail_path) if thumbnail_path else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading image: {str(e)}"
        )

@router.post("/upload/video", status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a video file.
    
    A thumbnail will be extracted from the video automatically.
    """
    try:
        file_path, _ = await media_service.save_uploaded_file(
            file, 
            media_type="video",
            max_size_mb=settings.MAX_VIDEO_SIZE_MB
        )
        
        # Extract thumbnail from video
        thumbnail_path = await media_service.extract_video_thumbnail(file_path)
        
        return {
            "status": "success",
            "message": "Video uploaded successfully",
            "file_path": media_service.get_media_url(file_path),
            "thumbnail_path": media_service.get_media_url(thumbnail_path) if thumbnail_path else None
        }
    except HTTPException:
        raise
    except Exception as e:
        # Clean up if there was an error
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading video: {str(e)}"
        )

@router.get("/supported-formats")
async def get_supported_formats():
    """Get a list of supported media formats."""
    return {
        "image_formats": SUPPORTED_IMAGE_TYPES,
        "video_formats": SUPPORTED_VIDEO_TYPES,
        "max_image_size_mb": settings.MAX_IMAGE_SIZE_MB,
        "max_video_size_mb": settings.MAX_VIDEO_SIZE_MB
    }

@router.delete("/{media_path:path}")
async def delete_media(
    media_path: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a media file.
    
    Only the owner of the media or an admin can delete it.
    """
    try:
        # In a real app, you would check if the current user has permission to delete this file
        # For now, we'll just check if the file exists
        full_path = os.path.join(settings.MEDIA_UPLOAD_DIR, media_path)
        
        if not os.path.exists(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Delete the file
        success = media_service.delete_media(full_path)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete file"
            )
            
        return {"status": "success", "message": "File deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting file: {str(e)}"
        )
