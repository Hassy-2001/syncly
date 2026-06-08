from pathlib import PurePosixPath
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import Storage


class CloudinaryMediaStorage(Storage):
    """Small Cloudinary-backed storage for user uploads only."""

    def _cloudinary(self):
        try:
            import cloudinary
            import cloudinary.uploader
            import cloudinary.utils
        except ImportError as exc:
            raise ImproperlyConfigured("Cloudinary uploads require the cloudinary package.") from exc
        config = getattr(settings, "CLOUDINARY_STORAGE", {})
        if config:
            cloudinary.config(
                cloud_name=config.get("CLOUD_NAME"),
                api_key=config.get("API_KEY"),
                api_secret=config.get("API_SECRET"),
                secure=True,
            )
        elif getattr(settings, "MEDIA_UPLOADS_REQUIRE_CLOUDINARY", False):
            raise ImproperlyConfigured(
                "Cloudinary is not configured. Add CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET in Vercel."
            )
        return cloudinary, cloudinary.uploader, cloudinary.utils

    def _save(self, name, content):
        cloudinary, uploader, utils = self._cloudinary()
        path = PurePosixPath(name)
        folder = str(path.parent).strip(".")
        stem = path.stem or uuid4().hex
        public_id = f"{stem}-{uuid4().hex[:10]}"

        options = {
            "resource_type": "auto",
            "public_id": public_id,
            "overwrite": False,
            "use_filename": False,
            "unique_filename": False,
        }
        if folder:
            options["folder"] = folder

        upload = uploader.upload(content, **options)
        public_id = upload.get("public_id") or name
        resource_type = upload.get("resource_type") or "image"
        return f"{resource_type}:{public_id}"

    def url(self, name):
        if not name:
            return ""
        name = str(name)
        if name.startswith(("http://", "https://")):
            return name

        cloudinary, uploader, utils = self._cloudinary()
        resource_type = "image"
        public_id = name
        if ":" in name:
            resource_type, public_id = name.split(":", 1)
        url, options = utils.cloudinary_url(public_id, resource_type=resource_type, secure=True)
        return url

    def delete(self, name):
        if not name:
            return
        name = str(name)
        resource_type = "image"
        public_id = name
        if ":" in name:
            resource_type, public_id = name.split(":", 1)
        cloudinary, uploader, utils = self._cloudinary()
        uploader.destroy(public_id, resource_type=resource_type)

    def exists(self, name):
        return False

    def size(self, name):
        return 0

    def get_available_name(self, name, max_length=None):
        return name
