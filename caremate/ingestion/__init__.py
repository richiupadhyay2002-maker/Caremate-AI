"""Document ingestion pipeline — extraction, classification, and upload handling."""

from caremate.ingestion.extractor import DocumentExtractor, ExtractedPage
from caremate.ingestion.classifier import DocumentClassifier, classify_document

__all__ = [
    "DocumentExtractor",
    "ExtractedPage",
    "DocumentClassifier",
    "classify_document",
]
