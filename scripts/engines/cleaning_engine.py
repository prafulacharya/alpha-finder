"""Cleaning Engine - Normalizes and cleans document data."""

from __future__ import annotations

import re
from pathlib import Path

import fitz

from ..utils import Config, DocumentProcessingError


class CleaningEngine:
    """Cleans and normalizes document content."""
    
    def __init__(self, config: Config) -> None:
        self.config = config

    @staticmethod
    def extract_pdf_text(path: Path) -> str:
        """Extract text from PDF file."""
        try:
            with fitz.open(path) as document:
                return "\n".join(page.get_text() for page in document)
        except Exception as exc:
            raise DocumentProcessingError(f"Failed to extract PDF: {path}") from exc

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalize excessive whitespace."""
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text for analysis."""
        # Normalize line breaks and whitespace
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\n\s+\n", "\n\n", text)  # Remove extra blank lines
        text = re.sub(r"[ \t]+", " ", text)      # Collapse multiple spaces/tabs
        return text.strip()

    @staticmethod
    def extract_snippet(text: str, match: re.Match[str], radius: int = 150) -> str:
        """Extract context snippet around match."""
        start = max(0, match.start() - radius)
        end = min(len(text), match.end() + radius)
        snippet = text[start:end]
        return re.sub(r"\s+", " ", snippet).strip()

    def prepare_for_analysis(self, text: str) -> str:
        """Prepare text for analysis."""
        return self.clean_text(text).lower()
