"""
Storage service for MinIO (S3-compatible object storage) - wraps the
synchronous `minio` SDK, same style as OPSService/ScopusService wrapping
their respective HTTP clients.
"""

import io

from minio import Minio

from core.logging import get_logger

logger = get_logger(__name__)


class MinioService:
    """Cliente síncrono do MinIO - upload/download/delete de objetos e
    garantia de existência do bucket usado pra guardar os gráficos gerados."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ) -> None:
        self.bucket = bucket
        self._client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)

    def ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self.bucket):
            self._client.make_bucket(self.bucket)
            logger.info("minio_bucket_created", bucket=self.bucket)

    def upload_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            self.bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def download_bytes(self, key: str) -> bytes:
        response = self._client.get_object(self.bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_object(self, key: str) -> None:
        self._client.remove_object(self.bucket, key)
