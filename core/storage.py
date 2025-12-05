"""Manual storage utilities for draft/publish/version management."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.time_utils import beijing_now


@dataclass
class VersionEntry:
    version: str
    published_at: str
    changelog: str
    source: str = "publish"  # publish | rollback | legacy


class ManualStorage:
    """Manage assembly manual drafts, published versions, and history on disk."""

    def __init__(self, base_dir: Path, task_id: str):
        self.base_dir = Path(base_dir)
        self.task_id = task_id
        self.task_dir = self.base_dir / task_id
        self.task_dir.mkdir(parents=True, exist_ok=True)
        self.versions_dir = self.task_dir / "versions"
        self.version_history_path = self.versions_dir / "version_history.json"
        self.published_path = self.task_dir / "assembly_manual.json"
        self.draft_path = self.task_dir / "draft.json"

    # ---------- helpers ----------
    def _read_json(self, path: Path) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _now(self) -> str:
        return beijing_now().isoformat()

    def _parse_version_number(self, version_str: str) -> int:
        """Extract integer part from version string."""
        if not version_str:
            return 1
        s = version_str.lower().lstrip("v")
        try:
            # 支持 "1.3" 等形式，取整数部分
            return int(float(s))
        except Exception:
            return 1

    def _format_version(self, number: int) -> str:
        return f"v{number}"

    def _max_version_number(self, versions: List[Dict[str, Any]]) -> int:
        nums = [
            self._parse_version_number(item.get("version", ""))
            for item in versions
        ]
        return max(nums) if nums else 0

    # ---------- core loaders ----------
    def load_published(self, allow_absent: bool = False) -> Optional[Dict[str, Any]]:
        if not self.published_path.exists():
            if allow_absent:
                return None
            raise FileNotFoundError(f"published manual not found: {self.published_path}")
        return self._read_json(self.published_path)

    def load_draft(self) -> Optional[Dict[str, Any]]:
        if not self.draft_path.exists():
            return None
        return self._read_json(self.draft_path)

    def load_version(self, version: str) -> Dict[str, Any]:
        target = self.versions_dir / f"{version}.json"
        if not target.exists():
            raise FileNotFoundError(f"version file not found: {target}")
        return self._read_json(target)

    def load_version_history(self) -> Dict[str, Any]:
        if not self.version_history_path.exists():
            return {"current_version": None, "versions": []}
        return self._read_json(self.version_history_path)

    # ---------- migration ----------
    def ensure_migration(self) -> Dict[str, Any]:
        """
        If the task only has assembly_manual.json, bootstrap versions/version_history.
        """
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        history = self.load_version_history()

        # 先尝试升级已存在的发布版/草稿的步骤结构（UUID step_id + display_order）
        self._maybe_upgrade_manual_file(self.published_path)
        self._maybe_upgrade_manual_file(self.draft_path)

        if history.get("versions"):
            return history

        if not self.published_path.exists():
            return history

        manual = self.load_published()
        base_version_num = self._parse_version_number(manual.get("version", "v1"))
        base_version = self._format_version(base_version_num)

        manual = dict(manual)
        manual["version"] = base_version
        manual.setdefault("lastUpdated", self._now())

        # 将当前发布版也存入 versions 以便历史查询
        self._write_json(self.versions_dir / f"{base_version}.json", manual)

        history = {
            "current_version": base_version,
            "versions": [
                VersionEntry(
                    version=base_version,
                    published_at=self._now(),
                    changelog="初始化迁移",
                    source="legacy",
                ).__dict__
            ],
        }
        self._write_json(self.version_history_path, history)
        # 覆盖回已发布文件的版本字段（保持一致）
        self._write_json(self.published_path, manual)
        return history

    def _maybe_upgrade_manual_file(self, path: Path) -> None:
        """升级单个手册文件的步骤结构，缺失 display_order/UUID step_id 时补齐。"""
        if not path.exists():
            return
        manual = self._read_json(path)
        if self._upgrade_manual_schema(manual):
            self._write_json(path, manual)

    def _upgrade_manual_schema(self, manual: Dict[str, Any]) -> bool:
        """为旧手册补充 UUID step_id、display_order，并保留 legacy 字段。"""
        changed = False

        if manual.get("_edit_version") is None:
            manual["_edit_version"] = 0
            changed = True

        def upgrade_steps(steps: List[Dict[str, Any]]) -> bool:
            local_changed = False
            if not isinstance(steps, list):
                return local_changed
            for idx, step in enumerate(steps):
                if not isinstance(step, dict):
                    continue
                # display_order：缺失则按顺序补齐
                if not isinstance(step.get("display_order"), (int, float)):
                    step["display_order"] = (idx + 1) * 1000
                    local_changed = True
                # step_id：非 UUID 则生成新的，并保留 legacy
                step_id = step.get("step_id")
                if not self._is_uuid_step_id(step_id):
                    if step_id:
                        step.setdefault("_legacy_step_id", step_id)
                    step["step_id"] = f"step_{uuid.uuid4().hex[:12]}"
                    local_changed = True
                # 保留原始步骤号，便于回溯
                if "step_number" in step and "_legacy_step_number" not in step:
                    step["_legacy_step_number"] = step["step_number"]
                    local_changed = True
            return local_changed

        # 组件装配章节
        for chapter in manual.get("component_assembly", []):
            steps = chapter.get("steps")
            if upgrade_steps(steps):
                changed = True

        # 产品装配章节
        product_steps = None
        if isinstance(manual.get("product_assembly"), dict):
            product_steps = manual["product_assembly"].get("steps")
        if upgrade_steps(product_steps):
            changed = True

        return changed

    def _is_uuid_step_id(self, step_id: Any) -> bool:
        if not isinstance(step_id, str):
            return False
        return bool(re.match(r"^step_[0-9a-f]{12}$", step_id))

    # ---------- actions ----------
    def save_draft(self, manual_data: Dict[str, Any]) -> Dict[str, Any]:
        if not manual_data:
            raise ValueError("manual_data is empty")
        manual_data = dict(manual_data)
        manual_data["lastUpdated"] = self._now()
        self._write_json(self.draft_path, manual_data)
        return manual_data

    def publish_draft(self, changelog: str, manual_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not changelog or not changelog.strip():
            raise ValueError("changelog is required for publish")

        self.ensure_migration()
        history = self.load_version_history()
        versions = history.get("versions", [])

        # 归档当前发布版（确保版本文件存在）
        current_version = history.get("current_version")
        if current_version:
            if not (self.versions_dir / f"{current_version}.json").exists():
                published = self.load_published(allow_absent=True)
                if published:
                    self._write_json(self.versions_dir / f"{current_version}.json", published)

        draft = manual_data or self.load_draft()
        if draft is None:
            raise FileNotFoundError("draft.json not found, please save draft first")

        next_number = self._max_version_number(versions) + 1
        new_version = self._format_version(next_number)

        published = dict(draft)
        published["version"] = new_version
        published["lastUpdated"] = self._now()

        # 写入发布版与版本归档
        self._write_json(self.published_path, published)
        self._write_json(self.versions_dir / f"{new_version}.json", published)

        new_entry = VersionEntry(
            version=new_version,
            published_at=self._now(),
            changelog=changelog.strip(),
            source="publish",
        ).__dict__
        versions.insert(0, new_entry)

        history["current_version"] = new_version
        history["versions"] = versions
        self._write_json(self.version_history_path, history)

        # 删除草稿（发布后清理）
        if self.draft_path.exists():
            self.draft_path.unlink()

        return published

    def rollback_to_version(self, version: str, changelog: Optional[str] = None) -> Dict[str, Any]:
        self.ensure_migration()
        history = self.load_version_history()
        versions = history.get("versions", [])

        target_version = version
        target_data = self.load_version(target_version)

        next_number = self._max_version_number(versions) + 1
        new_version = self._format_version(next_number)

        published = dict(target_data)
        published["version"] = new_version
        published["lastUpdated"] = self._now()

        self._write_json(self.published_path, published)
        self._write_json(self.versions_dir / f"{new_version}.json", published)

        entry_changelog = changelog.strip() if changelog else f"回滚到 {target_version}"
        new_entry = VersionEntry(
            version=new_version,
            published_at=self._now(),
            changelog=entry_changelog,
            source="rollback",
        ).__dict__
        versions.insert(0, new_entry)

        history["current_version"] = new_version
        history["versions"] = versions
        self._write_json(self.version_history_path, history)
        return published

    def list_history(self) -> Dict[str, Any]:
        self.ensure_migration()
        return self.load_version_history()

    def ensure_version_file(self, version: str) -> Path:
        path = self.versions_dir / f"{version}.json"
        if not path.exists():
            raise FileNotFoundError(f"version file not found: {path}")
        return path
