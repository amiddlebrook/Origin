"""
Base schemas and configurations used throughout the application.
"""
from .schemas import (
    BaseSchema,
    PaginatedResponse,
    Message,
    ErrorResponse
)

__all__ = [
    'BaseSchema',
    'PaginatedResponse',
    'Message',
    'ErrorResponse'
]
