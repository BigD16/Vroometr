from urllib.parse import quote
from uuid import UUID

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.models.attachment import Attachment
from app.services.uploads import (
    PresignedPost,
    StoredObjectMetadata,
    StoredObjectNotFound,
    UploadStorageUnavailable,
)


class S3ObjectStorage:
    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        endpoint_url: str | None,
    ) -> None:
        addressing_style = "path" if endpoint_url else "auto"
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            endpoint_url=endpoint_url,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": addressing_style},
            ),
        )

    def presign_post(
        self,
        *,
        object_key: str,
        mime_type: str,
        file_size: int,
        attachment_id: UUID,
        expires_in: int,
    ) -> PresignedPost:

        attachment_value = str(attachment_id)
        fields = {
            "Content-Type": mime_type,
            "x-amz-meta-attachment-id": attachment_value,
        }
        conditions: list[object] = [
            {"Content-Type": mime_type},
            {"x-amz-meta-attachment-id": attachment_value},
            ["content-length-range", file_size, file_size],
        ]
        try:
            response = self._client.generate_presigned_post(
                Bucket=self._bucket,
                Key=object_key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expires_in,
            )
        except (BotoCoreError, ClientError) as exc:
            raise UploadStorageUnavailable("could not authorize upload") from exc
        return PresignedPost(
            url=response["url"],
            fields=response["fields"],
            expires_in=expires_in,
        )

    def head_object(self, object_key: str) -> StoredObjectMetadata:
        try:
            response = self._client.head_object(Bucket=self._bucket, Key=object_key)
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                raise StoredObjectNotFound from exc
            raise UploadStorageUnavailable("could not verify upload") from exc
        except BotoCoreError as exc:
            raise UploadStorageUnavailable("could not verify upload") from exc

        metadata = response.get("Metadata", {})
        return StoredObjectMetadata(
            content_length=response["ContentLength"],
            content_type=response.get("ContentType"),
            attachment_id=metadata.get("attachment-id"),
        )

    def presign_read(self, attachment: Attachment, *, download: bool, expires_in: int) -> str:
        disposition = "attachment" if download else "inline"
        # Force an allowed response type; never render client-supplied HTML as active content.
        mime_type = (
            attachment.mime_type
            if attachment.mime_type
            in {
                "application/pdf",
                "image/jpeg",
                "image/png",
                "image/webp",
            }
            else "application/octet-stream"
        )
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self._bucket,
                    "Key": attachment.s3_key,
                    "ResponseContentType": "application/octet-stream" if download else mime_type,
                    "ResponseContentDisposition": (
                        f"{disposition}; filename*=UTF-8''{quote(attachment.file_name, safe='')}"
                    ),
                    "ResponseCacheControl": "private, no-store",
                },
                ExpiresIn=expires_in,
            )
        except (BotoCoreError, ClientError) as exc:
            raise UploadStorageUnavailable("could not authorize file access") from exc

    def delete_object(self, object_key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=object_key)
        except (BotoCoreError, ClientError) as exc:
            raise UploadStorageUnavailable("could not delete file") from exc

    def read_attachment(self, attachment: Attachment) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=attachment.s3_key)
            body = response["Body"]
            try:
                if (response["ContentLength"] != attachment.file_size
                    or response.get("ContentType") != attachment.mime_type
                    or response.get("Metadata", {}).get("attachment-id") != str(attachment.id)):
                    raise UploadStorageUnavailable("Stored file metadata changed")
                content = body.read(attachment.file_size + 1)
                if len(content) != attachment.file_size:
                    raise UploadStorageUnavailable("Stored file size changed")
                return content
            finally:
                body.close()
        except (BotoCoreError, ClientError) as exc:
            raise UploadStorageUnavailable("Could not read the stored file") from exc
