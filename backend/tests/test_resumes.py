"""简历上传、文本提取与用户隔离集成测试。"""

from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path

import pymupdf
from docx import Document
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.resume import Resume

PASSWORD = "StrongPass123"


def make_pdf(
    text: str = (
        "Zhang San\nBackend Engineer\nPython FastAPI PostgreSQL Docker\nEmail: zhang@example.com"
    ),
) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    y = 72
    if text:
        for line in text.split("\n"):
            page.insert_text((72, y), line, fontsize=12)
            y += 20
    data = document.tobytes()
    document.close()
    return data


def make_encrypted_pdf() -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Encrypted resume", fontsize=12)
    data = document.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="owner-password",
        user_pw="user-password",
    )
    document.close()
    return data


def make_docx() -> bytes:
    document = Document()
    document.add_heading("张三", level=1)
    document.add_paragraph("后端开发工程师")
    document.add_paragraph("熟悉 Python、FastAPI、PostgreSQL 与 Docker。")
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def register_and_login(client: AsyncClient, email: str) -> str:
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "测试用户"},
    )
    assert register.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


async def upload_resume(
    client: AsyncClient,
    token: str,
    filename: str,
    data: bytes,
    content_type: str = "application/pdf",
) -> Response:
    return await client.post(
        "/api/v1/resumes/upload",
        headers=bearer(token),
        files={"file": (filename, data, content_type)},
    )


async def test_upload_pdf_extracts_text(auth_client: AsyncClient) -> None:
    token = await register_and_login(auth_client, "pdf@example.com")

    response = await upload_resume(auth_client, token, "resume.pdf", make_pdf())

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "extracted"
    assert body["original_filename"] == "resume.pdf"
    assert body["mime_type"] == "application/pdf"
    assert body["text_length"] > 0
    assert body["page_count"] == 1
    assert "Python" in body["text_preview"]
    assert len(body["sha256"]) == 64
    assert body["error_message"] is None


async def test_upload_docx_extracts_chinese_text(auth_client: AsyncClient) -> None:
    token = await register_and_login(auth_client, "docx@example.com")

    response = await upload_resume(
        auth_client,
        token,
        "resume.docx",
        make_docx(),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "extracted"
    assert "张三" in body["text_preview"]
    assert "FastAPI" in body["text_preview"]
    assert body["page_count"] is None


async def test_scanned_pdf_needs_ocr(auth_client: AsyncClient) -> None:
    token = await register_and_login(auth_client, "scan@example.com")

    response = await upload_resume(auth_client, token, "scan.pdf", make_pdf(""))

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "needs_ocr"
    assert body["text_length"] == 0
    assert "OCR" in body["error_message"]


async def test_encrypted_pdf_is_saved_as_failed(auth_client: AsyncClient) -> None:
    token = await register_and_login(auth_client, "encrypted@example.com")

    response = await upload_resume(
        auth_client,
        token,
        "encrypted.pdf",
        make_encrypted_pdf(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert "加密" in body["error_message"]


async def test_upload_rejects_unsupported_extension(auth_client: AsyncClient) -> None:
    token = await register_and_login(auth_client, "txt@example.com")

    response = await upload_resume(auth_client, token, "resume.txt", b"hello")

    assert response.status_code == 415
    assert "仅支持 PDF 和 DOCX" in response.json()["detail"]


async def test_upload_rejects_fake_pdf(auth_client: AsyncClient) -> None:
    token = await register_and_login(auth_client, "fake@example.com")

    response = await upload_resume(auth_client, token, "resume.pdf", b"not a real pdf")

    assert response.status_code == 400
    assert "不是有效的 PDF" in response.json()["detail"]


async def test_upload_rejects_oversized_file(auth_client: AsyncClient) -> None:
    token = await register_and_login(auth_client, "large@example.com")
    oversized = b"%PDF-" + b"0" * (10 * 1024 * 1024)

    response = await upload_resume(auth_client, token, "large.pdf", oversized)

    assert response.status_code == 413
    assert "10 MB" in response.json()["detail"]


async def test_filename_traversal_is_sanitized(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
) -> None:
    token = await register_and_login(auth_client, "path@example.com")

    response = await upload_resume(auth_client, token, "../../evil.pdf", make_pdf())

    assert response.status_code == 201
    assert response.json()["original_filename"] == "evil.pdf"

    result = await db_session.execute(select(Resume))
    resume = result.scalar_one()
    assert ".." not in Path(resume.stored_path).parts
    absolute_path = (settings.upload_path / resume.stored_path).resolve()
    assert absolute_path.is_relative_to(settings.upload_path.resolve())
    assert absolute_path.exists()


async def test_list_resumes_is_user_scoped(auth_client: AsyncClient) -> None:
    owner = await register_and_login(auth_client, "owner@example.com")
    other = await register_and_login(auth_client, "other@example.com")
    await upload_resume(auth_client, owner, "owner.pdf", make_pdf())
    await upload_resume(auth_client, owner, "owner.docx", make_docx())

    owner_list = await auth_client.get("/api/v1/resumes", headers=bearer(owner))
    other_list = await auth_client.get("/api/v1/resumes", headers=bearer(other))

    assert owner_list.status_code == 200
    assert {item["original_filename"] for item in owner_list.json()} == {
        "owner.pdf",
        "owner.docx",
    }
    assert other_list.status_code == 200
    assert other_list.json() == []


async def test_detail_and_delete_are_user_scoped(auth_client: AsyncClient) -> None:
    owner = await register_and_login(auth_client, "detail-owner@example.com")
    other = await register_and_login(auth_client, "detail-other@example.com")
    upload = await upload_resume(auth_client, owner, "private.pdf", make_pdf())
    resume_id = upload.json()["id"]

    other_detail = await auth_client.get(
        f"/api/v1/resumes/{resume_id}",
        headers=bearer(other),
    )
    other_delete = await auth_client.delete(
        f"/api/v1/resumes/{resume_id}",
        headers=bearer(other),
    )
    owner_detail = await auth_client.get(
        f"/api/v1/resumes/{resume_id}",
        headers=bearer(owner),
    )

    assert other_detail.status_code == 404
    assert other_delete.status_code == 404
    assert owner_detail.status_code == 200


async def test_delete_removes_record_and_file(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
) -> None:
    token = await register_and_login(auth_client, "delete@example.com")
    upload = await upload_resume(auth_client, token, "delete.pdf", make_pdf())
    resume_id = uuid.UUID(upload.json()["id"])

    result = await db_session.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one()
    absolute_path = settings.upload_path / resume.stored_path
    assert absolute_path.exists()

    response = await auth_client.delete(
        f"/api/v1/resumes/{resume_id}",
        headers=bearer(token),
    )

    assert response.status_code == 204
    assert response.content == b""
    assert not absolute_path.exists()

    db_session.expire_all()
    remaining = await db_session.execute(select(Resume).where(Resume.id == resume_id))
    assert remaining.scalar_one_or_none() is None


async def test_upload_and_list_require_auth(auth_client: AsyncClient) -> None:
    upload = await auth_client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", make_pdf(), "application/pdf")},
    )
    listing = await auth_client.get("/api/v1/resumes")

    assert upload.status_code == 401
    assert listing.status_code == 401
