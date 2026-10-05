"""Document text extraction with PDF support and OCR fallback.

For text-based PDFs, pypdf extracts embedded text directly.
For scanned PDFs or image files, pytesseract OCR is used as a fallback.

Extraction is done per-page so that provenance (page_number) is preserved.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from caremate.utils.config import get_logger

logger = get_logger(__name__)

# Supported file extensions
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif"}


@dataclass
class ExtractedPage:
    """A single page of extracted text with provenance metadata.

    Attributes:
        text: The extracted text content.
        page_number: 1-based page number in the source document.
        confidence: Mean OCR confidence (0.0-1.0). None for native PDF text.
        source: How the text was extracted ("native_pdf" or "ocr").
    """
    text: str
    page_number: int
    confidence: Optional[float] = None
    source: str = "native_pdf"


class DocumentExtractor:
    """Extracts text from PDFs and images with OCR fallback.

    Uses pypdf for native PDF text extraction. Falls back to
    pytesseract OCR for scanned PDFs and standalone image files.

    If Tesseract is not installed on the system, OCR methods raise a
    clear error so callers can handle the degradation gracefully.
    """

    def __init__(self):
        self._tesseract_available = self._check_tesseract()
        if not self._tesseract_available:
            logger.warning(
                "Tesseract OCR binary not found on PATH - OCR will be "
                "unavailable. Install Tesseract for scanned document support."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def extract(self, file_path: str) -> list[ExtractedPage]:
        """Extract text from a file, returning one ExtractedPage per page.

        Auto-detects file type and routes to the appropriate extractor.

        Raises:
            ValueError: If the file extension is not supported.
            FileNotFoundError: If the file does not exist.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext in PDF_EXTENSIONS:
            return self._extract_pdf(file_path)
        elif ext in IMAGE_EXTENSIONS:
            return self._extract_image(file_path)
        else:
            raise ValueError(
                f"Unsupported file extension: \'{ext}\'. "
                f"Allowed: {sorted(PDF_EXTENSIONS | IMAGE_EXTENSIONS)}"
            )

    def extract_text(self, file_path: str) -> str:
        """Convenience: extract full text (all pages joined)."""
        pages = self.extract(file_path)
        return "\n".join(p.text for p in pages)

    @property
    def ocr_available(self) -> bool:
        """Whether Tesseract OCR is usable on this system."""
        return self._tesseract_available

    # ------------------------------------------------------------------
    # Internal: file-type dispatch
    # ------------------------------------------------------------------
    def _extract_pdf(self, file_path: str) -> list[ExtractedPage]:
        """Extract text from a PDF, using OCR for pages with no native text."""
        from pypdf import PdfReader

        try:
            reader = PdfReader(file_path)
        except Exception as exc:
            logger.error("Failed to open PDF %s: %s", file_path, exc)
            raise ValueError(f"Cannot read PDF: {exc}") from exc

        pages: list[ExtractedPage] = []
        for i, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                logger.warning("Failed to extract page %d from %s: %s", i, file_path, exc)
                text = ""

            text = text.strip()
            if text:
                pages.append(ExtractedPage(text=text, page_number=i, source="native_pdf"))
            elif self._tesseract_available:
                ocr_text, ocr_conf = self._ocr_pdf_page(file_path, i)
                if ocr_text.strip():
                    pages.append(ExtractedPage(
                        text=ocr_text, page_number=i, confidence=ocr_conf, source="ocr",
                    ))
                else:
                    pages.append(ExtractedPage(text="", page_number=i, source="ocr"))
            else:
                pages.append(ExtractedPage(text="", page_number=i, source="native_pdf"))

        if not pages:
            logger.warning("PDF %s contained 0 pages", file_path)
        return pages

    def _extract_image(self, file_path: str) -> list[ExtractedPage]:
        """Extract text from a single-page image using OCR."""
        if not self._tesseract_available:
            raise RuntimeError(
                "Tesseract OCR is not installed. Cannot extract text from images "
                "without a fallback PDF text layer."
            )
        text, confidence = self._ocr_image_file(file_path)
        return [ExtractedPage(text=text, page_number=1, confidence=confidence, source="ocr")]

    # ------------------------------------------------------------------
    # Internal: OCR helpers
    # ------------------------------------------------------------------
    def _check_tesseract(self) -> bool:
        """Check whether the Tesseract binary is available on PATH."""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def _ocr_image_file(self, file_path: str) -> tuple[str, Optional[float]]:
        """OCR a single image file, returning (text, mean_confidence)."""
        import pytesseract
        from PIL import Image

        img = Image.open(file_path)
        processed = self._preprocess_image(img)
        text = pytesseract.image_to_string(processed)

        try:
            data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)
            confidences = [c for c in data.get("conf", []) if isinstance(c, (int, float)) and c >= 0]
            mean_conf = sum(confidences) / len(confidences) / 100.0 if confidences else None
        except Exception:
            mean_conf = None

        return text.strip(), mean_conf

    def _ocr_pdf_page(self, pdf_path: str, page_number: int) -> tuple[str, Optional[float]]:
        """OCR a single page of a PDF by rendering it to an image."""
        try:
            from pdf2image import convert_pdf_to_image  # type: ignore
        except ImportError:
            logger.error("pdf2image is not installed - cannot OCR PDF page %d", page_number)
            return "", None

        try:
            images = convert_pdf_to_image(
                pdf_path,
                first_page=page_number,
                last_page=page_number,
            )
            if images:
                import pytesseract
                from PIL import Image
                img = images[0]
                processed = self._preprocess_image(img)
                text = pytesseract.image_to_string(processed)
                try:
                    data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)
                    confidences = [c for c in data.get("conf", [])
                                   if isinstance(c, (int, float)) and c >= 0]
                    mean_conf = sum(confidences) / len(confidences) / 100.0 if confidences else None
                except Exception:
                    mean_conf = None
                return text.strip(), mean_conf
            return "", None
        except Exception as exc:
            logger.error("OCR failed for page %d of %s: %s", page_number, pdf_path, exc)
            return "", None

    @staticmethod
    def _preprocess_image(img) -> "object":
        """Apply grayscale + threshold to improve OCR accuracy."""
        from PIL import Image, ImageOps

        if img.mode != "RGB":
            img = img.convert("RGB")
        gray = ImageOps.grayscale(img)
        try:
            import numpy as np
            arr = np.array(gray)
            binary_img = Image.fromarray(np.where(arr > arr.mean() * 0.7, 255, 0).astype("uint8"))
            return binary_img
        except Exception:
            return gray
