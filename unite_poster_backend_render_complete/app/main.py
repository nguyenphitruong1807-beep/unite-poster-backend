from __future__ import annotations

import json
import os
import time
import uuid
from io import BytesIO
from typing import Any, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image

from .auth import get_current_user_optional
from .config import get_settings
from .image_autofit import load_rgba, suggest_transform
from .image_remove_bg import remove_background_bytes
from .poster_render import load_image_from_bytes, load_image_from_url, render_poster, save_png_bytes
from .supabase_client import (
    create_job,
    download_url_bytes,
    insert_output_record,
    update_job,
    upload_bytes,
)

settings = get_settings()

app = FastAPI(title=settings.APP_NAME, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {
        "ok": True,
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY),
    }


@app.post("/api/remove-bg")
async def api_remove_bg(
    file: UploadFile = File(...),
    save_to_storage: bool = Form(True),
    folder: str = Form("processed/remove-bg"),
    output_name: str | None = Form(None),
    return_base64: bool = Form(False),
    user: Optional[dict[str, Any]] = Depends(get_current_user_optional),
):
    job_id = create_job("remove_bg", user.get("id") if user else None, {"file": file.filename, "folder": folder})
    try:
        update_job(job_id, status="processing")
        source_bytes = await file.read()
        result_bytes, meta = remove_background_bytes(source_bytes)
        payload: dict[str, Any] = {"success": True, "meta": meta, "job_id": job_id}

        if save_to_storage:
            suffix = ".png"
            stem = output_name or f"{os.path.splitext(file.filename or 'person')[0]}-{uuid.uuid4().hex[:8]}"
            path = f"{folder.rstrip('/')}/{stem}{suffix}"
            uploaded = upload_bytes(path, result_bytes, "image/png")
            payload["storage"] = uploaded

        if return_base64:
            import base64
            payload["base64"] = base64.b64encode(result_bytes).decode("utf-8")

        update_job(job_id, status="done", result_json=payload)
        return JSONResponse(payload)
    except Exception as exc:
        update_job(job_id, status="failed", error_message=str(exc))
        raise HTTPException(status_code=500, detail=f"Xóa nền lỗi: {exc}") from exc


@app.post("/api/auto-fit-person")
async def api_auto_fit_person(
    file: UploadFile | None = File(default=None),
    image_url: str | None = Form(default=None),
    slot_x: int = Form(...),
    slot_y: int = Form(...),
    slot_width: int = Form(...),
    slot_height: int = Form(...),
    anchor_y: str = Form("bottom"),
    fit_mode: str = Form("head_to_belly"),
    save_removed_bg: bool = Form(True),
    folder: str = Form("processed/autofit"),
    user: Optional[dict[str, Any]] = Depends(get_current_user_optional),
):
    if file is None and not image_url:
        raise HTTPException(status_code=400, detail="Cần upload file hoặc truyền image_url")

    job_id = create_job(
        "auto_fit",
        user.get("id") if user else None,
        {
            "file": getattr(file, "filename", None),
            "image_url": image_url,
            "slot": {"x": slot_x, "y": slot_y, "width": slot_width, "height": slot_height},
        },
    )
    try:
        update_job(job_id, status="processing")
        source_bytes = await file.read() if file is not None else download_url_bytes(image_url)  # type: ignore[arg-type]
        removed_bytes, meta = remove_background_bytes(source_bytes)
        img = load_rgba(removed_bytes)
        transform = suggest_transform(
            img,
            slot_x=slot_x,
            slot_y=slot_y,
            slot_width=slot_width,
            slot_height=slot_height,
            anchor_y=anchor_y,
            fit_mode=fit_mode,
        )
        payload: dict[str, Any] = {
            "success": True,
            "job_id": job_id,
            "meta": meta,
            "transform": transform,
        }
        if save_removed_bg:
            stem = os.path.splitext(file.filename or "person")[0] if file else f"autofit-{uuid.uuid4().hex[:8]}"
            path = f"{folder.rstrip('/')}/{stem}-{uuid.uuid4().hex[:6]}.png"
            payload["storage"] = upload_bytes(path, removed_bytes, "image/png")
        update_job(job_id, status="done", result_json=payload)
        return JSONResponse(payload)
    except Exception as exc:
        update_job(job_id, status="failed", error_message=str(exc))
        raise HTTPException(status_code=500, detail=f"Auto-fit lỗi: {exc}") from exc


async def _load_upload_or_url(upload: UploadFile | None, url: str | None) -> Image.Image | None:
    if upload is not None:
        return load_image_from_bytes(await upload.read())
    if url:
        return load_image_from_url(url)
    return None


@app.post("/api/render-poster")
async def api_render_poster(
    template_json: str = Form(...),
    texts_json: str = Form("{}"),
    person_x: float = Form(0),
    person_y: float = Form(0),
    person_scale: float = Form(1),
    background_url: str | None = Form(default=None),
    foreground_url: str | None = Form(default=None),
    person_image_url: str | None = Form(default=None),
    background_file: UploadFile | None = File(default=None),
    foreground_file: UploadFile | None = File(default=None),
    person_file: UploadFile | None = File(default=None),
    save_to_storage: bool = Form(True),
    output_folder: str = Form("outputs/posters"),
    output_name: str | None = Form(default=None),
    user: Optional[dict[str, Any]] = Depends(get_current_user_optional),
):
    try:
        template = json.loads(template_json)
        text_values = json.loads(texts_json or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"JSON không hợp lệ: {exc}") from exc

    job_id = create_job(
        "render_poster",
        user.get("id") if user else None,
        {
            "template_id": template.get("templateId"),
            "template_name": template.get("templateName"),
            "output_folder": output_folder,
        },
    )

    try:
        update_job(job_id, status="processing")

        background_img = await _load_upload_or_url(background_file, background_url or template.get("layers", {}).get("background"))
        foreground_img = await _load_upload_or_url(foreground_file, foreground_url or template.get("layers", {}).get("foreground"))
        person_img = await _load_upload_or_url(person_file, person_image_url)

        poster = render_poster(
            template=template,
            text_values=text_values,
            person_image=person_img,
            background_image=background_img,
            foreground_image=foreground_img,
            person_x=person_x,
            person_y=person_y,
            person_scale=person_scale,
        )
        poster_bytes = save_png_bytes(poster)

        payload: dict[str, Any] = {
            "success": True,
            "job_id": job_id,
            "width": poster.width,
            "height": poster.height,
        }

        if save_to_storage and settings.AUTO_UPLOAD_OUTPUTS:
            stem = output_name or f"{template.get('templateId', 'poster')}-{int(time.time())}-{uuid.uuid4().hex[:6]}"
            path = f"{output_folder.rstrip('/')}/{stem}.png"
            uploaded = upload_bytes(path, poster_bytes, "image/png")
            payload["storage"] = uploaded
            insert_output_record(
                template_slug=template.get("templateId"),
                job_id=job_id,
                employee_name=text_values.get("name"),
                team_name=text_values.get("team"),
                award_title=text_values.get("awardTitle"),
                output_url=uploaded["public_url"],
                created_by=user.get("id") if user else None,
            )
        else:
            import base64
            payload["base64"] = base64.b64encode(poster_bytes).decode("utf-8")

        update_job(job_id, status="done", result_json=payload)
        return JSONResponse(payload)
    except Exception as exc:
        update_job(job_id, status="failed", error_message=str(exc))
        raise HTTPException(status_code=500, detail=f"Render poster lỗi: {exc}") from exc
