# -*- coding: utf-8 -*-
"""启动时检查 GitHub Releases 是否有新版本，有则弹窗提示。"""

import json
import socket
import urllib.request
import urllib.error
import webbrowser
from tkinter import messagebox

from constants import VERSION
from utils import log_error

GITHUB_API_URL = "https://api.github.com/repos/xhn272/macro/releases/latest"
REQUEST_TIMEOUT = 10  # 秒

_CHECK_DONE = False  # 每个进程只检查一次


def _parse_version(tag):
    """从 git tag 中提取语义化版本元组。

    支持的格式: "v1.2.3" → (1, 2, 3), "1.2.3" → (1, 2, 3)
    无法解析时返回 None。
    """
    if not tag:
        return None
    tag = tag.strip().lstrip("v")
    try:
        parts = tag.split(".")
        if len(parts) < 2:
            return None
        return tuple(int(p) for p in parts[:3])
    except (ValueError, TypeError):
        return None


def _is_newer(current_str, remote_tag):
    """比较远程版本是否严格大于当前版本。"""
    current = _parse_version(current_str)
    remote = _parse_version(remote_tag)
    if current is None or remote is None:
        return False
    return remote > current


def _show_update_dialog(parent, remote_tag, release_url):
    """在主线程弹出更新提示对话框（由 after() 调度）。"""
    result = messagebox.askyesno(
        "发现新版本",
        f"检测到新版本 {remote_tag}，当前版本为 v{VERSION}。\n\n"
        f"是否打开浏览器下载？",
        parent=parent
    )
    if result:
        webbrowser.open(release_url)


def check_for_updates(parent_window):
    """在后台线程中运行，检查 GitHub 最新 Release 并弹窗提示。

    所有错误都静默处理 —— 更新检查不是关键功能。
    """
    global _CHECK_DONE
    if _CHECK_DONE:
        return
    _CHECK_DONE = True

    try:
        req = urllib.request.Request(GITHUB_API_URL)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "macro-keyboard-manager")

        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        # 跳过预发布版本
        if data.get("prerelease"):
            return

        remote_tag = data.get("tag_name", "")
        if not remote_tag:
            return

        if not _is_newer(VERSION, remote_tag):
            return

        html_url = data.get("html_url", "https://github.com/xhn272/macro/releases")
        parent_window.after(0, lambda: _show_update_dialog(parent_window, remote_tag, html_url))

    except urllib.error.HTTPError as e:
        # 403: 被限制, 429: 请求过多 — 静默跳过
        if e.code not in (403, 429):
            log_error(f"更新检查 HTTP 错误: {e.code}")
    except (urllib.error.URLError, socket.timeout, OSError):
        # DNS 解析失败、网络不通、超时 — 静默跳过
        pass
    except json.JSONDecodeError:
        log_error("更新检查返回了无效的 JSON 数据")
    except Exception:
        log_error("更新检查发生未知异常")
