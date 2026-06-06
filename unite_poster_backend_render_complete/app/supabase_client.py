from __future__ import annotations

import os
from typing import Any, Optional

import httpx
from supabase import Client, create_client

from .config import get_settings


def get_admin_client() -> Optional[Client]:
    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        return None
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def assert_admin_client() -> Client:
    client = get_admin_client()
    if client is None:
        raise RuntimeError("Thiếu SUPABASE_URL hoặc SUPABASE_SERVICE_ROLE_KEY trong biến môi trường.")
    return client


def upload_bytes(path: str, payload: bytes, content_type: str) -> dict[str, Any]:
    settings = get_settings()
    client = assert_admin_client()
    bucket = client.storage.from_(settings.SUPABASE_BUCKET)
    bucket.upload(path, payload, {"content-type": content_type, "upsert": "true"})
    public_url = bucket.get_public_url(path)
    if isinstance(public_url, dict):
        public_url = public_url.get("publicUrl") or public_url.get("public_url")
    return {
        "bucket": settings.SUPABASE_BUCKET,
        "path": path,
        "public_url": public_url,
    }


def download_url_bytes(url: str) -> bytes:
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content


def get_public_url(path: str) -> str:
    settings = get_settings()
    client = assert_admin_client()
    data = client.storage.from_(settings.SUPABASE_BUCKET).get_public_url(path)
    if isinstance(data, dict):
        return data.get("publicUrl") or data.get("public_url")
    return data


def fetch_profile_by_user_id(user_id: str) -> Optional[dict[str, Any]]:
    client = assert_admin_client()
    result = (
        client.table("profiles")
        .select("id,email,full_name,role")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def create_job(job_type: str, created_by: str | None, input_json: dict[str, Any]) -> Optional[str]:
    settings = get_settings()
    if not settings.JOB_LOGGING_ENABLED:
        return None
    client = get_admin_client()
    if client is None:
        return None
    payload = {
        "job_type": job_type,
        "status": "pending",
        "input_json": input_json,
        "created_by": created_by,
    }
    result = client.table("poster_jobs").insert(payload).execute()
    rows = result.data or []
    return rows[0]["id"] if rows else None


def update_job(job_id: str | None, **fields: Any) -> None:
    if not job_id:
        return
    client = get_admin_client()
    if client is None:
        return
    client.table("poster_jobs").update(fields).eq("id", job_id).execute()


def insert_output_record(
    *,
    template_slug: str | None,
    job_id: str | None,
    employee_name: str | None,
    team_name: str | None,
    award_title: str | None,
    output_url: str,
    created_by: str | None,
) -> None:
    client = get_admin_client()
    if client is None:
        return

    template_id = None
    if template_slug:
        result = client.table("poster_templates").select("id").eq("slug", template_slug).limit(1).execute()
        rows = result.data or []
        template_id = rows[0]["id"] if rows else None

    payload = {
        "template_id": template_id,
        "job_id": job_id,
        "employee_name": employee_name,
        "team_name": team_name,
        "award_title": award_title,
        "output_url": output_url,
        "created_by": created_by,
    }
    client.table("poster_outputs").insert(payload).execute()
