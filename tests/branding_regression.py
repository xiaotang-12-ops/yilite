"""品牌配置持久化与隔离回归，所有写入只在临时目录。-codex，2026-10-10"""
import ast
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.brand_settings import create_brand_router, DEFAULT_NAMES


class BrandingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)
        self.client = self.new_client()

    def tearDown(self):
        self.directory.cleanup()

    def new_client(self):
        app = FastAPI()
        app.include_router(create_brand_router(self.path))
        return TestClient(app)

    def test_default_public_shape(self):
        result = self.client.get('/api/branding')
        self.assertEqual(result.json(), {'branding': DEFAULT_NAMES, 'warning': ''})
        self.assertEqual(result.headers['cache-control'], 'no-store')

    def test_save_restart_and_ai_isolation(self):
        ai = self.path / 'app_settings.json'
        ai.write_text('{"test_sentinel":true}', encoding='utf-8')
        payload = {'platform_name': ' 工业平台 ', 'home_title': '第一行\r\n第二行'}
        result = self.client.put('/api/branding', json=payload)
        self.assertEqual(result.status_code, 200)
        expected = {'platform_name': '工业平台', 'home_title': '第一行\n第二行', 'dashboard_title': '装配成果总览'}
        self.assertEqual(self.new_client().get('/api/branding').json()['branding'], expected)
        self.assertEqual(json.loads((self.path / 'brand_settings.json').read_text('utf-8')), expected)
        self.assertEqual(ai.read_text('utf-8'), '{"test_sentinel":true}')

    def test_invalid_input_does_not_write(self):
        cases = [dict(DEFAULT_NAMES, platform_name=' '), dict(DEFAULT_NAMES, platform_name='a'*25),
                 dict(DEFAULT_NAMES, home_title='a'*61), dict(DEFAULT_NAMES, home_title='a\nb\nc\nd'),
                 dict(DEFAULT_NAMES, platform_name='a\nb'), dict(DEFAULT_NAMES, platform_name=10),
                 dict(DEFAULT_NAMES, platform_name='a\t'), dict(DEFAULT_NAMES, api_key='oops'), {}]
        cases.extend([dict(DEFAULT_NAMES, dashboard_title=' '), dict(DEFAULT_NAMES, dashboard_title='字'*25), dict(DEFAULT_NAMES, dashboard_title='一\n二\n三')])
        # 尾部空白会规范化；控制字符用中间制表符测试。-codex，2026-10-10
        cases[6]['platform_name'] = 'a\tb'
        for payload in cases:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.put('/api/branding', json=payload).status_code, 422)
        self.assertFalse((self.path / 'brand_settings.json').exists())

    def test_failed_write_preserves_saved_value(self):
        self.client.put('/api/branding', json=DEFAULT_NAMES)
        with patch('backend.brand_settings.os.replace', side_effect=OSError('simulated')):
            response = self.client.put('/api/branding', json=dict(DEFAULT_NAMES, platform_name='不会保存'))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.client.get('/api/branding').json()['branding'], DEFAULT_NAMES)
        self.assertEqual(list(self.path.glob('*.tmp')), [])

    def test_corrupt_file_does_not_get_overwritten_on_read(self):
        file = self.path / 'brand_settings.json'
        file.write_text('{broken', encoding='utf-8')
        result = self.client.get('/api/branding').json()
        self.assertEqual(result['branding'], DEFAULT_NAMES)
        self.assertTrue(result['warning'])
        self.assertEqual(file.read_text('utf-8'), '{broken')

    def test_production_router_registration(self):
        # 静态集成断言避免导入全后端时触碰生产环境和输出目录。-codex，2026-10-10
        root = Path(__file__).resolve().parents[1]
        tree = ast.parse((root / 'backend/simple_app.py').read_text('utf-8-sig'))
        calls = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.Call)]
        self.assertIn('app.include_router(create_brand_router(RUNTIME_SETTINGS_DIR))', calls)

    def test_legacy_file_and_old_client_preserve_dashboard(self):
        file = self.path / 'brand_settings.json'
        legacy = {'platform_name': '旧平台', 'home_title': '旧首页'}
        file.write_text(json.dumps(legacy), encoding='utf-8')
        self.assertEqual(self.client.get('/api/branding').json()['branding']['dashboard_title'], '装配成果总览')
        self.assertEqual(json.loads(file.read_text('utf-8')), legacy)
        self.client.put('/api/branding', json=dict(DEFAULT_NAMES, dashboard_title='制造成果\n项目总览'))
        self.client.put('/api/branding', json=legacy)
        self.assertEqual(self.new_client().get('/api/branding').json()['branding']['dashboard_title'], '制造成果\n项目总览')


if __name__ == '__main__':
    unittest.main()
