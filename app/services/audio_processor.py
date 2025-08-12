import logging
import os
import json
from typing import Dict, Any, Optional
import subprocess
import tempfile
from pydub import AudioSegment
import speech_recognition as sr

logger = logging.getLogger(__name__)

class AudioProcessingError(Exception):
    """Custom exception for audio processing errors."""
    pass

async def process_audio_file(file_path: str) -> Dict[str, Any]:
    """
    Process an audio file to extract metadata and transcribe it.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Dict containing processing results including duration, transcript, and metadata
    """
    if not os.path.exists(file_path):
        raise AudioProcessingError(f"File not found: {file_path}")
    
    try:
        # Get file metadata
        file_info = await get_audio_metadata(file_path)
        duration = file_info.get('duration_seconds')
        
        # Transcribe the audio
        transcript = await transcribe_audio(file_path)
        
        return {
            'duration_seconds': duration,
            'transcript': transcript,
            'metadata': file_info
        }
        
    except Exception as e:
        logger.exception(f"Error processing audio file {file_path}")
        raise AudioProcessingError(f"Failed to process audio: {str(e)}")

async def get_audio_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from an audio file using ffprobe."""
    try:
        # Use ffprobe to get metadata
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration:stream=codec_name,sample_rate,channels',
            '-of', 'json',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        # Extract relevant metadata
        format_info = data.get('format', {})
        stream_info = data.get('streams', [{}])[0] if data.get('streams') else {}
        
        return {
            'duration_seconds': float(format_info.get('duration', 0)),
            'codec': stream_info.get('codec_name'),
            'sample_rate': stream_info.get('sample_rate'),
            'channels': stream_info.get('channels'),
            'format': format_info.get('format_name'),
            'size_bytes': os.path.getsize(file_path)
        }
        
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Could not extract metadata using ffprobe: {e}")
        # Fallback to pydub for basic info
        try:
            audio = AudioSegment.from_file(file_path)
            return {
                'duration_seconds': len(audio) / 1000.0,  # pydub works in milliseconds
                'channels': audio.channels,
                'sample_rate': audio.frame_rate,
                'format': os.path.splitext(file_path)[1].lstrip('.').lower()
            }
        except Exception as fallback_error:
            logger.warning(f"Fallback metadata extraction failed: {fallback_error}")
            return {}

async def transcribe_audio(file_path: str, language: str = 'en-US') -> Optional[str]:
    """
    Transcribe an audio file using speech recognition.
    
    Args:
        file_path: Path to the audio file
        language: Language code for transcription (default: 'en-US')
        
    Returns:
        Transcribed text or None if transcription fails
    """
    # Convert to WAV if needed (speech_recognition works best with WAV)
    if not file_path.lower().endswith('.wav'):
        try:
            audio = AudioSegment.from_file(file_path)
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                audio.export(temp_path, format='wav')
                file_path = temp_path
        except Exception as e:
            logger.warning(f"Could not convert {file_path} to WAV: {e}")
    
    # Initialize recognizer
    recognizer = sr.Recognizer()
    
    try:
        with sr.AudioFile(file_path) as source:
            # Listen for the data (load audio to memory)
            audio_data = recognizer.record(source)
            # Recognize (convert from speech to text)
            text = recognizer.recognize_google(audio_data, language=language)
            return text
            
    except sr.UnknownValueError:
        logger.warning("Google Speech Recognition could not understand the audio")
    except sr.RequestError as e:
        logger.error(f"Could not request results from Google Speech Recognition service; {e}")
    except Exception as e:
        logger.exception(f"Error during speech recognition: {e}")
    
    return None
