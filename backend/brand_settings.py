"""公开品牌名称配置：与 AI 密钥文件隔离，原子保存后才对读取生效。
隐藏设置入口沿用现有权限机制，本模块不充当身份认证。-codex，2026-10-10
"""
import json
import logging
import os
import tempfile
from pathlib import Path
from threading import Lock

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, StrictStr, field_validator

DEFAULT_NAMES = {"platform_name": "装配指导", "home_title": "装配指导", "dashboard_title": "装配成果总览"}


class BrandSettings(BaseModel):
    platform_name: StrictStr
    home_title: StrictStr
    dashboard_title: StrictStr = "装配成果总览"
    model_config = ConfigDict(extra="forbid")

    @field_validator("platform_name", "home_title", "dashboard_title")
    @classmethod
    def validate_name(cls, value, info):
        value = value.replace("\r\n", "\n").replace("\r", "\n").strip()
        limit = 24 if info.field_name in ("platform_name", "dashboard_title") else 60
        if not value or len(value) > limit:
            raise ValueError(f"名称不能为空，最多 {limit} 个字符")
        if any(ord(char) < 32 and char != "\n" for char in value):
            raise ValueError("名称不能包含控制字符")
        if info.field_name == "platform_name" and "\n" in value:
            raise ValueError("平台名称仅支持单行")
        if info.field_name == "home_title" and len(value.split("\n")) > 3:
            raise ValueError("首页标题最多 3 行")
        if info.field_name == "dashboard_title" and len(value.split("\n")) > 2:
            raise ValueError("看板标题最多 2 行")
        return value

def create_brand_router(settings_dir: Path) -> APIRouter:
    router = APIRouter(prefix="/api/branding", tags=["branding"])
    config_path = settings_dir / "brand_settings.json"
    lock = Lock()

    @router.get("")
    def read_branding(response: Response):
        response.headers["Cache-Control"] = "no-store"
        with lock:
            if not config_path.exists():
                return {"branding": DEFAULT_NAMES.copy(), "warning": ""}
            try:
                config = BrandSettings(**json.loads(config_path.read_text(encoding="utf-8")))
                return {"branding": config.model_dump(), "warning": ""}
            except (OSError, ValueError, TypeError):
                logging.getLogger(__name__).warning("品牌配置读取失败，暂用默认名称", exc_info=True)
                return {"branding": DEFAULT_NAMES.copy(), "warning": "品牌配置读取失败，当前显示默认名称；请检查后重新保存。"}

    @router.put("")
    def save_branding(settings: BrandSettings):
        # 唯一临时文件避免并发覆盖中间文件；失败不动原文件，不触碰 app_settings.json。-codex，2026-10-10
        with lock:
            temporary = None
            try:
                # 旧客户端只提交双字段时保留已有看板标题，旧配置缺字段则读默认值。
                if 'dashboard_title' not in settings.model_fields_set and config_path.exists():
                    try:
                        previous = BrandSettings(**json.loads(config_path.read_text(encoding='utf-8')))
                    except (OSError, ValueError, TypeError):
                        raise HTTPException(status_code=409, detail='请重新读取名称配置后再保存。')
                    settings = settings.model_copy(update={'dashboard_title': previous.dashboard_title})
                settings_dir.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=settings_dir,
                                                 prefix="brand-", suffix=".tmp", delete=False) as stream:
                    temporary = Path(stream.name)
                    json.dump(settings.model_dump(), stream, ensure_ascii=False, indent=2)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, config_path)
            except OSError:
                logging.getLogger(__name__).exception("品牌配置保存失败")
                raise HTTPException(status_code=500, detail="名称保存失败，原名称未更改，请稍后重试。")
            finally:
                if temporary is not None and temporary.exists():
                    try:
                        temporary.unlink(missing_ok=True)
                    except OSError:
                        logging.getLogger(__name__).warning("品牌保存临时文件清理失败")
        return {"branding": settings.model_dump(), "warning": ""}

    return router
