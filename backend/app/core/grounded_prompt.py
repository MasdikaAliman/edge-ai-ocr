"""
Grounded Prompt Builder — Constructs fragment-tagged OCR context for VLM.

Instead of sending plain OCR text to the VLM, this module tags each fragment
with its Fragment ID so the VLM can reference specific fragments in its output.
This eliminates the need for post-hoc fuzzy matching.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.fragment_store import FragmentStore


def build_grounded_context(store: "FragmentStore", page_no: int) -> str:
    """
    Build a fragment-tagged OCR context string for a specific page.

    Output format (one fragment per line):
        [F0001] NIK
        [F0002] 3173010203040001
        [F0003] Nama
        [F0004] BUDI SANTOSO

    Fragments are ordered top-to-bottom, left-to-right to preserve
    the visual document layout.
    """
    fragments = store.get_page(page_no)
    if not fragments:
        return ""

    # Sort by vertical position (y), then horizontal position (x)
    sorted_frags = sorted(
        fragments,
        key=lambda f: (round(f.bbox[1] / 10) * 10, f.bbox[0])
    )

    lines = []
    for frag in sorted_frags:
        lines.append(f"[{frag.id}] {frag.text}")

    return "\n".join(lines)


GROUNDED_OUTPUT_INSTRUCTION = """
GROUNDED OUTPUT FORMAT:
- For EVERY extracted field, you MUST return an object with "value" and "sources".
- "value": The extracted text value (string, number, or null).
- "sources": A list of Fragment IDs (e.g. ["F0002"]) that contain the source text.
- If the value comes from multiple fragments, list ALL relevant Fragment IDs.
- If a field cannot be found, return {"value": null, "sources": []}.
- Fragment IDs are the tags in square brackets (e.g. [F0001]) shown in the OCR context.
- Do NOT invent Fragment IDs. Only use IDs that appear in the OCR context.

EXAMPLE INPUT:
[F0001] NIK
[F0002] 3173010203040001
[F0003] Nama
[F0004] BUDI SANTOSO

EXAMPLE OUTPUT:
{
  "nik": {"value": "3173010203040001", "sources": ["F0002"]},
  "nama": {"value": "BUDI SANTOSO", "sources": ["F0004"]}
}

MULTI-FRAGMENT EXAMPLE:
If the address spans multiple fragments:
[F0010] JL MELATI
[F0011] NO 10
[F0012] RT 05 RW 03

Output:
{
  "alamat": {"value": "JL MELATI NO 10", "sources": ["F0010", "F0011"]},
  "rt": {"value": "05", "sources": ["F0012"]},
  "rw": {"value": "03", "sources": ["F0012"]}
}

TABLE/ARRAY FIELDS:
For table rows, each cell value should also have "value" and "sources":
{
  "table": [
    {
      "item_number": {"value": "1", "sources": ["F0050"]},
      "description": {"value": "Widget A", "sources": ["F0051"]},
      "quantity": {"value": "100", "sources": ["F0052"]}
    }
  ]
}
"""


def get_grounded_output_instruction() -> str:
    """Return the grounded output instruction block to be appended to prompts."""
    return GROUNDED_OUTPUT_INSTRUCTION


GROUNDED_REMINDER = """
CRITICAL: Output MUST use grounded format:
{"field": {"value": "...", "sources": ["F000X"]}}

Example from above context:
{"nik": {"value": "910001", "sources": ["F0003"]}}
"""