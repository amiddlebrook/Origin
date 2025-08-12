import os
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

# Test data
TEST_AUDIO_FILE = "test_audio.wav"
TEST_TITLE = "Test Oral History"

@pytest.fixture
def audio_file():
    """Create a test audio file."""
    # Create a minimal WAV file
    with open(TEST_AUDIO_FILE, "wb") as f:
        # WAV header for an empty audio file
        f.write(b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00')
        f.write(b'\x80\xbb\x00\x00\x00\x77\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00')
    
    yield TEST_AUDIO_FILE
    
    # Cleanup
    if os.path.exists(TEST_AUDIO_FILE):
        os.remove(TEST_AUDIO_FILE)

@pytest.mark.asyncio
async def test_upload_oral_history(client: TestClient, auth_headers: dict, audio_file: str, db: AsyncSession):
    """Test uploading an oral history audio file."""
    with open(audio_file, "rb") as f:
        response = client.post(
            "/oral-histories/upload",
            headers=auth_headers,
            files={"file": (os.path.basename(audio_file), f, "audio/wav")},
            data={"title": TEST_TITLE}
        )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == TEST_TITLE
    assert data["status"] == "pending"
    assert data["file_path"] is not None

@pytest.mark.asyncio
async def test_upload_invalid_file_type(client: TestClient, auth_headers: dict):
    """Test uploading a non-audio file."""
    with open("test.txt", "w") as f:
        f.write("This is not an audio file")
    
    with open("test.txt", "rb") as f:
        response = client.post(
            "/oral-histories/upload",
            headers=auth_headers,
            files={"file": ("test.txt", f, "text/plain")},
            data={"title": "Invalid File"}
        )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Only audio files are allowed" in response.text
    
    # Cleanup
    if os.path.exists("test.txt"):
        os.remove("test.txt")

@pytest.mark.asyncio
async def test_list_oral_histories(client: TestClient, auth_headers: dict, db: AsyncSession):
    """Test listing oral histories."""
    # First, upload a test file
    with open("test_audio.wav", "wb") as f:
        f.write(b'dummy audio data')
    
    with open("test_audio.wav", "rb") as f:
        client.post(
            "/oral-histories/upload",
            headers=auth_headers,
            files={"file": ("test_audio.wav", f, "audio/wav")},
            data={"title": "Test List"}
        )
    
    # Now list all oral histories
    response = client.get("/oral-histories/", headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(item["title"] == "Test List" for item in data)
    
    # Cleanup
    if os.path.exists("test_audio.wav"):
        os.remove("test_audio.wav")

@pytest.mark.asyncio
async def test_get_oral_history(client: TestClient, auth_headers: dict, db: AsyncSession):
    """Test getting a single oral history by ID."""
    # First, upload a test file
    with open("test_audio.wav", "wb") as f:
        f.write(b'dummy audio data')
    
    with open("test_audio.wav", "rb") as f:
        upload_response = client.post(
            "/oral-histories/upload",
            headers=auth_headers,
            files={"file": ("test_audio.wav", f, "audio/wav")},
            data={"title": "Test Get"}
        )
    
    # Get the ID of the uploaded history
    history_id = upload_response.json()["id"]
    
    # Now get it by ID
    response = client.get(f"/oral-histories/{history_id}", headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == history_id
    assert data["title"] == "Test Get"
    
    # Cleanup
    if os.path.exists("test_audio.wav"):
        os.remove("test_audio.wav")

@pytest.mark.asyncio
async def test_update_oral_history(client: TestClient, auth_headers: dict, db: AsyncSession):
    """Test updating an oral history."""
    # First, upload a test file
    with open("test_audio.wav", "wb") as f:
        f.write(b'dummy audio data')
    
    with open("test_audio.wav", "rb") as f:
        upload_response = client.post(
            "/oral-histories/upload",
            headers=auth_headers,
            files={"file": ("test_audio.wav", f, "audio/wav")},
            data={"title": "Before Update"}
        )
    
    # Get the ID of the uploaded history
    history_id = upload_response.json()["id"]
    
    # Now update it
    update_data = {"title": "After Update"}
    response = client.put(
        f"/oral-histories/{history_id}",
        headers={"Content-Type": "application/json", **auth_headers},
        json=update_data
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == "After Update"
    
    # Cleanup
    if os.path.exists("test_audio.wav"):
        os.remove("test_audio.wav")

@pytest.mark.asyncio
async def test_delete_oral_history(client: TestClient, auth_headers: dict, db: AsyncSession):
    """Test deleting an oral history."""
    # First, upload a test file
    with open("test_audio.wav", "wb") as f:
        f.write(b'dummy audio data')
    
    with open("test_audio.wav", "rb") as f:
        upload_response = client.post(
            "/oral-histories/upload",
            headers=auth_headers,
            files={"file": ("test_audio.wav", f, "audio/wav")},
            data={"title": "To Be Deleted"}
        )
    
    # Get the ID of the uploaded history
    history_id = upload_response.json()["id"]
    
    # Now delete it
    response = client.delete(f"/oral-histories/{history_id}", headers=auth_headers)
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify it's gone
    get_response = client.get(f"/oral-histories/{history_id}", headers=auth_headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    # Cleanup
    if os.path.exists("test_audio.wav"):
        os.remove("test_audio.wav")
