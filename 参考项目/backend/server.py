from __future__ import annotations

import io
from typing import Dict, List, Optional, Tuple

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader


app = FastAPI(title="Assembly BOM Parser", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


class BomItem(BaseModel):
    index: Optional[int]
    code: str
    name: str
    quantity: Optional[int]
    weight: Optional[float]
    raw: str
    source: str


class ParseResponse(BaseModel):
    items: List[BomItem]
    stats: Dict[str, int]


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/parse-bom", response_model=ParseResponse)
async def parse_bom(files: List[UploadFile] = File(...)) -> ParseResponse:
    all_items: List[BomItem] = []
    stats: Dict[str, int] = {}
    for up in files:
        content = await up.read()
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(filter(None, (page.extract_text() or "" for page in reader.pages)))
        entries = extract_bom_items(text)
        for entry in entries:
            all_items.append(BomItem(source=up.filename, **entry))
        stats[up.filename] = len(entries)
    return ParseResponse(items=all_items, stats=stats)


def extract_bom_items(raw_text: str) -> List[Dict[str, Optional[str]]]:
    items: List[Dict[str, Optional[str]]] = []
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        tokens = line.split()
        if len(tokens) < 4 or not tokens[0].isdigit():
            continue
        index = int(tokens[0])
        code = tokens[1]
        if not _looks_like_code(code):
            continue
        qty_info = _find_last_int(tokens)
        weight_info = _find_last_float(tokens)
        desc_end = len(tokens)
        if qty_info:
            desc_end = min(desc_end, qty_info[1])
        elif weight_info:
            desc_end = min(desc_end, weight_info[1])
        name_tokens = tokens[2:desc_end]
        if not name_tokens:
            name_tokens = tokens[1:desc_end]
        items.append(
            {
                "index": index,
                "code": code,
                "name": " ".join(name_tokens),
                "quantity": qty_info[0] if qty_info else None,
                "weight": weight_info[0] if weight_info else None,
                "raw": line,
            }
        )
    return items


def _looks_like_code(token: str) -> bool:
    if any(ch.isalpha() for ch in token):
        return True
    return any(ch in "-_.*/" for ch in token)


def _find_last_int(tokens: List[str]) -> Optional[Tuple[int, int]]:
    for idx in range(len(tokens) - 1, -1, -1):
        if tokens[idx].isdigit():
            return int(tokens[idx]), idx
    return None


def _find_last_float(tokens: List[str]) -> Optional[Tuple[float, int]]:
    for idx in range(len(tokens) - 1, -1, -1):
        tok = tokens[idx]
        if any(ch.isdigit() for ch in tok):
            try:
                return float(tok.replace(",", "")), idx
            except ValueError:
                continue
    return None
