# -*- coding: utf-8 -*-
"""应用配置管理：从 config.json 加载用户可设置项，缺失时回退到默认值。"""

import json
import os

CONFIG_FILE = "config.json"

DEFAULTS = {
    "check_update": True,
    "log_keep": 50,
    "macros_file": "macros.json",
    "backup_keep": 10,
    "theme": "litera",
}


class Config:
    """读取 config.json，不存在的键自动回退到 DEFAULTS。加载失败时静默使用默认值。"""

    def __init__(self) -> None:
        self._data = dict(DEFAULTS)
        self._load()

    def _load(self) -> None:
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self._data.update(loaded)
        except (json.JSONDecodeError, OSError):
            pass

    def get(self, key: str):
        return self._data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value) -> None:
        self._data[key] = value

    def save(self) -> None:
        """持久化当前配置到 config.json。写入失败静默跳过。"""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4, ensure_ascii=False)
        except OSError:
            pass


config = Config()
