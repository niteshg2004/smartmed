from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings


class OCRUnavailableError(RuntimeError):
    """Raised when OCR cannot run (missing tesseract binary, etc.)."""


class OCRProcessingError(RuntimeError):
    """Raised when OCR is available but the file cannot be processed."""


@dataclass(frozen=True)
class OCRResult:
    text: str
    engine: str = "tesseract"


def _resolve_tesseract_cmd() -> str | None:
    configured = (getattr(settings, "OCR_PATH", "") or "").strip()
    if configured:
        return configured
    return shutil.which("tesseract")


def is_ocr_available() -> bool:
    return bool(_resolve_tesseract_cmd())


def ocr_file_to_text(file_path: str | Path) -> OCRResult:
    """
    Convert a prescription file (image) to text using pytesseract.

    Notes:
    - This function intentionally supports *images* only in the demo setup.
      PDF OCR would require additional system dependencies (e.g., Poppler).
    - Any caller must treat OCR output as untrusted and require user confirmation.
    """

    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        raise OCRProcessingError(
            "PDF OCR is not enabled in this demo environment. Please upload a JPG or PNG image."
        )

    cmd = _resolve_tesseract_cmd()
    if not cmd:
        raise OCRUnavailableError(
            "OCR is not available because the Tesseract binary is not installed/configured."
        )

    try:
        import pytesseract
        from PIL import Image
    except Exception as exc:  # pragma: no cover
        raise OCRUnavailableError("OCR libraries are not installed correctly.") from exc

    pytesseract.pytesseract.tesseract_cmd = cmd

    try:
        image = Image.open(path)
        # Normalize to RGB to reduce format-related errors.
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        text = pytesseract.image_to_string(image)
    except OCRUnavailableError:
        raise
    except Exception as exc:
        raise OCRProcessingError("Failed to extract text from the uploaded image.") from exc

    return OCRResult(text=text or "")

