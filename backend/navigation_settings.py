"""管理员顶栏显示配置，独立持久化，避免菜单保存覆盖名称或AI设置。
只控制入口展示，沿用现有设置访问机制，不承担路由鉴权。-codex，2026-10-12
"""
import json
import logging
import os
import tempfile
from pathlib import Path
from threading import Lock

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, StrictBool


class NavigationSettings(BaseModel):
    home: StrictBool
    generator: StrictBool
    viewer: StrictBool
    factory: StrictBool
    model_config = ConfigDict(extra="forbid")


DEFAULT_NAVIGATION = {"home": True, "generator": True, "viewer": True, "factory": True}


def create_navigation_router(settings_dir: Path) -> APIRouter:
    router = APIRouter(prefix="/api/navigation", tags=["navigation"])
    config_path = settings_dir / "navigation_settings.json"
    lock = Lock()

    @router.get("")
    def read_navigation(response: Response):
        response.headers["Cache-Control"] = "no-store"
        with lock:
            if not config_path.exists():
                return {"navigation": DEFAULT_NAVIGATION.copy(), "warning": ""}
            try:
                config = NavigationSettings(**json.loads(config_path.read_text(encoding="utf-8")))
                return {"navigation": config.model_dump(), "warning": ""}
            except (OSError, ValueError, TypeError):
                logging.getLogger(__name__).warning("菜单配置读取失败，暂显示全部入口", exc_info=True)
                return {"navigation": DEFAULT_NAVIGATION.copy(), "warning": "菜单配置读取失败，当前显示全部入口；重新保存可恢复配置。"}

    @router.put("")
    def save_navigation(settings: NavigationSettings):
        # 原子替换后才算保存成功；不写入brand_settings.json或app_settings.json。-codex，2026-10-12
        with lock:
            temporary = None
            try:
                settings_dir.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=settings_dir,
                                                 prefix="navigation-", suffix=".tmp", delete=False) as stream:
                    temporary = Path(stream.name)
                    json.dump(settings.model_dump(), stream, ensure_ascii=False, indent=2)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, config_path)
            except OSError:
                logging.getLogger(__name__).exception("菜单配置保存失败")
                raise HTTPException(status_code=500, detail="菜单保存失败，原配置未更改，请稍后重试。")
            finally:
                if temporary is not None and temporary.exists():
                    try:
                        temporary.unlink(missing_ok=True)
                    except OSError:
                        logging.getLogger(__name__).warning("菜单配置临时文件清理失败")
        return {"navigation": settings.model_dump(), "warning": ""}

    return router
