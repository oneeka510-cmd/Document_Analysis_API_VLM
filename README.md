# Document & Image Analysis API

A FastAPI service that checks whether a publicly hosted document or image satisfies a set of caller-defined conditions, using a vision-capable GPT model for structured, prompt-based verification.

## Why

Plain OCR reads characters, not layout — scanned tables, forms, and mixed-content documents (like bunker delivery notes) often confuse it. This service sends the document directly to a VLM, which understands structure the way a human reviewer would, and returns a strict `true`/`false` verdict for the given conditions.

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
