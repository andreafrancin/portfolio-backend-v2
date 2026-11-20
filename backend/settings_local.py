"""
Settings for working on a local copy of the production data.

    DJANGO_SETTINGS_MODULE=backend.settings_local python manage.py runserver

The database is whatever LOCAL_DATABASE_URL points to (never the production one), and the
production bucket is read-only: existing images are served from it, new uploads are written to
./local_media and deleting an image only removes the local file.
"""
import os
from urllib.request import urlopen

import dj_database_url
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage

from .settings import *  # noqa: F401,F403
from .settings import AWS_STORAGE_BUCKET_NAME, BASE_DIR

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
CORS_ALLOWED_ORIGINS = ["http://localhost:8081"]

DATABASES = {
    "default": dj_database_url.parse(os.environ["LOCAL_DATABASE_URL"], conn_max_age=0),
}

ROOT_URLCONF = "backend.urls_local"
MEDIA_ROOT = BASE_DIR / "local_media"
MEDIA_URL = "/media/"
LOCAL_MEDIA_ORIGIN = "http://localhost:8000"
REMOTE_MEDIA_ORIGIN = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"

AWS_ACCESS_KEY_ID = None
AWS_SECRET_ACCESS_KEY = None

local_files = FileSystemStorage(location=MEDIA_ROOT, base_url=MEDIA_URL)


def _save(self, name, content):
    return local_files.save(name, content)


def _open(self, name, mode="rb"):
    if local_files.exists(name):
        return local_files.open(name, mode)
    with urlopen(f"{REMOTE_MEDIA_ORIGIN}/{name}") as response:
        return ContentFile(response.read(), name=name)


def _delete(self, name):
    if local_files.exists(name):
        local_files.delete(name)


def _exists(self, name):
    return local_files.exists(name)


def _url(self, name, *args, **kwargs):
    if local_files.exists(name):
        return f"{LOCAL_MEDIA_ORIGIN}{local_files.url(name)}"
    return f"{REMOTE_MEDIA_ORIGIN}/{name}"


# The image fields create their own S3Boto3Storage instances, so the class itself is redirected.
S3Boto3Storage._save = _save
S3Boto3Storage._open = _open
S3Boto3Storage.delete = _delete
S3Boto3Storage.exists = _exists
S3Boto3Storage.url = _url
