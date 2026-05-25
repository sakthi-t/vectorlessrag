import os
import boto3
from fastapi import UploadFile

from app.config import settings

LOCAL_STORAGE_DIR = "local_storage"


class B2StorageService:
    def __init__(self):
        try:
            self.s3 = boto3.client(
                "s3",
                endpoint_url=settings.B2_ENDPOINT,
                aws_access_key_id=settings.B2_KEY_ID,
                aws_secret_access_key=settings.B2_APP_KEY,
                region_name=settings.B2_REGION,
            )
            self.s3.head_bucket(Bucket=settings.B2_BUCKET_NAME)
            self.use_local = False
            self.bucket = settings.B2_BUCKET_NAME
        except Exception:
            self.use_local = True
            self.s3 = None
            self.bucket = None
            os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)

    async def upload(self, tenant_id: str, doc_id: str, file: UploadFile) -> str:
        key = f"{tenant_id}/documents/{doc_id}/{file.filename}"
        contents = await file.read()
        if self.use_local:
            local_path = os.path.join(LOCAL_STORAGE_DIR, *key.split("/"))
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(contents)
        else:
            self.s3.put_object(Bucket=self.bucket, Key=key, Body=contents, ContentType=file.content_type)
        await file.seek(0)
        return key

    async def download(self, key: str) -> bytes:
        if self.use_local:
            local_path = os.path.join(LOCAL_STORAGE_DIR, *key.split("/"))
            with open(local_path, "rb") as f:
                return f.read()
        response = self.s3.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    async def delete(self, key: str) -> None:
        if self.use_local:
            local_path = os.path.join(LOCAL_STORAGE_DIR, *key.split("/"))
            if os.path.exists(local_path):
                os.remove(local_path)
        else:
            self.s3.delete_object(Bucket=self.bucket, Key=key)


storage_service = B2StorageService()
