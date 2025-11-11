"""Utility for scanning CAD/PDF uploads and preparing data for the assembly prototype."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import textwrap
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from pypdf import PdfReader  # type: ignore
except ImportError:  # pragma: no cover
    PdfReader = None


@dataclass
class PdfExtraction:
    path: str
    page_count: int
    preview: str
    bom_items: List[Dict[str, Any]]
    items: List[Dict[str, Any]]


@dataclass
class CadConversionStatus:
    path: str
    status: str
    message: str
    generated_files: List[str]


def main() -> None:
    parser = argparse.ArgumentParser(description="Process CAD/PDF uploads for assembly pipeline")
    parser.add_argument("input_dir", nargs="?", default=".", help="Root directory to scan")
    parser.add_argument("--output", "-o", default="processing/output", help="Directory to place reports")
    parser.add_argument("--placeholder-glb", default="model.glb", help="Fallback GLB used when conversion is missing")
    args = parser.parse_args()

    root = Path(args.input_dir).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_out_dir = output_dir / "pdf"
    cad_out_dir = output_dir / "cad"
    pdf_out_dir.mkdir(parents=True, exist_ok=True)
    cad_out_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "root": str(root),
        "pdf_reports": [],
        "cad_reports": [],
    }

    for pdf_path in iter_files(root, (".pdf",)):
        report = handle_pdf(pdf_path, pdf_out_dir)
        if report:
            summary["pdf_reports"].append(report)

    for cad_path in iter_files(root, (".dwg",)):
        report = handle_dwg(cad_path, cad_out_dir, Path(args.placeholder_glb))
        summary["cad_reports"].append(report)

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote summary to {summary_path}")


def iter_files(root: Path, suffixes: Iterable[str]) -> Iterable[Path]:
    suff = tuple(s.lower() for s in suffixes)
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in suff:
            yield path


def handle_pdf(path: Path, output_dir: Path) -> Optional[Dict[str, Any]]:
    if PdfReader is None:
        print("pypdf is not installed; skipping PDF extraction.")
        return None

    try:
        reader = PdfReader(path)
    except Exception as exc:  # pragma: no cover - depends on file integrity
        print(f"Failed to load PDF {path}: {exc}")
        return None

    text_chunks = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text:
            text_chunks.append(page_text)

    text = "\n".join(text_chunks)
    preview = textwrap.shorten(text.replace("\n", " "), width=600, placeholder="…")
    bom_items = extract_bom_items(text)
    items = build_frontend_items(bom_items, source=str(path))

    report = PdfExtraction(
        path=str(path),
        page_count=len(reader.pages),
        preview=preview,
        bom_items=bom_items,
        items=items,
    )
    out_path = output_dir / f"{path.stem}.json"
    out_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    bom_payload_path = output_dir / f"{path.stem}_bom.json"
    bom_payload = {"source_pdf": str(path), "items": items}
    bom_payload_path.write_text(json.dumps(bom_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Extracted PDF data -> {out_path}")
    print(f"Generated BOM payload -> {bom_payload_path}")
    return asdict(report)


def extract_bom_items(raw_text: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        tokens = line.split()
        if len(tokens) < 4 or not tokens[0].isdigit():
            continue

        code = tokens[1]
        if not _looks_like_code(code):
            continue

        index = int(tokens[0])
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

        item = {
            "index": index,
            "code": code,
            "name": " ".join(name_tokens),
            "quantity": qty_info[0] if qty_info else None,
            "weight": weight_info[0] if weight_info else None,
            "raw": line,
        }
        items.append(item)
    return items


def build_frontend_items(entries: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
    payload = []
    for entry in entries:
        payload.append(
            {
                "name": entry.get("name"),
                "partNumber": entry.get("code"),
                "quantity": entry.get("quantity"),
                "weight": entry.get("weight"),
                "source": source,
                "raw": entry.get("raw"),
            }
        )
    return payload


def _looks_like_code(token: str) -> bool:
    if any(ch.isalpha() for ch in token):
        return True
    return any(ch in "-_.*/" for ch in token)


def _find_last_int(tokens: List[str]) -> Optional[Tuple[int, int]]:
    for idx in range(len(tokens) - 1, -1, -1):
        token = tokens[idx]
        if token.isdigit():
            try:
                return int(token), idx
            except ValueError:
                continue
    return None


def _find_last_float(tokens: List[str]) -> Optional[Tuple[float, int]]:
    for idx in range(len(tokens) - 1, -1, -1):
        token = tokens[idx]
        try:
            if any(ch.isdigit() for ch in token):
                return float(token), idx
        except ValueError:
            continue
    return None


def handle_dwg(path: Path, output_dir: Path, placeholder_glb: Path) -> Dict[str, Any]:
    converter = os.environ.get("ODA_CONVERTER")
    generated: List[str] = []
    status = "pending"
    message = "Conversion not attempted"

    if converter and Path(converter).exists():
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            target_dir = output_dir / path.stem
            target_dir.mkdir(parents=True, exist_ok=True)
            run_converter(path, Path(converter), target_dir)
            status = "converted"
            message = f"Converted with {converter}"
            generated = [str(p) for p in target_dir.iterdir() if p.is_file()]
        except Exception as exc:  # pragma: no cover - external tool
            status = "failed"
            message = str(exc)
    else:
        if placeholder_glb.exists():
            target_dir = output_dir / path.stem
            target_dir.mkdir(parents=True, exist_ok=True)
            fallback = target_dir / f"{path.stem}_placeholder.glb"
            shutil.copy2(placeholder_glb, fallback)
            generated.append(str(fallback))
            status = "placeholder"
            message = "ODA_CONVERTER not configured; copied placeholder GLB"
        else:
            message = "ODA_CONVERTER not configured and no placeholder GLB available"

    report = CadConversionStatus(
        path=str(path),
        status=status,
        message=message,
        generated_files=generated,
    )
    out_path = output_dir / f"{path.stem}.json"
    out_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Processed DWG -> {out_path}")
    return asdict(report)


def run_converter(source: Path, converter: Path, target_dir: Path) -> None:
    """Invoke an external DWG conversion tool (ODAFileConverter-style)."""
    cmd = [
        str(converter),
        str(source.parent),
        str(target_dir),
        "ACAD2018",
        "ACAD2018",
        "0",
        "1",
        "0",
    ]
    print(f"Running converter: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
