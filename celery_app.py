from celery import Celery
import os

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

celery = Celery(
    "name_story_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

# Simple routing
celery.conf.task_routes = {
    "tasks.research_tasks.run_name_research": {"queue": "research"}
}

# Optional: make sure tasks are serialized as json
celery.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
