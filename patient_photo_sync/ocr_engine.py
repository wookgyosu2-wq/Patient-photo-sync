"""OCR helpers for the Patient Photo Sync desktop automation.

The AutoHotkey version depended on ``OCR.ahk``.  This module replaces that
with Python OCR backends and keeps a single ``read_screen_rect`` API for the
rest of the application.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import os
from typing import Protocol

if importlib.util.find_spec("PIL") is not None:
    from PIL import Image, ImageGrab
else:  # pragma: no cover - exercised only on machines without Pillow
    Image = None
    ImageGrab = None

if importlib.util.find_spec("pytesseract") is not None:
    import pytesseract
else:  # pragma: no cover - exercised only on machines without pytesseract
    pytesseract = None


@dataclass(frozen=True)
class OcrResult:
    """Text recognized from a screen rectangle."""

    text: str


class OcrBackend(Protocol):
    """Protocol implemented by OCR backends."""

    def image_to_text(self, image: "Image.Image", language: str = "ko") -> str:
        """Return text detected in ``image``."""


class TesseractBackend:
    """OCR backend powered by the ``pytesseract`` Python wrapper.

    Tesseract itself must be installed on Windows and Korean trained data must
    be available for ``kor``.  If your executable is not on PATH, set the
    ``TESSERACT_CMD`` environment variable to its full path.
    """

    LANGUAGE_MAP = {
        "ko": "kor+eng",
        "kr": "kor+eng",
        "en": "eng",
    }

    def __init__(self) -> None:
        if pytesseract is None:
            raise RuntimeError("pytesseract is not installed. Run: pip install -r requirements.txt")

        tesseract_cmd = os.environ.get("TESSERACT_CMD")
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def image_to_text(self, image: "Image.Image", language: str = "ko") -> str:
        tess_lang = self.LANGUAGE_MAP.get(language.lower(), language)
        text = pytesseract.image_to_string(image, lang=tess_lang, config="--psm 6")
        return text.strip()


class OcrEngine:
    """Capture a screen rectangle and recognize text from it."""

    def __init__(self, backend: OcrBackend | None = None) -> None:
        if ImageGrab is None:
            raise RuntimeError("Pillow is required for screen capture. Run: pip install -r requirements.txt")
        self.backend = backend or TesseractBackend()

    def read_screen_rect(self, left: float, top: float, width: float, height: float, language: str = "ko") -> OcrResult:
        """Read text from a screen rectangle using screen coordinates."""

        bbox = (
            int(round(left)),
            int(round(top)),
            int(round(left + width)),
            int(round(top + height)),
        )
        image = ImageGrab.grab(bbox=bbox)
        return OcrResult(text=self.backend.image_to_text(image, language=language))
