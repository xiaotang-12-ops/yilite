"""Generate assembly instructions from 2D engineering PDFs.

For each PDF:
- render pages to PNG
- parse BOM rows from extracted text
- generate a lightweight HTML manual referencing the rendered images
"""
from __future__ import annotations

import argparse
import json
import textwrap
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import fitz  # PyMuPDF
from pypdf import PdfReader


@dataclass
class BomItem:
    index: Optional[int]
    code: str
    name: str
    quantity: Optional[int]
    weight: Optional[float]
    raw: str


@dataclass
class ManualContext:
    pdf_path: str
    images: List[str]
    bom: List[BomItem]
    generated_at: str
    notes: str = ""


DEFAULT_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{title}</title>
  <style>
    :root {{ color-scheme: dark; font-family: 'Segoe UI', system-ui, sans-serif; }}
    body {{ margin:0; padding:24px; background:#0f172a; color:#e2e8f0; }}
    h1 {{ margin:0 0 4px; font-size:20px; }}
    .meta {{ color:#94a3b8; font-size:13px; margin-bottom:18px; }}
    .layout {{ display:grid; gap:16px; grid-template-columns: minmax(0,1fr) 360px; }}
    .panel {{ background:rgba(15,23,42,0.9); border:1px solid rgba(148,163,184,0.2); border-radius:16px; padding:16px; }}
    .panel h2 {{ margin:0 0 12px; font-size:15px; color:#94a3b8; text-transform:uppercase; letter-spacing:0.05em; }}
    .images {{ display:grid; gap:12px; }}
    .images img {{ width:100%; border-radius:12px; border:1px solid rgba(148,163,184,0.2); background:#0b1323; }}
    ol {{ padding-left:18px; margin:0; display:grid; gap:12px; }}
    li {{ background:rgba(30,41,59,0.8); border-radius:12px; padding:12px 14px; box-shadow:0 8px 20px rgba(15,23,42,0.3); }}
    .code {{ font-family: 'JetBrains Mono', Consolas, Monaco, monospace; background:rgba(58,73,99,0.4); padding:2px 6px; border-radius:6px; }}
    .empty {{ color:#94a3b8; font-style:italic; }}
    @media (max-width: 1080px) {{ .layout {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class=\"meta\">来源：{source}<br/>生成时间：{generated_at}</div>
  <div class=\"layout\">
    <section class=\"panel\">
      <h2>装配图页</h2>
      <div class=\"images\">
        {image_tags}
      </div>
    </section>
    <aside class=\"panel\">
      <h2>装配步骤（自动生成）</h2>
      {steps_html}
      <div class=\"meta\" style=\"margin-top:12px;\">{notes}</div>
    </aside>
  </div>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate manuals from 2D PDFs")
    parser.add_argument("input_dir", nargs="?", default=".", help="Directory containing PDFs")
    parser.add_argument("--output", "-o", default="processing/manual", help="Output directory")
    parser.add_argument("--dpi", type=int, default=200, help="Rendered image DPI")
    args = parser.parse_args()

    root = Path(args.input_dir).resolve()
    output_root = Path(args.output).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "dpi": args.dpi,
        "root": str(root),
        "manuals": [],
    }

    for pdf_path in iter_pdfs(root):
        manual_dir = output_root / pdf_path.stem
        manual_dir.mkdir(parents=True, exist_ok=True)
        images = render_pdf_to_images(pdf_path, manual_dir, dpi=args.dpi)
        bom = parse_bom(pdf_path)
        context = ManualContext(
            pdf_path=str(pdf_path),
            images=[str(Path("images") / Path(p).name) for p in images],
            bom=bom,
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
            notes="自动提取的步骤仅供草稿，请结合经验审核。",
        )
        manual_path = manual_dir / "manual.html"
        manual_path.write_text(render_html(context), encoding="utf-8")
        bom_path = manual_dir / "bom.json"
        bom_path.write_text(json.dumps([asdict(item) for item in bom], indent=2, ensure_ascii=False), encoding="utf-8")
        summary["manuals"].append({
            "pdf": str(pdf_path),
            "manual_html": str(manual_path),
            "images": [str(Path(manual_dir.name) / "images" / Path(p).name) for p in images],
            "bom_json": str(bom_path),
            "bom_items": len(bom),
        })
        print(f"Generated manual for {pdf_path} -> {manual_path}")

    summary_path = output_root / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Summary written to {summary_path}")


def iter_pdfs(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.pdf"):
        if path.is_file():
            yield path


def render_pdf_to_images(pdf_path: Path, manual_dir: Path, dpi: int) -> List[Path]:
    images_dir = manual_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    rendered: List[Path] = []
    for page_index, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        output_path = images_dir / f"page-{page_index:02d}.png"
        pix.save(output_path)
        rendered.append(output_path)
    return rendered


def parse_bom(pdf_path: Path) -> List[BomItem]:
    reader = PdfReader(pdf_path)
    text = "\n".join(filter(None, (page.extract_text() or "" for page in reader.pages)))
    items = extract_bom_items(text)
    return [BomItem(**item) for item in items]


def extract_bom_items(raw_text: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
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
        items.append({
            "index": index,
            "code": code,
            "name": " ".join(name_tokens),
            "quantity": qty_info[0] if qty_info else None,
            "weight": weight_info[0] if weight_info else None,
            "raw": line,
        })
    return items


def _looks_like_code(token: str) -> bool:
    if any(ch.isalpha() for ch in token):
        return True
    return any(ch in "-_.*/" for ch in token)


def _find_last_int(tokens: List[str]) -> Optional[tuple[int, int]]:
    for idx in range(len(tokens) - 1, -1, -1):
        token = tokens[idx]
        if token.isdigit():
            try:
                return int(token), idx
            except ValueError:
                continue
    return None


def _find_last_float(tokens: List[str]) -> Optional[tuple[float, int]]:
    for idx in range(len(tokens) - 1, -1, -1):
        token = tokens[idx]
        try:
            if any(ch.isdigit() for ch in token):
                return float(token), idx
        except ValueError:
            continue
    return None


def render_html(context: ManualContext) -> str:
    steps_html = ""
    if context.bom:
        bullet_lines = []
        for item in context.bom:
            step_text = textwrap.dedent(f"""
            <li>
              <div><strong>步骤 {item.index or '?'}：</strong> 安装 <span class=\"code\">{item.name}</span></div>
              <div class=\"meta\">物料号 <span class=\"code\">{item.code}</span>
              {format_quantity(item.quantity)}{format_weight(item.weight)}</div>
              <div class=\"meta\">原始信息：{item.raw}</div>
            </li>
            """).strip()
            bullet_lines.append(step_text)
        steps_html = "<ol>" + "".join(bullet_lines) + "</ol>"
    else:
        steps_html = "<div class=\"empty\">未自动识别出 BOM 条目，请人工补充。</div>"

    image_tags = "".join(
        f"<img src=\"{src}\" alt=\"{Path(src).name}\" loading=\"lazy\" />" for src in context.images
    )

    title = Path(context.pdf_path).stem + " · 自动装配手册"
    return DEFAULT_HTML_TEMPLATE.format(
        title=title,
        source=context.pdf_path,
        generated_at=context.generated_at,
        image_tags=image_tags,
        steps_html=steps_html,
        notes=context.notes,
    )


def format_quantity(quantity: Optional[int]) -> str:
    if quantity is None:
        return ""
    return f" · 数量 {quantity}"


def format_weight(weight: Optional[float]) -> str:
    if weight is None:
        return ""
    return f" · 重量 {weight}"


if __name__ == "__main__":
    main()
