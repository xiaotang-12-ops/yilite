# -*- coding: utf-8 -*-
"""
PDF 文本层 BOM 提取（确定性解析）

核心目标：优先稳定提取 6 列关键字段：
seq, code, product_code, name, material, quantity

设计原则：
- 文本层解析首先保证“序号、物料代码、代号、名称、材料、数量”正确。
- 重量字段属于弱约束，只做可选补充，不能反过来破坏 6 列关键字段。
- 表格被线性化后，单元格通常以“逐行”形式输出（每个 cell 一行）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


_INT_RE = re.compile(r"^\d+$")
_CODE_RE = re.compile(r"^\d{2}\.\d{2}(?:\.\d{2})?\.\d{4}$")
_NUM_LINE_RE = re.compile(r"^\s*[-+]?\d+(?:\.\d+)?(?:\s+[-+]?\d+(?:\.\d+)?)*\s*$")
_CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")


@dataclass
class TextLayerBOMStats:
    pages_total: int = 0
    pages_with_text: int = 0
    pages_empty_text: int = 0
    lines_total: int = 0
    items_extracted: int = 0
    plausible: bool = False


def _normalize_cell(text: str) -> str:
    if not text:
        return ""
    # 常见全角/变体符号归一，避免 code/数字识别失败
    return (
        str(text)
        .strip()
        .replace("．", ".")
        .replace("。", ".")
        .replace("／", "/")
        .replace("\u3000", " ")
    )


def _parse_numeric_tokens(line: str) -> List[float]:
    line = _normalize_cell(line)
    if not line or not _NUM_LINE_RE.match(line):
        return []
    tokens = line.split()
    out: List[float] = []
    for t in tokens:
        try:
            out.append(float(t))
        except Exception:
            return []
    return out


def _looks_like_record_start(lines: List[str], idx: int) -> bool:
    if idx < 0 or idx + 1 >= len(lines):
        return False
    seq_raw = _normalize_cell(lines[idx])
    code_raw = _normalize_cell(lines[idx + 1])
    if not _INT_RE.match(seq_raw) or not _CODE_RE.match(code_raw):
        return False
    try:
        seq_int = int(seq_raw)
    except Exception:
        return False
    return 0 < seq_int <= 9999


def _looks_like_product_code(text: str) -> bool:
    text = _normalize_cell(text)
    if not text:
        return False
    if _CHINESE_RE.search(text):
        return False
    return True


def _find_record_end(lines: List[str], start_idx: int) -> int:
    idx = start_idx + 2
    while idx < len(lines):
        if _looks_like_record_start(lines, idx):
            return idx
        idx += 1
    return len(lines)


def _extract_quantity_and_weights(body: List[str]) -> Tuple[Optional[int], Optional[int], Optional[float], Optional[float]]:
    if not body:
        return None, None, None, None

    # 优先按“代号/名称/材料/数量/重量...”的自然顺序前向识别，
    # 避免最后一条 BOM 把表尾里的整数误抓成数量。
    for q_idx in range(len(body)):
        qty_raw = _normalize_cell(body[q_idx])
        if not _INT_RE.match(qty_raw):
            continue
        if q_idx < 2:
            continue
        try:
            qty = int(qty_raw)
        except Exception:
            continue
        if qty < 0 or qty > 100000:
            continue

        tail = body[q_idx + 1 :]
        if not tail:
            continue

        first_tail = _parse_numeric_tokens(tail[0])
        if not first_tail:
            continue

        unit_weight: Optional[float] = None
        total_weight: Optional[float] = None

        if len(first_tail) >= 2:
            unit_weight = first_tail[0]
            total_weight = first_tail[1]
        else:
            unit_weight = first_tail[0]
            for extra in tail[1:3]:
                extra_tail = _parse_numeric_tokens(extra)
                if extra_tail:
                    total_weight = extra_tail[0]
                    break

        return q_idx, qty, unit_weight, total_weight

    # 兜底：只认第一处“前面至少有 名称/材料，后面没有被更早命中”的数量。
    for q_idx in range(len(body)):
        qty_raw = _normalize_cell(body[q_idx])
        if not _INT_RE.match(qty_raw):
            continue
        if q_idx < 2:
            continue
        try:
            qty = int(qty_raw)
        except Exception:
            continue
        if qty < 0 or qty > 100000:
            continue
        return q_idx, qty, None, None

    return None, None, None, None


def _split_prefix_to_fields(prefix: List[str]) -> Tuple[str, str, str]:
    product_code = ""
    cells = [x for x in prefix if _normalize_cell(x)]
    if not cells:
        return "", "", ""

    if _looks_like_product_code(cells[0]):
        product_code = cells[0]
        cells = cells[1:]

    if not cells:
        return product_code, "", ""

    if len(cells) == 1:
        return product_code, cells[0], ""

    material = cells[-1]
    name = " ".join(cells[:-1]).strip()
    return product_code, name, material


def _score_item(item: Dict) -> int:
    score = 0
    if item.get("code"):
        score += 2
    if item.get("product_code"):
        score += 1
    if item.get("name"):
        score += 1
    if item.get("material"):
        score += 1
    if item.get("quantity") not in (None, "", 0):
        score += 1
    if item.get("unit_weight") is not None:
        score += 1
    if item.get("total_weight") is not None:
        score += 1
    return score


def _dedupe_and_sort(items: List[Dict]) -> List[Dict]:
    # 同一个 PDF 内，BOM 序号通常唯一；若重复，保留字段更完整者
    by_seq: Dict[int, Dict] = {}
    for item in items:
        try:
            seq_int = int(str(item.get("seq", "")).strip())
        except Exception:
            continue
        prev = by_seq.get(seq_int)
        if prev is None or _score_item(item) > _score_item(prev):
            by_seq[seq_int] = item

    result = list(by_seq.values())
    result.sort(key=lambda x: int(str(x.get("seq", "999999")).strip() or "999999"))
    return result


def _is_plausible_bom(items: List[Dict]) -> bool:
    if not items:
        return False
    seqs: List[int] = []
    for item in items:
        try:
            seqs.append(int(str(item.get("seq", "")).strip()))
        except Exception:
            continue
    if not seqs:
        return False
    min_seq, max_seq = min(seqs), max(seqs)
    # 经验：BOM 一般从 1 开始；过大的起始序号通常是误匹配
    if min_seq > 3:
        return False
    expected = max_seq - min_seq + 1
    if expected <= 0:
        return False
    coverage = len(set(seqs)) / expected
    # 允许少量缺失（格式异常/跨页断行），但不能只抽到零星几条
    if expected >= 8 and coverage < 0.7:
        return False
    return True


def _extract_from_lines(lines: List[str], source_pdf: str) -> List[Dict]:
    lines = [_normalize_cell(x) for x in lines if _normalize_cell(x)]
    out: List[Dict] = []

    i = 0
    while i + 1 < len(lines):
        if not _looks_like_record_start(lines, i):
            i += 1
            continue

        seq_int = int(lines[i])
        code = _normalize_cell(lines[i + 1])
        next_i = _find_record_end(lines, i)
        body = lines[i + 2 : next_i]

        qty_idx, qty, unit_weight, total_weight = _extract_quantity_and_weights(body)
        if qty_idx is None or qty is None:
            i = next_i
            continue

        prefix = body[:qty_idx]
        product_code, name, material = _split_prefix_to_fields(prefix)

        weight = total_weight if total_weight is not None else unit_weight

        out.append(
            {
                "seq": str(seq_int),
                "code": code,
                "product_code": product_code,
                "name": name,
                "material": material,
                "quantity": int(qty),
                "unit_weight": unit_weight,
                "total_weight": total_weight,
                "weight": weight,
                "source_pdf": source_pdf,
            }
        )

        i = next_i

    return _dedupe_and_sort(out)


def extract_bom_from_pdf_text_layer(pdf_path: str, source_pdf: str) -> Tuple[List[Dict], TextLayerBOMStats]:
    """
    从 PDF 文本层提取 BOM。

    Args:
        pdf_path: PDF 文件路径
        source_pdf: 写回 BOM 的来源标识（通常用文件名，如 xxx.pdf）

    Returns:
        (items, stats)
    """
    stats = TextLayerBOMStats()
    try:
        import fitz  # PyMuPDF
    except Exception as e:  # pragma: no cover
        # 环境缺依赖时直接返回空（由上层决定是否回退到 vision）
        return [], stats

    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return [], stats

    try:
        stats.pages_total = len(doc)
        all_lines: List[str] = []
        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                text = page.get_text("text") or ""
            except Exception:
                text = ""

            if not text.strip():
                stats.pages_empty_text += 1
                continue

            stats.pages_with_text += 1
            lines = [x for x in text.splitlines()]
            all_lines.extend(lines)

        stats.lines_total = len(all_lines)
        items = _extract_from_lines(all_lines, source_pdf=source_pdf)
        stats.items_extracted = len(items)
        stats.plausible = _is_plausible_bom(items)
        return items, stats
    finally:
        try:
            doc.close()
        except Exception:
            pass
