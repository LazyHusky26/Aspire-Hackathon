import os
import re
from typing import Optional


def read_text_from_file(file_path: str) -> str:
	"""Return extracted plain text from PDF, DOCX, or TXT. Best-effort cleanup."""
	text = ""
	lower = file_path.lower()
	if lower.endswith(".pdf"):
		text = _read_pdf(file_path)
	elif lower.endswith(".docx"):
		text = _read_docx(file_path)
	elif lower.endswith(".txt"):
		with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
			text = f.read()
	else:
		raise ValueError(f"Unsupported file type: {os.path.basename(file_path)}")
	return _basic_cleanup(text)


def _basic_cleanup(text: str) -> str:
	# Enhanced text cleanup for better parsing
	if not text:
		return ""
	
	# Fix common PDF extraction issues
	text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)  # Add space between camelCase
	text = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", text)  # Add space between letters and numbers
	text = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", text)  # Add space between numbers and letters
	
	# Normalize whitespace and special characters
	text = re.sub(r"[^\S\n]+", " ", text)  # Replace multiple spaces/tabs with single space
	text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)  # Normalize multiple newlines
	
	# Fix common encoding issues
	replacements = {
		"\u00e2\u0080\u0099": "'",  # Smart apostrophe
		"\u00e2\u0080\u009c": '"',  # Left double quote
		"\u00e2\u0080\u009d": '"',  # Right double quote
		"\u00e2\u0080\u00a2": "•",  # Bullet point
		"\u00e2\u0080\u0093": "-",  # En dash
		"\u00e2\u0080\u0094": "-",  # Em dash
		"\u00c2": "",               # Non-breaking space artifact
		"\u00e2": ""                # General encoding artifact
	}
	for old, new in replacements.items():
		text = text.replace(old, new)
	
	# Clean up lines
	lines = []
	for line in text.splitlines():
		line = line.strip()
		if line:  # Only keep non-empty lines
			lines.append(line)
	
	return "\n".join(lines)


def _read_pdf(file_path: str) -> str:
	"""Try PyMuPDF first, fallback to pdfplumber."""
	try:
		import fitz  # PyMuPDF
		doc = fitz.open(file_path)
		chunks = []
		for page in doc:
			chunks.append(page.get_text("text"))
		return "\n".join(chunks)
	except Exception:
		pass
	try:
		import pdfplumber
		text_parts = []
		with pdfplumber.open(file_path) as pdf:
			for page in pdf.pages:
				text_parts.append(page.extract_text() or "")
		return "\n".join(text_parts)
	except Exception:
		return ""


def _read_docx(file_path: str) -> str:
	try:
		from docx import Document
		doc = Document(file_path)
		paras = [p.text for p in doc.paragraphs]
		return "\n".join(paras)
	except Exception:
		return ""

