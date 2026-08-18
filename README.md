# Document & Image Analysis API

A drop-in reasoning layer for verifying documents. Send a public document/image URL plus a plain-English prompt describing what to check, and get back a strict `true`/`false` verdict — no fixed schema or document type required, so any project needing human-style judgment on a document can call it as-is.

## Why

Plain OCR reads characters, not layout — scanned tables, forms, and mixed-content documents often confuse it, and rule-based checks can't handle "does this look right" judgment calls. This service sends the document directly to a VLM, which reads it the way a human reviewer would and reasons about whether the caller's conditions are actually met, rather than pattern-matching on exact text.

Because the conditions are just a prompt (not hardcoded fields), the same endpoint works for one document type today and a completely different one tomorrow — swap the prompt, not the code.

## Use cases

Any workflow that currently relies on a person eyeballing a document can point at this endpoint instead:

- Verifying uploaded documents meet compliance/format requirements before they're accepted
- Checking that a specific value, field, or clause is present (and within tolerance) in a scanned form
- Gatekeeping automated pipelines — only proceed if the document passes a human-style check
- Flagging documents that need manual review instead of silently failing

Since the check is defined entirely by the prompt in the request body, it doesn't need to know about your document type ahead of time — no retraining, no per-document-type code path.

This was built for maritime documents (bunker delivery notes, receipts, certificates), but nothing in the reasoning logic is maritime-specific. To adapt it to your own use case:

- **`CONDITION_PROMPT_EXAMPLE` in `main.py`** — this is just the example shown in the Swagger docs. Replace it with conditions relevant to your documents.
- **`_records_path()` in `main.py`** — this assumes every URL contains a `Records` path segment (specific to how documents are stored in this maritime setup) and returns a 422 if it's missing. If your URLs don't follow that structure, remove this function and the `path` field from `AnalyzeDocumentResponse`, and just return the URL itself (or drop the field entirely).
- **`SUPPORTED_EXTENSIONS_FOR_OPENAI` in `matcher.py`** — already generic (PDFs, images, Word docs); trim or extend based on what file types you expect.
- **`MODEL_NAME` in `matcher.py`** — swap if you want a different model.

Everything else — the prompt/bracket handling, the strict-schema boolean verdict, the FastAPI route shape — works as-is regardless of domain.

## How it works

1. The caller sends a public document/image URL and a plain-English prompt describing the conditions to check.
2. The prompt can include **bracketed guidance** next to any condition — e.g. `viscosity is present and around 210 [+-10 is okay]` — to give the model tolerances or alternate phrasing to look for, without turning it into a separate condition.
3. The model's response is constrained by a strict JSON schema (`{"verdict": bool}`), so the API can never return anything other than a genuine boolean.

## Example

```json
POST /analyze-document
{
  "url": "https://example.com/Records/BunkerReceipt/BunkerReceipt-843.pdf",
  "prompt": "Check whether this document meets ALL of these conditions: (1) it is a bunker delivery note [look for words like bunker analysis, bunker fuel, and use your own reasoning - not only these exact words]; (2) viscosity is present and around 210 [+-10 is okay]; and (3) a date is present [+- 10 hrs is allowed]. Return true only if every condition is clearly visible in the document."
}
```

```json
{
  "path": "Records/BunkerReceipt/BunkerReceipt-843.pdf",
  "verdict": true
}
```

## Stack

- **FastAPI** for the HTTP layer
- **OpenAI API** (structured outputs / JSON schema) for the verdict
- **Pydantic** for request/response validation

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```
OPENAI_API_KEY=your_key_here
```

Run the service:

```bash
uvicorn main:app --reload
```

Interactive API docs are available at `/docs`.

## Project structure

```
main.py     # FastAPI routes and request/response models
matcher.py  # OpenAI call, MIME detection, verdict parsing
```

## Error handling

- **422** — the supplied URL doesn't contain the expected `Records` path segment
- **500** — misconfiguration (missing API key) or a failure calling OpenAI

## Limitations

- Only works with **publicly accessible** URLs — the API references the URL directly rather than downloading the file.
