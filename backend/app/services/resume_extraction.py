"""PDF / DOCX 文本提取与清洗。"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from docx import Document

from app.models.resume import ResumeStatus

logger = logging.getLogger(__name__)

MIN_PDF_TEXT_CHARS = 50
MAX_TEXT_CHARS = 200_000
_SPACE_RE = re.compile(r"[ \t\u00a0]+")


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    page_count: int | None
    status: str
    error_message: str | None


def clean_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for raw_line in text.split("\n"):
        line = _SPACE_RE.sub(" ", raw_line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)[:MAX_TEXT_CHARS]


def extract_text(path: Path, suffix: str) -> ExtractionResult:
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix == ".docx":
        return _extract_docx(path)
    return ExtractionResult(
        text="",
        page_count=None,
        status=ResumeStatus.FAILED.value,
        error_message="不支持的文件类型",
    )


def _extract_pdf(path: Path) -> ExtractionResult:
    try:
        with pymupdf.open(path) as document:
            if document.needs_pass:
                return ExtractionResult(
                    text="",
                    page_count=None,
                    status=ResumeStatus.FAILED.value,
                    error_message="PDF 已加密，请先解除密码后重新上传",
                )
            pages = [page.get_text("text") for page in document]
            page_count = document.page_count
    except Exception:  # noqa: BLE001 - 第三方解析器的异常类型不稳定
        logger.exception("PDF 文本提取失败")
        return ExtractionResult(
            text="",
            page_count=None,
            status=ResumeStatus.FAILED.value,
            error_message="PDF 解析失败，文件可能已损坏或加密",
        )

    text = clean_text("\n".join(pages))
    if len(text) < MIN_PDF_TEXT_CHARS:
        return ExtractionResult(
            text=text,
            page_count=page_count,
            status=ResumeStatus.NEEDS_OCR.value,
            error_message="未检测到足够的文本，可能是扫描件；OCR 将在后续阶段支持",
        )

    return ExtractionResult(
        text=text,
        page_count=page_count,
        status=ResumeStatus.EXTRACTED.value,
        error_message=None,
    )


def _extract_docx(path: Path) -> ExtractionResult:
    try:
        document = Document(path)
        parts = [paragraph.text for paragraph in document.paragraphs]
        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                if any(cells):
                    parts.append(" | ".join(cells))
    except Exception:  # noqa: BLE001 - 第三方解析器的异常类型不稳定
        logger.exception("DOCX 文本提取失败")
        return ExtractionResult(
            text="",
            page_count=None,
            status=ResumeStatus.FAILED.value,
            error_message="DOCX 解析失败，文件可能已损坏",
        )

    text = clean_text("\n".join(parts))
    if not text:
        return ExtractionResult(
            text="",
            page_count=None,
            status=ResumeStatus.FAILED.value,
            error_message="DOCX 中未提取到文本内容",
        )

    return ExtractionResult(
        text=text,
        page_count=None,
        status=ResumeStatus.EXTRACTED.value,
        error_message=None,
    )
