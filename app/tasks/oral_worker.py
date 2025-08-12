import asyncio
import logging
import time
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session
from app.models_story import OralHistory
from app.services.audio_processor import AudioProcessor

# Configure logging
logger = logging.getLogger("oral_worker")

class ProcessingMetrics:
    """Track processing metrics for monitoring."""
    def __init__(self):
        self.start_time: float = 0
        self.end_time: float = 0
        self.steps: Dict[str, float] = {}
        self.metadata: Dict[str, Any] = {}
    
    def start_timer(self) -> None:
        """Start the processing timer."""
        self.start_time = time.time()
    
    def record_step(self, step_name: str) -> None:
        """Record the duration of a processing step."""
        self.steps[step_name] = time.time() - (self.start_time + sum(self.steps.values()))
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all recorded metrics."""
        self.end_time = time.time()
        return {
            "total_duration": self.end_time - self.start_time,
            "steps": self.steps,
            "metadata": self.metadata
        }

async def process_oral_history(oral_history_id: int, file_path: str) -> None:
    """
    Process an oral history audio file in the background.
    
    Args:
        oral_history_id: The ID of the oral history record
        file_path: Path to the audio file to process
    """
    metrics = ProcessingMetrics()
    metrics.start_timer()
    
    logger.info(f"Starting processing for oral history {oral_history_id}")
    
    db = None
    oral_history = None
    
    try:
        # Initialize database session
        db = async_session()
        
        # Get the oral history record
        oral_history = await db.get(OralHistory, oral_history_id)
        if not oral_history:
            logger.error(f"Oral history {oral_history_id} not found")
            return
            
        # Update status to processing
        oral_history.status = "processing"
        oral_history.processing_started_at = time.time()
        await db.commit()
        metrics.record_step("db_initialization")
        
        # Initialize audio processor
        processor = AudioProcessor()
        
        # Process the audio file
        logger.info(f"Starting audio processing for {oral_history_id}")
        result = await processor.process_audio(file_path)
        metrics.record_step("audio_processing")
        
        # Update the oral history with results
        logger.info(f"Updating database for {oral_history_id}")
        oral_history.status = "completed"
        oral_history.duration = result.get("duration")
        oral_history.transcript = result.get("transcript")

        # Safely merge metadata
        current_metadata = oral_history.metadata or {}
        current_metadata.update(result.get("metadata", {}))
        current_metadata["processing_metrics"] = metrics.get_metrics()
        oral_history.metadata = current_metadata

        oral_history.processing_completed_at = time.time()
        
        await db.commit()
        metrics.record_step("db_update")
        
        logger.info(
            f"Successfully processed oral history {oral_history_id} in "
            f"{metrics.get_metrics()['total_duration']:.2f} seconds"
        )
        
    except asyncio.CancelledError:
        logger.warning(f"Processing cancelled for oral history {oral_history_id}")
        if oral_history and db:
            oral_history.status = "cancelled"
            oral_history.error_message = "Processing was cancelled"
            await db.commit()
        raise
        
    except Exception as e:
        error_msg = f"Error processing oral history {oral_history_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        if oral_history and db:
            try:
                oral_history.status = "failed"
                oral_history.error_message = str(e)

                # Safely merge metadata for error
                error_metadata = oral_history.metadata or {}
                error_metadata["error_traceback"] = str(e.__traceback__)
                error_metadata["processing_metrics"] = metrics.get_metrics()
                oral_history.metadata = error_metadata

                await db.commit()
            except Exception as db_error:
                logger.error(f"Failed to update failed status: {db_error}", exc_info=True)
        
        # Re-raise to allow task retry if needed
        raise
        
    finally:
        if db:
            try:
                await db.close()
            except Exception as e:
                logger.error(f"Error closing database connection: {e}", exc_info=True)

def run_oral_processing_in_background(oral_history_id: int, file_path: str) -> None:
    """
    Run the oral history processing in a background task.
    
    This function is called from the API endpoint and manages the asyncio event loop.
    """
    logger.info(f"Starting background processing for oral history {oral_history_id}")
    
    loop = None
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(process_oral_history(oral_history_id, file_path))
    except Exception as e:
        logger.critical(
            f"Critical error in background task for oral history {oral_history_id}: {str(e)}",
            exc_info=True
        )
        raise
    finally:
        if loop:
            try:
                loop.close()
            except Exception as e:
                logger.error(f"Error closing event loop: {e}", exc_info=True)
