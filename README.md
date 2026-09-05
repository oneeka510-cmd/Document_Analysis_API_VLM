# Document Consistency API

A FastAPI service that checks whether a publicly hosted document or image satisfies a set of caller-defined conditions, using a vision-capable GPT model for structured, prompt-based verification.

## Use Cases
This API is intended to act as a verification layer between document-heavy workflows and the systems that store their structured data.

Instead of:
```Upload → Store → Trust```
you can build:
```Upload → Verify → Store```

```Invoices - verify vendor, amount, tax, date, quantity
Purchase Orders                verify PO number, products, prices, quantities
Receipts & Expenses            verify claimed values against receipts
Certificates & Licenses        verify identity, validity, expiry dates
Delivery & Shipping Documents  verify shipment details, quantities, dates
Compliance & Audit Documents   verify required information and conditions
Contracts & Legal Documents    verify parties, dates, amounts, clauses
Custom Business Documents      define your own conditions and expected values
```

Core idea: Apply the same verification rules across thousands of documents while the expected values change for each record.

## Why

If users are uploading documents and typing in values against them, you can't fully trust what they entered - and once you're dealing with thousands of records, checking each document manually against its entered values just isn't feasible.

I built this to solve exactly that. Point it at the uploaded document and describe what values it should contain, and you get back a consistent, structured verdict - true or false, plus exactly what didn't match - instead of manually re-verifying record by record.

One place this holds up well: invoice verification, where an invoice is uploaded alongside entered values like vendor name, invoice amount, quantity, and date across thousands of records. A mismatch here isn't cosmetic - it can lead to incorrect payments, accounting errors, or financial loss. Catching these discrepancies after the fact means manually checking every invoice against its entered values. Wire this API into the document workflow instead, and each record gets a clear pass or fail without the manual sweep.

Try it with your own documents and conditions using the example prompts below, or see the demo frontend for a live walkthrough.
This service sends the document directly to a VLM, which understands structure the way a human reviewer would, and returns a strict `true`/`false` verdict for the given conditions - along with the specific reasons behind any failure.

## How it works

1. The caller sends a public document/image URL and a plain-English prompt describing the conditions to check.
2. The prompt can include **bracketed guidance** next to any condition - e.g. `viscosity is present and around 210 [+-10 is okay]` - to give the model tolerances or alternate phrasing to look for, without turning it into a separate condition.
3. The model's response is constrained by a strict JSON schema (`{"verdict": bool, "unmatched": [str]}`), so the API can never return anything other than a genuine boolean plus a list of reasons for any condition that failed.
4. If any condition isn't satisfied, the model explains why in plain English (e.g. `"Date not found in document, expected 29 Nov 2020"`). The API joins these into a single `unmatched` string, separated by `;` when more than one condition failed.

## Example

**Request:**
```json
POST /analyze-document
{
  "url": "https://example.com/Records/BReceipt/Receipt-843.pdf",
  "prompt": "Check whether this document meets ALL of these conditions: (1) it is a bunker delivery note [look for words like bunker analysis, bunker fuel, and use your own reasoning - not only these exact words]; (2) viscosity is present and around 210 [+-10 is okay]; and (3) a date is present [+- 10 hrs is allowed]. Return true only if every condition is clearly visible in the document."
}
```

**All conditions matched:**
```json
{
  "path": "Records/BReceipt/Receipt-843.pdf",
  "verdict": true,
  "unmatched": ""
}
```

**One or more conditions failed:**
```json
{
  "path": "Records/BReceipt/Receipt-843.pdf",
  "verdict": false,
  "unmatched": "Date not found in document, expected within 10 hours of the target date; Viscosity found is 195, expected around 210"
}
```

## Why use this API instead of calling OpenAI directly?
The value is convenience and consistency for anyone integrating document checks into their own project.

- **No schema design required.** Getting a VLM to reliably return a clean, typed `{"verdict": bool, "unmatched": [...]}` - not prose, not inconsistent formatting - already took real trial and error (structured outputs, strict schema, a developer prompt explaining the bracket convention). Callers just send a URL and prompt.
- **Consistent, predictable errors.** A caller gets a clean `422` for a bad URL or `500` with a clear message, instead of a raw OpenAI exception they'd have to interpret themselves.
- **Centralized behavior.** Swapping models, adjusting the prompt, or fixing a bug benefits every caller instantly, without them touching their own code.

This mainly pays off when **multiple callers or services** need the same document-verification behavior - for a single one-off use case with full control over the code, calling OpenAI directly is simpler.

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
matcher.py  # OpenAI call, MIME detection, verdict + unmatched-reasons parsing
```

## Response fields

| Field | Type | Description |
|---|---|---|
| `path` | string | URL path beginning with the `Records` segment |
| `verdict` | boolean | `true` only when every condition in the prompt is satisfied |
| `unmatched` | string | Reasons for any conditions that weren't matched, separated by `;`. Empty when `verdict` is `true` |

## Error handling

- **422** - the supplied URL doesn't contain the expected `Records` path segment
- **500** - misconfiguration (missing API key) or a failure calling OpenAI


## Limitations

- Only works with **publicly accessible** URLs - the API references the URL directly rather than downloading the file.

  
