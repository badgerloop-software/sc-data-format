"""Download the signal spreadsheet from Google Drive."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path

import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload


EXPORT_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _credentials():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw:
        info = json.loads(raw)
        return service_account.Credentials.from_service_account_info(
            info,
            scopes=DRIVE_SCOPES,
        )
    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if path and Path(path).is_file():
        return service_account.Credentials.from_service_account_file(
            path,
            scopes=DRIVE_SCOPES,
        )
    creds, _ = google.auth.default(scopes=DRIVE_SCOPES)
    if creds:
        return creds
    raise RuntimeError(
        "No Google credentials found. Use Workload Identity Federation in CI, "
        "or set GOOGLE_SERVICE_ACCOUNT_JSON / GOOGLE_APPLICATION_CREDENTIALS locally."
    )


def download_spreadsheet(file_id: str, output_path: str) -> str:
    creds = _credentials()
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        request = service.files().export_media(fileId=file_id, mimeType=EXPORT_MIME)
        return _write_request(request, output_path)
    except HttpError as err:
        if err.resp.status not in (400, 403, 404):
            raise
        request = service.files().get_media(fileId=file_id)
        return _write_request(request, output_path)


def _write_request(request, output_path: str) -> str:
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    Path(output_path).write_bytes(buffer.getvalue())
    return output_path
