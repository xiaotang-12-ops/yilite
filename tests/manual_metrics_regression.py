"""正式看板摘要与现有统计口径回归，不修改真实output。-codex，2026-10-20"""
import ast
import json
import unittest
from pathlib import Path
from backend.manual_metrics import summarize_manual


class ManualMetricsTests(unittest.TestCase):
    def test_steps_and_reference_deduplication(self):
        page = '/api/manual/项目/pdf_images/part/page_001.png'
        manual = {'drawings': [page], '3d_resources': {'pdf_images': [page + '?v=2']},
                  'component_assembly': [{'steps': [{'drawings': [page]}, {}]}],
                  'product_assembly': {'steps': [{'drawings': [page, '/api/manual/项目/pdf_images/part/page_002.png',
                                      '/api/manual/其他/pdf_images/page_001.png', 'https://external.test' + page,
                                      '/api/manual/项目/pdf_images/../page_003.png']} ]}}
        self.assertEqual(summarize_manual(manual, '项目'), {'assemblyStepCount': 3, 'referencedDrawingPageCount': 2})

    def test_invalid_is_unavailable_not_zero(self):
        for invalid in (None, [], {'component_assembly': [None]}):
            result = summarize_manual(invalid, 'x')
            self.assertIsNone(result['assemblyStepCount'])
            self.assertIsNone(result['referencedDrawingPageCount'])
        self.assertEqual(summarize_manual({}, 'empty')['assemblyStepCount'], 0)

    def test_production_integration_and_existing_counter_agree(self):
        root = Path(__file__).resolve().parents[1]
        tree = ast.parse((root / 'backend/simple_app.py').read_text('utf-8-sig'))
        counter = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == '_count_manual_steps')
        # 只执行纯统计函数，避免导入应用触发生产启动副作用。
        scope = {'Dict': dict, 'Any': object}
        exec(compile(ast.Module(body=[counter], type_ignores=[]), '<counter>', 'exec'), scope)
        for path in (root / 'output').glob('*/assembly_manual.json'):
            manual = json.loads(path.read_text('utf-8'))
            self.assertEqual(summarize_manual(manual, path.parent.name)['assemblyStepCount'], scope['_count_manual_steps'](manual))
        calls = [ast.unparse(node) for node in ast.walk(tree) if isinstance(node, ast.Call)]
        self.assertIn('summarize_manual(manual_data, task_dir.name)', calls)

if __name__ == '__main__':
    unittest.main()
