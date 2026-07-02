"""
AI 设置持久化回归测试。
这里专门覆盖 runtime_settings/app_settings.json 的关键边界，避免后续再把设置保存链路退回“仅内存 + env”。
"""

import asyncio
import copy
import json
import os
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import simple_app


def _build_baseline_settings() -> dict:
    return {
        "openrouter_api_key": "openrouter-live-key",
        "deepseek_api_key": "deepseek-live-key",
        "newapi_api_key": "newapi-live-key",
        "doubao_api_key": "newapi-live-key",
        "call_points": simple_app._build_default_call_points(),
    }


@pytest.fixture
def runtime_settings_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # 这里直接操作 simple_app 模块级全局，是为了验证真实 save/load 路径，而不是测一层假的包装。
    original_settings = copy.deepcopy(simple_app.app_settings)
    original_meta = copy.deepcopy(simple_app.runtime_settings_meta)
    original_env = {
        "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", ""),
        "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY", ""),
        "NEWAPI_API_KEY": os.environ.get("NEWAPI_API_KEY", ""),
        "ARK_API_KEY": os.environ.get("ARK_API_KEY", ""),
    }
    runtime_dir = tmp_path / "runtime_settings"
    runtime_file = runtime_dir / "app_settings.json"
    monkeypatch.setattr(simple_app, "RUNTIME_SETTINGS_DIR", runtime_dir)
    monkeypatch.setattr(simple_app, "RUNTIME_SETTINGS_FILE", runtime_file)

    baseline = _build_baseline_settings()
    simple_app.app_settings.clear()
    simple_app.app_settings.update(copy.deepcopy(baseline))
    simple_app.runtime_settings_meta.clear()
    simple_app.runtime_settings_meta.update({
        "config_source": "env_only",
        "saved_at": "",
        "last_error": "",
    })
    simple_app._apply_runtime_settings_to_env(simple_app.app_settings)

    yield {
        "baseline": baseline,
        "runtime_dir": runtime_dir,
        "runtime_file": runtime_file,
    }

    simple_app.app_settings.clear()
    simple_app.app_settings.update(original_settings)
    simple_app.runtime_settings_meta.clear()
    simple_app.runtime_settings_meta.update(original_meta)
    for key, value in original_env.items():
        os.environ[key] = value


def test_save_settings_preserves_existing_keys_when_payload_is_none(runtime_settings_context):
    response = asyncio.run(simple_app.save_settings(simple_app.SettingsModel()))
    runtime_file = runtime_settings_context["runtime_file"]
    saved_payload = json.loads(runtime_file.read_text(encoding="utf-8"))

    assert response["success"] is True
    assert response["has_openrouter_key"] is True
    assert response["has_deepseek_key"] is True
    assert response["has_newapi_key"] is True
    assert saved_payload["openrouter_api_key"] == "openrouter-live-key"
    assert saved_payload["deepseek_api_key"] == "deepseek-live-key"
    assert saved_payload["newapi_api_key"] == "newapi-live-key"
    assert simple_app.app_settings["openrouter_api_key"] == "openrouter-live-key"
    assert simple_app.app_settings["deepseek_api_key"] == "deepseek-live-key"
    assert simple_app.app_settings["newapi_api_key"] == "newapi-live-key"


def test_save_settings_explicit_empty_string_clears_key(runtime_settings_context):
    response = asyncio.run(
        simple_app.save_settings(simple_app.SettingsModel(openrouter_api_key=""))
    )
    runtime_file = runtime_settings_context["runtime_file"]
    saved_payload = json.loads(runtime_file.read_text(encoding="utf-8"))

    assert response["has_openrouter_key"] is False
    assert simple_app.app_settings["openrouter_api_key"] == ""
    assert saved_payload["openrouter_api_key"] == ""


def test_save_settings_partial_call_points_keeps_existing_entries(runtime_settings_context):
    baseline_call_points = copy.deepcopy(simple_app.app_settings["call_points"])
    call_point_ids = list(simple_app.AI_CALL_POINT_DEFS.keys())
    target_call_point = call_point_ids[0]
    untouched_call_point = call_point_ids[1]

    response = asyncio.run(
        simple_app.save_settings(
            simple_app.SettingsModel(
                call_points={
                    target_call_point: simple_app.CallPointConfig(
                        provider="deepseek",
                        model="deepseek-chat",
                        fallback_model="",
                        custom_key="partial-call-point-key",
                    )
                }
            )
        )
    )

    runtime_file = runtime_settings_context["runtime_file"]
    saved_payload = json.loads(runtime_file.read_text(encoding="utf-8"))

    assert response["success"] is True
    assert saved_payload["call_points"][target_call_point]["provider"] == "deepseek"
    assert saved_payload["call_points"][target_call_point]["model"] == "deepseek-chat"
    assert saved_payload["call_points"][target_call_point]["custom_key"] == "partial-call-point-key"
    assert saved_payload["call_points"][untouched_call_point] == baseline_call_points[untouched_call_point]
    assert simple_app.app_settings["call_points"][untouched_call_point] == baseline_call_points[untouched_call_point]


def test_load_runtime_app_settings_prefers_runtime_file_over_env(runtime_settings_context, monkeypatch: pytest.MonkeyPatch):
    runtime_file = runtime_settings_context["runtime_file"]
    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    runtime_file.write_text(
        json.dumps(
            {
                "saved_at": "2026-07-01T18:00:00+08:00",
                "openrouter_api_key": "persisted-openrouter-key",
                "deepseek_api_key": "persisted-deepseek-key",
                "newapi_api_key": "persisted-newapi-key",
                "doubao_api_key": "persisted-newapi-key",
                "call_points": simple_app._build_default_call_points(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-openrouter-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "env-deepseek-key")
    monkeypatch.setenv("NEWAPI_API_KEY", "env-newapi-key")
    monkeypatch.setenv("ARK_API_KEY", "env-ark-key")

    loaded = simple_app._load_runtime_app_settings()

    assert loaded["openrouter_api_key"] == "persisted-openrouter-key"
    assert loaded["deepseek_api_key"] == "persisted-deepseek-key"
    assert loaded["newapi_api_key"] == "persisted-newapi-key"
    assert loaded["doubao_api_key"] == "persisted-newapi-key"
    assert simple_app.runtime_settings_meta["config_source"] == "runtime_file"
    assert simple_app.runtime_settings_meta["saved_at"] == "2026-07-01T18:00:00+08:00"


def test_save_settings_rolls_back_memory_and_env_when_persist_fails(runtime_settings_context, monkeypatch: pytest.MonkeyPatch):
    before_settings = copy.deepcopy(simple_app.app_settings)
    before_meta = copy.deepcopy(simple_app.runtime_settings_meta)
    before_env = {
        "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", ""),
        "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY", ""),
        "NEWAPI_API_KEY": os.environ.get("NEWAPI_API_KEY", ""),
        "ARK_API_KEY": os.environ.get("ARK_API_KEY", ""),
    }

    def explode(_settings):
        raise RuntimeError("persist failed intentionally")

    monkeypatch.setattr(simple_app, "_persist_runtime_app_settings", explode)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            simple_app.save_settings(
                simple_app.SettingsModel(deepseek_api_key="should-rollback")
            )
        )

    assert exc_info.value.status_code == 500
    assert simple_app.app_settings == before_settings
    assert simple_app.runtime_settings_meta == before_meta
    assert os.environ.get("OPENROUTER_API_KEY", "") == before_env["OPENROUTER_API_KEY"]
    assert os.environ.get("DEEPSEEK_API_KEY", "") == before_env["DEEPSEEK_API_KEY"]
    assert os.environ.get("NEWAPI_API_KEY", "") == before_env["NEWAPI_API_KEY"]
    assert os.environ.get("ARK_API_KEY", "") == before_env["ARK_API_KEY"]
