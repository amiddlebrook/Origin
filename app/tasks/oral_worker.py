import logging
import asyncio
from typing import Optional
from sqlalchemy import select, update
from app.database import AsyncSessionLocal
from app.models_story import OralHistory
from app.services.audio_processor import process_audio_file

logger = logging.getLogger(__name__)

async def process_oral_history(oral_id: int):
    """
    Process an oral history recording.
    This could include:
    - Transcribing the audio
    - Extracting metadata (duration, format, etc.)
    - Generating a summary or key points
    - Any other post-processing
    """
    async with AsyncSessionLocal() as db:
        # Mark as processing
        async with db.begin():
            await db.execute(
                update(OralHistory)
                .where(OralHistory.id == oral_id)
                .values(status="processing")
            )

        # Get the oral history record
        result = await db.execute(
            select(OralHistory).where(OralHistory.id == oral_id)
        )
        oral_history = result.scalar_one_or_none()
        
        if not oral_history:
            logger.error(f"Oral history with ID {oral_id} not found")
            return

        try:
            # Process the audio file
            processing_result = await process_audio_file(oral_history.file_path)
            
            # Update the record with processing results
            async with db.begin():
                await db.execute(
                    update(OralHistory)
                    .where(OralHistory.id == oral_id)
                    .values(
                        status="processed",
                        duration_seconds=processing_result.get("duration_seconds"),
                        transcript=processing_result.get("transcript"),
                        metadata=processing_result.get("metadata", {})
                    )
                )
                
            logger.info(f"Successfully processed oral history {oral_id}")
            
        except Exception as e:
            logger.exception(f"Error processing oral history {oral_id}")
            # Update with error status
            async with db.begin():
                await db.execute(
                    update(OralHistory)
                    .where(OralHistory.id == oral_id)
                    .values(
                        status="error",
                        error_message=str(e)
                    )
                )

async def run_oral_processing_in_background(oral_id: int):
    """Run the oral history processing in the background."""
    asyncio.create_task(process_oral_history(oral_id))
