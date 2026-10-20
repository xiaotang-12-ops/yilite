"""说明书摘要计数，不读取或写入文件；页数仅指项目内唯一引用页。-codex，2026-10-10"""
from urllib.parse import unquote, urlsplit


def unavailable_metrics():
    return {'assemblyStepCount': None, 'referencedDrawingPageCount': None, 'metricsError': '说明书统计暂不可用'}


def summarize_manual(manual, task_id):
    try:
        return manual_metrics(manual, task_id)
    except (TypeError, AttributeError, ValueError):
        return unavailable_metrics()


def count_manual_steps(manual):
    total = 0
    for chapter in manual.get('component_assembly', []) or []:
        steps = chapter.get('steps') or []
        if isinstance(steps, list):
            total += len(steps)
    product = manual.get('product_assembly') or {}
    if isinstance(product, dict) and isinstance(product.get('steps'), list):
        total += len(product['steps'])
    return total


def manual_metrics(manual, task_id):
    """与 drawingEvidence 收集范围一致；只接受本项目根相对API图片路径。"""
    if not isinstance(manual, dict):
        raise ValueError('说明书格式无效')
    candidates = []

    def collect(source):
        if isinstance(source, dict):
            for key in ('drawings', 'pdf_images', 'technical_drawings', 'drawing_images'):
                if isinstance(source.get(key), list):
                    candidates.extend(source[key])

    collect(manual)
    collect(manual.get('3d_resources'))
    for chapter in [*(manual.get('component_assembly') or []), manual.get('product_assembly')]:
        collect(chapter)
        if isinstance(chapter, dict) and isinstance(chapter.get('steps'), list):
            for step in chapter['steps']:
                collect(step)
    pages = set()
    prefix = f'/api/manual/{task_id}/pdf_images/'
    for item in candidates:
        if not isinstance(item, str):
            continue
        try:
            url = urlsplit(item)
            path = unquote(url.path)
            relative = path.removeprefix(prefix)
            if (not url.scheme and not url.netloc and path.startswith(prefix)
                    and not any(part in ('..', '.') for part in relative.split('/'))
                    and path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))):
                pages.add(path)
        except ValueError:
            continue
    return {'assemblyStepCount': count_manual_steps(manual), 'referencedDrawingPageCount': len(pages)}
