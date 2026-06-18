# -*- coding: utf-8 -*-
"""工具函数：热键修饰键解析、错误日志记录、管理员权限检查。"""

import os
import sys
import time
import ctypes
import platform
from tkinter import messagebox


def parse_modifiers(key_str, ctrl_var, alt_var, shift_var, win_var):
    """Parse a hotkey string like 'ctrl+shift+a' and set the modifier checkboxes."""
    ctrl_var.set(False)
    alt_var.set(False)
    shift_var.set(False)
    win_var.set(False)
    if not key_str:
        return
    parts = key_str.strip().lower().split('+')
    if len(parts) > 1:
        for mod in parts[:-1]:
            mod = mod.strip()
            if mod == 'ctrl':
                ctrl_var.set(True)
            elif mod == 'alt':
                alt_var.set(True)
            elif mod == 'shift':
                shift_var.set(True)
            elif mod in ('win', 'cmd'):
                win_var.set(True)


def build_modifier_key(current_key, ctrl_var, alt_var, shift_var, win_var):
    """Build a full hotkey string from a base key and modifier checkboxes."""
    if '+' in current_key:
        base = current_key.split('+')[-1].strip()
    else:
        base = current_key.strip()
    if not base:
        return current_key
    mods = []
    if ctrl_var.get():
        mods.append("ctrl")
    if alt_var.get():
        mods.append("alt")
    if shift_var.get():
        mods.append("shift")
    if win_var.get():
        mods.append("win")
    return "+".join(mods) + "+" + base if mods else base


from config import config as app_config


def prune_old_logs(log_dir, keep=None):
    """保留最近 keep 个日志文件，删除更早的。"""
    if keep is None:
        keep = app_config.get("log_keep")
    try:
        files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith(".log")]
        files.sort(key=os.path.getmtime, reverse=True)
        for old in files[keep:]:
            os.remove(old)
    except OSError:
        pass


def log_error(msg):
    os.makedirs("logs", exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    with open(os.path.join("logs", f"error_{timestamp}.log"), "w", encoding="utf-8") as f:
        f.write(f"错误时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Python 版本：{sys.version}\n")
        f.write(f"平台：{platform.platform()}\n")
        f.write(f"\n{msg}")
    prune_old_logs("logs")


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except (AttributeError, OSError):
        return False


def check_admin_gui(parent):
    if not is_admin():
        messagebox.showwarning(
            "权限警告",
            "未以管理员身份运行，可能无法在某些窗口中模拟按键。\n"
            "建议以管理员身份重新运行本程序。",
            parent=parent
        )
