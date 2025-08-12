"""
Tests for the media upload API endpoints.
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image
import io
import tempfile
from pathlib import Path

from app.main import app
from app.core.config import settings
from app.database import get_db, Base, AsyncSessionLocal
from app.models_user import User
from app.auth.schemas import UserCreate
from app.auth.utils import get_password_hash

# Test client
client = TestClient(app)

TEST_USER = {
    "email": "test_media@example.com",
    "password": "testpassword123",
    "full_name": "Test User"
}

@pytest.fixture(scope="module")
async def db():
    async with AsyncSessionLocal() as session:
        yield session

@pytest.fixture(scope="module")
def client(db: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
async def test_user(db: AsyncSession):
    user_data = UserCreate(**TEST_USER)
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@pytest.fixture(scope="module")
def auth_headers(client: TestClient, test_user: User):
    response = client.post(
        "/auth/token",
        data={"username": TEST_USER["email"], "password": TEST_USER["password"]}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# Test image data
def create_test_image():
    """Create a test image in memory."""
    image = Image.new('RGB', (100, 100), color='red')
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    return img_byte_arr

# Test video data
def create_test_video():
    """Create a test video file."""
    # Create a small video file (just a few KB)
    video_data = b'\x00' * (1024 * 10)  # 10KB test video
    return io.BytesIO(video_data)

# Test image upload
def test_upload_image(client: TestClient, auth_headers: dict):
    """Test uploading an image file."""
    # Create a test image
    test_image = create_test_image()
    
    # Create a test file upload
    files = {
        'file': ('test_image.jpg', test_image, 'image/jpeg')
    }
    
    # Make the request
    response = client.post("/media/upload/image", headers=auth_headers, files=files)
    
    # Check the response
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert "file_path" in data
    assert "thumbnail_path" in data
    
    # Verify the file exists
    if data["file_path"].startswith("/"):
        file_path = data["file_path"][1:]  # Remove leading slash
    else:
        file_path = data["file_path"]
    
    assert os.path.exists(file_path)
    
    # Clean up
    if os.path.exists(file_path):
        os.remove(file_path)
    if data.get("thumbnail_path") and os.path.exists(data["thumbnail_path"]):
        os.remove(data["thumbnail_path"])

# Test video upload
def test_upload_video(client: TestClient, auth_headers: dict):
    """Test uploading a video file."""
    # Create a test video
    test_video = create_test_video()
    
    # Create a test file upload
    files = {
        'file': ('test_video.mp4', test_video, 'video/mp4')
    }
    
    # Make the request
    response = client.post("/media/upload/video", headers=auth_headers, files=files)
    
    # Check the response
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert "file_path" in data
    
    # Verify the file exists
    if data["file_path"].startswith("/"):
        file_path = data["file_path"][1:]  # Remove leading slash
    else:
        file_path = data["file_path"]
    
    assert os.path.exists(file_path)
    
    # Clean up
    if os.path.exists(file_path):
        os.remove(file_path)
    if data.get("thumbnail_path") and os.path.exists(data["thumbnail_path"]):
        os.remove(data["thumbnail_path"])

# Test unsupported file type
def test_unsupported_file_type(client: TestClient, auth_headers: dict):
    """Test uploading an unsupported file type."""
    # Create a test file with unsupported type
    files = {
        'file': ('test.txt', io.BytesIO(b'test content'), 'text/plain')
    }
    
    # Try to upload as image
    response = client.post("/media/upload/image", headers=auth_headers, files=files)
    assert response.status_code == 400
    
    # Try to upload as video
    response = client.post("/media/upload/video", headers=auth_headers, files=files)
    assert response.status_code == 400

# Test file size limit
def test_file_size_limit(client: TestClient, auth_headers: dict):
    """Test uploading a file that exceeds size limits."""
    # Create a large file (exceeds default 10MB limit for images)
    large_file = io.BytesIO(b'\x00' * (11 * 1024 * 1024))  # 11MB
    
    # Try to upload as image
    files = {
        'file': ('large_image.jpg', large_file, 'image/jpeg')
    }
    response = client.post("/media/upload/image", headers=auth_headers, files=files)
    assert response.status_code == 413  # Payload Too Large
    
    # Create a very large file (exceeds video size limit)
    large_video = io.BytesIO(b'\x00' * (101 * 1024 * 1024))  # 101MB
    
    # Try to upload as video
    files = {
        'file': ('large_video.mp4', large_video, 'video/mp4')
    }
    response = client.post("/media/upload/video", headers=auth_headers, files=files)
    assert response.status_code == 500  # Server error due to size limit

# Test getting supported formats
def test_get_supported_formats(client: TestClient):
    """Test getting the list of supported file formats."""
    response = client.get("/media/supported-formats")
    assert response.status_code == 200
    data = response.json()
    assert "image_formats" in data
    assert "video_formats" in data
    assert "max_image_size_mb" in data
    assert "max_video_size_mb" in data
