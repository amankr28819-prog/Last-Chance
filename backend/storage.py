"""
Last Chance — Storage Service
Seamless hybrid storage service supporting private Supabase Storage buckets
in production, with automatic fallback to local disk storage for development.
"""
import os
import mimetypes
from typing import Optional, Dict, Any, Tuple
import httpx

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY", "")
SUPABASE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "handouts")

class StorageService:
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None, bucket: Optional[str] = None):
        self.url = (url or SUPABASE_URL).rstrip("/")
        self.key = key or SUPABASE_KEY
        self.bucket = bucket or SUPABASE_BUCKET
        self.is_cloud = bool(self.url and self.key)

        # Local fallback directory
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.local_dir = os.path.join(self.base_dir, "uploads")
        os.makedirs(self.local_dir, exist_ok=True)

    def _headers(self, content_type: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}"
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def upload_file(self, file_bytes: bytes, file_name: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Uploads file content to storage.
        If Supabase is configured, uploads to the private Supabase bucket.
        Always preserves a local copy in uploads/ to prevent data loss.
        """
        if not content_type:
            mime, _ = mimetypes.guess_type(file_name)
            content_type = mime or "application/octet-stream"

        local_path = os.path.join(self.local_dir, file_name)
        try:
            with open(local_path, "wb") as f:
                f.write(file_bytes)
        except Exception:
            pass

        if not self.is_cloud:
            return {
                "storage_path": local_path,
                "is_remote": False,
                "filename": file_name,
                "file_size": len(file_bytes),
                "content_type": content_type
            }

        endpoint = f"{self.url}/storage/v1/object/{self.bucket}/{file_name}"
        headers = self._headers(content_type)
        headers["x-upsert"] = "true"

        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.post(endpoint, content=file_bytes, headers=headers)
                if res.status_code in (200, 201):
                    return {
                        "storage_path": f"{self.bucket}/{file_name}",
                        "is_remote": True,
                        "filename": file_name,
                        "file_size": len(file_bytes),
                        "content_type": content_type
                    }
                else:
                    return {
                        "storage_path": local_path,
                        "is_remote": False,
                        "filename": file_name,
                        "file_size": len(file_bytes),
                        "content_type": content_type,
                        "warning": f"Supabase upload status {res.status_code}: {res.text}"
                    }
        except Exception as e:
            return {
                "storage_path": local_path,
                "is_remote": False,
                "filename": file_name,
                "file_size": len(file_bytes),
                "content_type": content_type,
                "warning": f"Supabase connection exception: {str(e)}"
            }

    def get_file_bytes(self, storage_path_or_filename: str) -> Tuple[Optional[bytes], str]:
        """
        Retrieves file bytes from storage.
        If file is remote, streams from Supabase.
        Falls back seamlessly to local uploads/ directory.
        """
        clean_name = os.path.basename(storage_path_or_filename)
        mime, _ = mimetypes.guess_type(clean_name)
        content_type = mime or "application/octet-stream"

        if self.is_cloud:
            endpoint = f"{self.url}/storage/v1/object/{self.bucket}/{clean_name}"
            try:
                with httpx.Client(timeout=30.0) as client:
                    res = client.get(endpoint, headers=self._headers())
                    if res.status_code == 200:
                        header_mime = res.headers.get("Content-Type")
                        return res.content, (header_mime or content_type)
            except Exception:
                pass

        # Fallback to local disk
        candidates = [
            storage_path_or_filename,
            os.path.join(self.local_dir, clean_name),
            os.path.join(self.local_dir, storage_path_or_filename)
        ]
        for p in candidates:
            if os.path.exists(p) and os.path.isfile(p):
                with open(p, "rb") as f:
                    return f.read(), content_type

        return None, content_type

    def create_signed_url(self, storage_path_or_filename: str, expires_in: int = 3600) -> Optional[str]:
        """
        Creates a time-limited signed URL for authorized access to private handouts.
        """
        if not self.is_cloud:
            return None

        clean_name = os.path.basename(storage_path_or_filename)
        endpoint = f"{self.url}/storage/v1/object/sign/{self.bucket}/{clean_name}"
        headers = self._headers("application/json")

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(endpoint, json={"expiresIn": expires_in}, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    signed = data.get("signedURL") or data.get("signedUrl")
                    if signed:
                        if signed.startswith("http"):
                            return signed
                        return f"{self.url}/storage/v1{signed}"
        except Exception:
            pass

        return None

    def delete_file(self, storage_path_or_filename: str) -> bool:
        """
        Deletes a file from Supabase storage and local disk.
        """
        clean_name = os.path.basename(storage_path_or_filename)
        deleted = False

        if self.is_cloud:
            endpoint = f"{self.url}/storage/v1/object/{self.bucket}"
            headers = self._headers("application/json")
            try:
                with httpx.Client(timeout=15.0) as client:
                    res = client.request("DELETE", endpoint, json={"prefixes": [clean_name]}, headers=headers)
                    if res.status_code in (200, 204):
                        deleted = True
            except Exception:
                pass

        local_path = os.path.join(self.local_dir, clean_name)
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
                deleted = True
            except Exception:
                pass

        return deleted

# Singleton instance
storage_service = StorageService()
