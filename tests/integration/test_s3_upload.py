from urllib.parse import urlparse
from uuid import uuid4

import boto3
import httpx
import pytest
from app.config import settings
from app.models.attachment import Attachment
from app.services.uploads import StoredObjectNotFound
from app.storage.s3 import S3ObjectStorage
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


def _client():
    endpoint_url = settings.aws_endpoint_url.strip() or None
    addressing_style = "path" if endpoint_url else "auto"
    return boto3.client(
        "s3",
        region_name=settings.aws_default_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        endpoint_url=endpoint_url,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": addressing_style},
        ),
    )


def test_presigned_post_uploads_to_localstack_and_can_be_verified() -> None:
    if urlparse(settings.aws_endpoint_url).hostname not in {
        "localhost",
        "127.0.0.1",
        "localstack",
    }:
        pytest.skip("LocalStack endpoint is not configured")
    client = _client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except (BotoCoreError, ClientError):
        pytest.skip("LocalStack S3 is not running")

    attachment_id = uuid4()
    object_key = f"integration/{attachment_id}.pdf"
    content = b"%PDF-1.4\nVroometr integration upload\n"
    storage = S3ObjectStorage(
        bucket=settings.s3_bucket,
        region=settings.aws_default_region,
        access_key_id=settings.aws_access_key_id,
        secret_access_key=settings.aws_secret_access_key,
        endpoint_url=settings.aws_endpoint_url.strip() or None,
    )
    post = storage.presign_post(
        object_key=object_key,
        mime_type="application/pdf",
        file_size=len(content),
        attachment_id=attachment_id,
        expires_in=900,
    )

    try:
        with httpx.Client(trust_env=False) as browser:
            response = browser.post(
                post.url,
                data=post.fields,
                files={"file": ("manual.pdf", content, "application/pdf")},
            )
        assert response.status_code == 204, response.text

        stored = storage.head_object(object_key)
        assert stored.content_length == len(content)
        assert stored.content_type == "application/pdf"
        assert stored.attachment_id == str(attachment_id)

        attachment = Attachment(
            id=attachment_id,
            s3_key=object_key,
            file_name="manual name.pdf",
            mime_type="application/pdf",
            file_size=len(content),
        )
        assert storage.read_attachment(attachment) == content
        with httpx.Client(trust_env=False) as browser:
            for download in [True, False]:
                url = storage.presign_read(attachment, download=download, expires_in=60)
                response = browser.get(url)
                assert response.status_code == 200
                assert response.content == content
                expected = "attachment" if download else "inline"
                assert response.headers["content-disposition"].startswith(expected)
                assert "no-store" in response.headers["cache-control"]
                expected_mime = "application/octet-stream" if download else "application/pdf"
                assert response.headers["content-type"] == expected_mime
        storage.delete_object(object_key)
        storage.delete_object(object_key)
        with pytest.raises(StoredObjectNotFound):
            storage.head_object(object_key)

        cors = client.get_bucket_cors(Bucket=settings.s3_bucket)
        assert "POST" in cors["CORSRules"][0]["AllowedMethods"]
    finally:
        client.delete_object(Bucket=settings.s3_bucket, Key=object_key)
