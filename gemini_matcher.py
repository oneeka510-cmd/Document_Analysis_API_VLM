"""
gemini_matcher.py
------------------
Analyzes a public image or document using a caller-supplied prompt and
OpenAI's GPT model.

Why this exists: plain OCR (Tesseract) struggles specifically on
scanned tables/forms - it reads characters without understanding
layout, so table borders, columns, and cell structure often confuse
it. A VLM looks at the page more like a human would, understanding
structure directly, which avoids that whole category of failure.

This only works for documents reachable at a public URL - OpenAI can
reference a public document/image URL directly without us needing to
download it first.
"""

import json
import mimetypes
import os

from openai import OpenAI

MODEL_NAME = "gpt-5.6"

# File extensions accepted as public image or document inputs.
SUPPORTED_EXTENSIONS_FOR_OPENAI = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
}


def is_configured() -> bool:
    """Checks whether an OpenAI API key is available."""
    return bool(os.environ.get("OPENAI_API_KEY"))


def _guess_mime_type(document_url: str) -> str:
    """
    Figures out the MIME type (e.g. "application/pdf") from the
    document URL's file extension, so OpenAI knows how to interpret it.
    """
    extension = os.path.splitext(document_url.split("?")[0])[1].lower()

    if extension in SUPPORTED_EXTENSIONS_FOR_OPENAI:
        return SUPPORTED_EXTENSIONS_FOR_OPENAI[extension]

    # Fall back to Python's built-in guesser for anything not in our
    # explicit list above, in case a valid-but-uncommon type comes through.
    guessed_type, _ = mimetypes.guess_type(document_url)
    if guessed_type:
        return guessed_type

    raise ValueError(f"Could not determine file type for URL: {document_url}")


def analyze_document_with_gpt(document_url: str, prompt: str) -> bool:
    """Evaluate a public image/document against a prompt and return its verdict."""
    if not is_configured():
        raise RuntimeError("OPENAI_API_KEY is not configured")

    mime_type = _guess_mime_type(document_url)
    if mime_type.startswith("image/"):
        document_input = {"type": "input_image", "image_url": document_url}
    else:
        document_input = {
            "type": "input_file",
            "file_url": document_url,
        }

    try:
        client = OpenAI()
        response = client.responses.create(
            model=MODEL_NAME,
            input=[
                {
                    "role": "developer",
                    "content": (
                        "Evaluate the attached document against the user's prompt. "
                        "Set verdict to true only when the requested condition is "
                        "visibly satisfied or the requested verification passes; "
                        "otherwise set it to false."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        document_input,
                    ],
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "document_verdict",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {"verdict": {"type": "boolean"}},
                        "required": ["verdict"],
                        "additionalProperties": False,
                    },
                }
            },
        )
        return bool(json.loads(response.output_text)["verdict"])

    except Exception as error:
        raise RuntimeError(f"OpenAI check failed: {error}") from error
