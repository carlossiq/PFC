"""
Object storage services package for external storage integrations.
"""

from services.storage.minio_service import MinioService

__all__ = [
    "MinioService",
]
