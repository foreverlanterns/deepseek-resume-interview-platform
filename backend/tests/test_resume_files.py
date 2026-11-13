"""上传文件校验单元测试。"""

from __future__ import annotations

from io import BytesIO

import pytest
from docx import Document

from app.services.resume_files import (
    FileTooLargeError,
    InvalidFileContentError,
    UnsupportedFileTypeError,
    sanitize_filename,
    validate_upload,
)

PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n"


def make_docx_bytes() -> bytes:
    document = Document()
    document.add_paragraph("张三")
    document.add_paragraph("Python FastAPI")
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_sanitize_filename_removes_paths() -> None:
    assert sanitize_filename("../../evil.pdf") == "evil.pdf"
    assert sanitize_filename("..\\..\\evil.docx") == "evil.docx"
    assert sanitize_filename("") == "resume"


def test_accepts_valid_pdf() -> None:
    result = validate_upload("resume.pdf", PDF_BYTES, max_size_bytes=1024 * 1024)
    assert result.filename == "resume.pdf"
    assert result.suffix == ".pdf"
    assert result.mime_type == "application/pdf"


def test_accepts_valid_docx() -> None:
    result = validate_upload("resume.docx", make_docx_bytes(), max_size_bytes=1024 * 1024)
    assert result.suffix == ".docx"
    assert result.mime_type.endswith("wordprocessingml.document")


def test_rejects_unsupported_extension() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        validate_upload("resume.txt", b"hello", max_size_bytes=1024 * 1024)


def test_rejects_fake_pdf_header() -> None:
    with pytest.raises(InvalidFileContentError):
        validate_upload("resume.pdf", b"not a pdf", max_size_bytes=1024 * 1024)


def test_rejects_fake_docx_container() -> None:
    with pytest.raises(InvalidFileContentError):
        validate_upload("resume.docx", b"PK\x03\x04not-a-zip", max_size_bytes=1024 * 1024)


def test_rejects_empty_file() -> None:
    with pytest.raises(InvalidFileContentError):
        validate_upload("resume.pdf", b"", max_size_bytes=1024 * 1024)


def test_rejects_oversized_file() -> None:
    with pytest.raises(FileTooLargeError):
        validate_upload("resume.pdf", PDF_BYTES + b"0" * (1024 * 1024), max_size_bytes=1024 * 1024)
