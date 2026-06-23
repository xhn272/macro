# -*- coding: utf-8 -*-
"""暗/亮双主题支持。用 ttk clam 基座 + 自定义色板实现，零额外依赖。"""

import tkinter as tk
from tkinter import ttk

from config import config as app_config

# ── 暗色色板 ─────────────────────────────────────────────────
_DARK_COLORS = {
    "bg": "#2d2d2d",
    "fg": "#e0e0e0",
    "entry_bg": "#3c3c3c",
    "button_bg": "#404040",
    "button_active": "#505050",
    "heading_bg": "#444444",
    "select_bg": "#1a5fb4",
    "select_fg": "#ffffff",
    "disabled_fg": "#888888",
    "tree_selected": "#4fc3f7",
    "tree_disabled": "#888888",
}


# ── 主题应用 ─────────────────────────────────────────────────

def apply_theme(theme_name: str) -> None:
    """切换全局 ttk 样式。"""
    if theme_name == "dark":
        _apply_dark()
    else:
        _apply_light()


def _apply_light() -> None:
    s = ttk.Style()
    s.theme_use("vista")
    # 恢复自定义字号（theme_use 会重置）
    s.configure("Treeview", font=("TkDefaultFont", 12))
    s.configure("Treeview.Heading", font=("TkDefaultFont", 12, "bold"))


def _apply_dark() -> None:
    c = _DARK_COLORS
    s = ttk.Style()
    s.theme_use("clam")  # clam 尊重自定义颜色

    # ── 全局默认 ──
    s.configure(".", background=c["bg"], foreground=c["fg"])

    # ── 框架类 ──
    s.configure("TFrame", background=c["bg"])
    s.configure("TLabelframe", background=c["bg"])
    s.configure("TLabelframe.Label", background=c["bg"], foreground=c["fg"])
    s.configure("TPanedwindow", background=c["bg"])

    # ── 标签 ──
    s.configure("TLabel", background=c["bg"], foreground=c["fg"])

    # ── 按钮 ──
    s.configure("TButton", background=c["button_bg"], foreground=c["fg"])
    s.map("TButton", background=[("active", c["button_active"])])

    # ── 输入类 ──
    s.configure("TEntry", fieldbackground=c["entry_bg"], foreground=c["fg"])
    s.configure("TCombobox", fieldbackground=c["entry_bg"], foreground=c["fg"])
    s.configure("TSpinbox", fieldbackground=c["entry_bg"], foreground=c["fg"])

    # ── 复选框 ──
    s.configure("TCheckbutton", background=c["bg"], foreground=c["fg"])

    # ── 列表/表格 ──
    s.configure("Treeview", background=c["bg"], foreground=c["fg"],
                fieldbackground=c["entry_bg"])
    s.configure("Treeview.Heading", background=c["heading_bg"], foreground=c["fg"])
    s.map("Treeview",
          background=[("selected", c["select_bg"])],
          foreground=[("selected", c["select_fg"])])

    # ── 滚动条 ──
    s.configure("TScrollbar", background=c["bg"], troughcolor=c["entry_bg"])

    # ── 分隔线（PanedWindow 把手） ──
    s.configure("TSeparator", background=c["button_bg"])

    # ── 恢复自定义字号 ──
    s.configure("Treeview", font=("TkDefaultFont", 12))
    s.configure("Treeview.Heading", font=("TkDefaultFont", 12, "bold"))


# ── Treeview 标签色 ─────────────────────────────────────────

def treeview_tag_colors(theme_name: str):
    """返回 Treeview 应使用的 tag_configure 颜色。"""
    if theme_name == "dark":
        return {"selected": _DARK_COLORS["tree_selected"],
                "disabled": _DARK_COLORS["tree_disabled"]}
    return {"selected": "green", "disabled": "black"}


# ── tk 原生控件色（Listbox / Canvas / Text）─────────────────

def tk_widget_colors(theme_name: str):
    """返回 tk 原生控件的背景/前景色。"""
    if theme_name == "dark":
        c = _DARK_COLORS
        return {
            "bg": c["bg"], "fg": c["fg"],
            "entry_bg": c["entry_bg"],
            "insertbackground": c["fg"],
            "selectbackground": c["select_bg"],
            "selectforeground": c["select_fg"],
        }
    return {
        "bg": "white", "fg": "black",
        "entry_bg": "white",
        "insertbackground": "black",
        "selectbackground": "#0078d7",
        "selectforeground": "white",
    }


# ── 辅助：对指定 Treeview 应用 tag 色 ────────────────────────

def apply_treeview_tags(tree, theme_name: str) -> None:
    """对已创建的 Treeview 实例设置 selected/disabled 标签颜色。"""
    colors = treeview_tag_colors(theme_name)
    tree.tag_configure("selected", foreground=colors["selected"])
    tree.tag_configure("disabled", foreground=colors["disabled"])
