"""菜单持久化与保存失败回归，只写临时目录，不触碰实际配置。-codex，2026-10-12"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.navigation_settings import create_navigation_router, DEFAULT_NAVIGATION


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)
        self.client = self.new_client()

    def tearDown(self):
        self.directory.cleanup()

    def new_client(self):
        app = FastAPI()
        app.include_router(create_navigation_router(self.path))
        return TestClient(app)

    def test_default_and_no_cache(self):
        result = self.client.get('/api/navigation')
        self.assertEqual(result.json(), {'navigation': DEFAULT_NAVIGATION, 'warning': ''})
        self.assertEqual(result.headers['cache-control'], 'no-store')

    def test_save_restart_all_hidden_and_other_settings_unchanged(self):
        for name in ('brand_settings.json', 'app_settings.json'):
            (self.path / name).write_text('{"sentinel":true}', encoding='utf-8')
        payload = dict.fromkeys(DEFAULT_NAVIGATION, False)
        self.assertEqual(self.client.put('/api/navigation', json=payload).status_code, 200)
        self.assertEqual(self.new_client().get('/api/navigation').json()['navigation'], payload)
        for name in ('brand_settings.json', 'app_settings.json'):
            self.assertEqual((self.path / name).read_text('utf-8'), '{"sentinel":true}')

    def test_invalid_input_does_not_write(self):
        cases = [{}, dict(DEFAULT_NAVIGATION, home='false'), dict(DEFAULT_NAVIGATION, viewer=0),
                 dict(DEFAULT_NAVIGATION, factory=None), dict(DEFAULT_NAVIGATION, unexpected=True)]
        for payload in cases:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.put('/api/navigation', json=payload).status_code, 422)
        self.assertFalse((self.path / 'navigation_settings.json').exists())

    def test_replace_failure_preserves_existing_and_cleans_temporary(self):
        original = dict(DEFAULT_NAVIGATION, factory=False)
        self.client.put('/api/navigation', json=original)
        with patch('backend.navigation_settings.os.replace', side_effect=OSError('simulated')):
            self.assertEqual(self.client.put('/api/navigation', json=DEFAULT_NAVIGATION).status_code, 500)
        self.assertEqual(self.new_client().get('/api/navigation').json()['navigation'], original)
        self.assertEqual(list(self.path.glob('*.tmp')), [])

    def test_corrupt_file_warns_without_overwriting_and_can_recover(self):
        path = self.path / 'navigation_settings.json'
        path.write_text('{broken', encoding='utf-8')
        result = self.client.get('/api/navigation').json()
        self.assertEqual(result['navigation'], DEFAULT_NAVIGATION)
        self.assertTrue(result['warning'])
        self.assertEqual(path.read_text('utf-8'), '{broken')
        self.assertEqual(self.client.put('/api/navigation', json=DEFAULT_NAVIGATION).status_code, 200)
        self.assertEqual(json.loads(path.read_text('utf-8')), DEFAULT_NAVIGATION)


if __name__ == '__main__':
    unittest.main()
