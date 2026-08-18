"""FastAPI service for analyzing a public image or document with GPT."""

from urllib.parse import unquote, urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

from gemini_matcher import analyze_document_with_gpt, is_configured


CONDITION_PROMPT_EXAMPLE = """Check whether this document meets ALL of these conditions: (1) it is a bunker delivery note; (2) viscosity is present; and (3) a date is present. Return true only if every condition is clearly visible in the document. Return false if any condition is missing, unreadable, or cannot be verified. Do not infer information that is not visible."""


app = FastAPI(
    title="Document and Image Analysis API",
    description=(
        "Send a public image/document URL and a custom prompt to GPT-5.6 for "
        "flexible visual inspection, extraction, matching, or verification."
    ),
    version="2.0.0",
)


class AnalyzeDocumentRequest(BaseModel):
    url: str = Field(
        ...,
        description="Publicly accessible URL of the image or document to analyze.",
        examples=[
            "https://nauserver.com/Records/BunkerReceipt/BunkerReceipt-843-0502015358.pdf"
        ],
    )
    prompt: str = Field(
        ...,
        min_length=1,
        description=(
            "Instructions for GPT describing what to find, match, extract, or "
            "verify in the supplied image/document."
        ),
        examples=[CONDITION_PROMPT_EXAMPLE],
    )


class AnalyzeDocumentResponse(BaseModel):
    path: str = Field(description="URL path beginning with the Records segment.")
    verdict: bool = Field(
        description=(
            "True when the requested condition is satisfied or verification "
            "passes; otherwise false."
        )
    )


def _records_path(url: str) -> str:
    """Return the decoded URL path beginning at its Records segment."""
    path = unquote(urlparse(url).path).lstrip("/")
    segments = path.split("/")
    try:
        records_index = segments.index("Records")
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail="The URL path must contain a 'Records' segment.",
        ) from error
    return "/".join(segments[records_index:])


@app.post("/analyze-document", response_model=AnalyzeDocumentResponse)
def analyze_document(request: AnalyzeDocumentRequest) -> AnalyzeDocumentResponse:
    """Analyze an image or document using the caller's custom prompt.

    The example prompt in the request schema demonstrates how to list multiple
    required document conditions. Replace those conditions for each document
    type or workflow. The verdict is true only when all requested conditions
    are visibly satisfied.
    """
    if not is_configured():
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured on the server.",
        )

    try:
        path = _records_path(request.url)
        verdict = analyze_document_with_gpt(request.url, request.prompt)
        return AnalyzeDocumentResponse(path=path, verdict=verdict)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Could not process document: {error}"
        ) from error


@app.get("/health")
def health_check():
    return {"status": "ok"}
