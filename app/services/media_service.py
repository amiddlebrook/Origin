"""
Media processing service for handling image and video uploads.
"""
import os
import uuid
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException, status
from PIL import Image, ImageOps
import imageio.v3 as iio
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Supported media types
SUPPORTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
SUPPORTED_VIDEO_TYPES = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/x-ms-wmv"]

class MediaService:
    """Service for handling media uploads and processing."""
    
    def __init__(self, upload_dir: str = None):
        """Initialize the media service with upload directory.
        
        Args:
            upload_dir: Base directory for uploads. Defaults to settings.MEDIA_UPLOAD_DIR.
        """
        self.upload_dir = upload_dir or settings.MEDIA_UPLOAD_DIR
        self.image_dir = os.path.join(self.upload_dir, "images")
        self.video_dir = os.path.join(self.upload_dir, "videos")
        self.thumbnail_dir = os.path.join(self.upload_dir, "thumbnails")
        
        # Create necessary directories
        for directory in [self.image_dir, self.video_dir, self.thumbnail_dir]:
            os.makedirs(directory, exist_ok=True)
    
    async def save_uploaded_file(
        self, 
        file: UploadFile, 
        media_type: str = "image",
        max_size_mb: int = 50
    ) -> Tuple[str, str]:
        """Save an uploaded file and generate a thumbnail if it's an image.
        
        Args:
            file: The uploaded file
            media_type: Type of media ("image" or "video")
            max_size_mb: Maximum allowed file size in MB
            
        Returns:
            Tuple of (saved_file_path, thumbnail_path)
            
        Raises:
            HTTPException: If file type is not supported or file is too large
        """
        # Validate file type
        content_type = file.content_type
        if media_type == "image" and content_type not in SUPPORTED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image type. Supported types: {', '.join(SUPPORTED_IMAGE_TYPES)}"
            )
        elif media_type == "video" and content_type not in SUPPORTED_VIDEO_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported video type. Supported types: {', '.join(SUPPORTED_VIDEO_TYPES)}"
            )
        
        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ".bin"
        filename = f"{uuid.uuid4()}{file_ext}"
        
        # Determine save directory based on media type
        save_dir = self.image_dir if media_type == "image" else self.video_dir
        file_path = os.path.join(save_dir, filename)
        
        # Save the file
        try:
            # Read file in chunks to handle large files
            file_size = 0
            with open(file_path, "wb") as buffer:
                while True:
                    chunk = await file.read(1024 * 1024)  # 1MB chunks
                    if not chunk:
                        break
                    file_size += len(chunk)
                    if file_size > max_size_mb * 1024 * 1024:  # Convert MB to bytes
                        os.remove(file_path)
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File size exceeds {max_size_mb}MB limit"
                        )
                    buffer.write(chunk)
            
            # Generate thumbnail for images
            thumbnail_path = None
            if media_type == "image":
                thumbnail_path = await self._generate_thumbnail(file_path)
            
            return file_path, thumbnail_path
            
        except Exception as e:
            logger.error(f"Error saving uploaded file: {str(e)}")
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing uploaded file"
            )
    
    async def _generate_thumbnail(self, image_path: str, size: Tuple[int, int] = (300, 300)) -> str:
        """Generate a thumbnail for an image.
        
        Args:
            image_path: Path to the source image
            size: Target size as (width, height)
            
        Returns:
            Path to the generated thumbnail
        """
        try:
            # Create thumbnail filename
            filename = f"{os.path.splitext(os.path.basename(image_path))[0]}_thumb.jpg"
            thumbnail_path = os.path.join(self.thumbnail_dir, filename)
            
            # Open and process image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary (for PNG with transparency)
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                
                # Create thumbnail
                img = ImageOps.exif_transpose(img)  # Handle orientation
                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(thumbnail_path, "JPEG", quality=85)
            
            return thumbnail_path
            
        except Exception as e:
            logger.error(f"Error generating thumbnail: {str(e)}")
            return None
    
    async def extract_video_thumbnail(
        self, 
        video_path: str, 
        time_sec: float = 5.0,
        size: Tuple[int, int] = (300, 300)
    ) -> Optional[str]:
        """Extract a thumbnail from a video.
        
        Args:
            video_path: Path to the source video
            time_sec: Timestamp in seconds to extract the frame from
            size: Target size as (width, height)
            
        Returns:
            Path to the generated thumbnail, or None if extraction failed
        """
        try:
            # Generate thumbnail filename
            filename = f"{os.path.splitext(os.path.basename(video_path))[0]}_thumb.jpg"
            thumbnail_path = os.path.join(self.thumbnail_dir, filename)
            
            # Read the frame at the specified time
            frame = iio.imread(video_path, index=int(time_sec * 30))  # Assuming 30fps
            
            # Convert to PIL Image and save as thumbnail
            img = Image.fromarray(frame)
            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(thumbnail_path, "JPEG", quality=85)
            
            return thumbnail_path
            
        except Exception as e:
            logger.error(f"Error extracting video thumbnail: {str(e)}")
            return None
    
    def get_media_url(self, file_path: str) -> str:
        """Get the public URL for a media file.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            Public URL for the media file
        """
        if not file_path or not os.path.exists(file_path):
            return ""
            
        # In a real app, this would generate a URL based on your CDN or media server
        # For development, we'll just return a relative path
        rel_path = os.path.relpath(file_path, self.upload_dir)
        return f"/media/{rel_path}"
    
    def delete_media(self, file_path: str) -> bool:
        """Delete a media file and its associated thumbnails.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                
                # Try to delete thumbnail if it exists
                filename = os.path.basename(file_path)
                name_without_ext = os.path.splitext(filename)[0]
                thumbnail_pattern = os.path.join(self.thumbnail_dir, f"{name_without_ext}*")
                
                import glob
                for thumb in glob.glob(thumbnail_pattern):
                    try:
                        os.remove(thumb)
                    except Exception:
                        pass
                        
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting media file {file_path}: {str(e)}")
            return False
