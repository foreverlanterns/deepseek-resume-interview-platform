"""上传文件校验：扩展名、大小、文件头与 DOCX 结构。"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
SUPPORTED_SUFFIXES = {".pdf", ".docx"}


class ResumeFileError(Exception):
    """上传文件不合法。"""


class UnsupportedFileTypeError(ResumeFileError):
    """扩展名不在支持范围。"""


class FileTooLargeError(ResumeFileError):
    """文件超过大小限制。"""


class InvalidFileContentError(ResumeFileError):
    """扩展名与真实文件内容不匹配，或文件损坏。"""


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str
    suffix: str
    mime_type: str


def sanitize_filename(filename: str | None) -> str:
    """只保留文件名本身，去掉路径与控制字符，避免路径穿越。"""
    raw = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = "".join(char for char in raw if char.isprintable()).strip()
    if cleaned in {"", ".", ".."}:
        return "resume"
    return cleaned[:255]


def validate_upload(
    filename: str | None,
    data: bytes,
    *,
    max_size_bytes: int,
) -> ValidatedUpload:
    if not data:
        raise InvalidFileContentError("文件内容为空")

    if len(data) > max_size_bytes:
        max_mb = max(1, max_size_bytes // (1024 * 1024))
        raise FileTooLargeError(f"文件大小不能超过 {max_mb} MB")

    safe_name = sanitize_filename(filename)
    suffix = Path(safe_name).suffix.lower()

    if suffix == ".pdf":
        if not data[:1024].lstrip().startswith(b"%PDF-"):
            raise InvalidFileContentError("文件扩展名为 PDF，但内容不是有效的 PDF")
        return ValidatedUpload(filename=safe_name, suffix=suffix, mime_type=PDF_MIME)

    if suffix == ".docx":
        _validate_docx_container(data)
        return ValidatedUpload(filename=safe_name, suffix=suffix, mime_type=DOCX_MIME)

    raise UnsupportedFileTypeError("目前仅支持 PDF 和 DOCX 文件；图片简历的 OCR 将在后续阶段支持")


def _validate_docx_container(data: bytes) -> None:
    if not zipfile.is_zipfile(BytesIO(data)):
        raise InvalidFileContentError("文件扩展名为 DOCX，但内容不是有效的 Word 文档")

    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile as exc:
        raise InvalidFileContentError("DOCX 文件已损坏，无法读取") from exc

    if "word/document.xml" not in names or "[Content_Types].xml" not in names:
        raise InvalidFileContentError("DOCX 文件结构不完整，可能不是 Word 文档")
