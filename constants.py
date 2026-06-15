# -*- coding: utf-8 -*-
"""常量定义：按键列表、鼠标动作、宏配置文件名等数据。"""

CONFIG_FILE = "macros.json"

VERSION = "1.3.2"  # 不带 v 前缀，需与 git tag 和 build_release.cmd 保持同步

ALL_KEYS = [
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
    "f13", "f14", "f15", "f16", "f17", "f18", "f19", "f20",
    "enter", "esc", "backspace", "tab", "space", "capslock",
    "up", "down", "left", "right",
    "insert", "delete", "home", "end", "page up", "page down",
    "numlock",
    "-", "=", "[", "]", "\\", ";", "'", ",", ".", "/", "`",
    "print screen", "scrolllock", "pause", "menu",
]

MOUSE_ACTIONS = [
    "左键单击", "左键双击", "右键单击", "右键双击",
    "移动到", "滚动向上", "滚动向下"
]

MOUSE_CLICK_MAP = {
    "左键单击": ("left", 1),
    "左键双击": ("left", 2),
    "右键单击": ("right", 1),
    "右键双击": ("right", 2),
}
MOUSE_CLICK_REVERSE = {v: k for k, v in MOUSE_CLICK_MAP.items()}
