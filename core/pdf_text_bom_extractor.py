# -*- coding: utf-8 -*-
"""
PDF 文本层 BOM 提取（确定性解析）

目标：在不使用 OCR/视觉模型 的前提下，从 PDF 的文本层中稳定提取 BOM 7 列：
seq, code, product_code, name, quantity, unit_weight, total_weight

设计前提（来自实际样本 BH1830 的文本层表现）：
- 表格被线性化后，单元格通常以“逐行”形式输出（每个 cell 一行）
- 典型记录结构：seq → code → product_code → name(可多行) → quantity → unit_weight/total_weight
- unit_weight 与 total_weight 可能分两行，也可能同一行出现两个数值（如 "622.57 622.57"）
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


_INT_RE = re.compile(r"^\d+$")
_CODE_RE = re.compile(r"^\d{2}\.\d{2}(?:\.\d{2})?\.\d{4}$")
_NUM_LINE_RE = re.compile(r"^\s*[-+]?\d+(?:\.\d+)?(?:\s+[-+]?\d+(?:\.\d+)?)*\s*$")


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


def _score_item(item: Dict) -> int:
    score = 0
    if item.get("code"):
        score += 2
    if item.get("product_code"):
        score += 1
    if item.get("name"):
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
        seq_raw = lines[i]
        if not _INT_RE.match(seq_raw):
            i += 1
            continue

        try:
            seq_int = int(seq_raw)
        except Exception:
            i += 1
            continue

        if seq_int <= 0 or seq_int > 9999:
            i += 1
            continue

        code = _normalize_cell(lines[i + 1])
        if not _CODE_RE.match(code):
            i += 1
            continue

        # 在 code 后寻找 quantity（纯整数）并校验其后紧跟重量数字
        # 说明：部分图纸可能缺少 product_code 列，因此 quantity 可能更靠前；
        #      我们通过“quantity 后必须跟重量数字”来降低误判风险。
        record_found: Optional[Tuple[int, int, float, float, int]] = None
        search_start = i + 3  # 允许缺少 product_code 列：seq → code → name → quantity ...
        search_end = min(i + 14, len(lines) - 1)
        for q_idx in range(search_start, search_end):
            qty_raw = lines[q_idx]
            if not _INT_RE.match(qty_raw):
                continue
            try:
                qty = int(qty_raw)
            except Exception:
                continue
            if qty < 0 or qty > 100000:
                continue

            # 解析重量：可能是一行两个数，也可能两行各一个数
            if q_idx + 1 >= len(lines):
                continue
            w1_tokens = _parse_numeric_tokens(lines[q_idx + 1])
            if len(w1_tokens) >= 2:
                unit_w, total_w = w1_tokens[0], w1_tokens[1]
                next_i = q_idx + 2
                record_found = (q_idx, qty, unit_w, total_w, next_i)
                break

            if len(w1_tokens) == 1 and q_idx + 2 < len(lines):
                w2_tokens = _parse_numeric_tokens(lines[q_idx + 2])
                if len(w2_tokens) == 1:
                    unit_w, total_w = w1_tokens[0], w2_tokens[0]
                    next_i = q_idx + 3
                    record_found = (q_idx, qty, unit_w, total_w, next_i)
                    break

        if not record_found:
            i += 1
            continue

        q_idx, qty, unit_w, total_w, next_i = record_found
        product_code = lines[i + 2] if i + 2 < len(lines) else ""
        name_lines = lines[i + 3 : q_idx]
        # 若 name 为空，通常表示缺少 product_code 列：把 product_code 置空，name 从 code 后开始吃
        if not any(x for x in name_lines) and product_code:
            name_lines = [product_code]
            product_code = ""
        name = " ".join([x for x in name_lines if x]).strip()

        total_weight = total_w
        unit_weight = unit_w
        weight = total_weight if total_weight is not None else unit_weight

        out.append(
            {
                "seq": str(seq_int),
                "code": code,
                "product_code": product_code,
                "name": name,
                "quantity": int(qty),
                "unit_weight": unit_weight,
                "total_weight": total_weight,
                # 兼容旧链路：step2 过去只有 weight 字段
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
