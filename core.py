# -*- coding: utf-8 -*-
"""宏管理核心：加载/保存配置文件、注册/注销热键、执行宏步骤。"""

import json
import os
import sys
import time
import threading
import traceback
import platform
from tkinter import messagebox
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import keyboard
import mouse

from constants import CONFIG_FILE
from utils import log_error, prune_old_logs

# ── 键盘库扫描码冲突修复 ────────────────────────────────────────────
# "." 映射到扫描码 (52, 83)，其中 83 也被 "delete" 使用。
# 导致按 Delete 键会误触发"."热键。注册热键时临时过滤冲突的扫描码。
_SCANCODE_CONFLICTS = {
    '.': 83,       # 83 = 小键盘小数点/Delete 键共用扫描码
    'period': 83,
    'dot': 83,
    'decimal': 83, # 录制小键盘 Del 键时 keyboard 返回 "decimal"
}
_original_key_to_scan_codes = keyboard.key_to_scan_codes


def _filtered_key_to_scan_codes(key, error_if_missing=True):
    codes = _original_key_to_scan_codes(key, error_if_missing)
    if key in _SCANCODE_CONFLICTS:
        filtered = tuple(c for c in codes if c != _SCANCODE_CONFLICTS[key])
        if not filtered:
            raise ValueError(f'触发键"{key}"不支持（扫描码与Delete键冲突），请换用其他按键。')
        return filtered
    return codes


def _add_hotkey_safe(trigger: str, callback) -> Any:
    """keyboard.add_hotkey 的包装，注册时过滤掉已知的扫描码冲突。"""
    keyboard.key_to_scan_codes = _filtered_key_to_scan_codes
    try:
        return keyboard.add_hotkey(trigger, callback)
    finally:
        keyboard.key_to_scan_codes = _original_key_to_scan_codes

# macro 数据是一个无 schema 的 dict，用类型别名便于阅读
Macro = Dict[str, Any]


class MacroManager:
    """宏数据管理与热键注册的核心层，所有公共方法线程安全。"""

    def __init__(self, config_file: str = CONFIG_FILE) -> None:
        self.config_file = config_file
        self.macros: List[Macro] = []
        self.hotkeys: Dict[str, Any] = {}
        self.registered: Set[int] = set()
        self._lock = threading.Lock()
        self._change_callbacks: List[Callable[[], None]] = []

    def load(self) -> None:
        with self._lock:
            try:
                if os.path.exists(self.config_file):
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        self.macros = json.load(f)
                    migrated = False
                    for m in self.macros:
                        if "enabled" in m and "selected" not in m:
                            m["selected"] = m.pop("enabled")
                            migrated = True
                    if migrated:
                        self._save_unlocked()
                    self._ensure_stopall_unlocked()
                else:
                    self.macros = [{
                        "name": "示例宏",
                        "selected": True,
                        "trigger": "f2",
                        "repeat": 1,
                        "steps": [
                            {"type": "key", "value": "ctrl+shift+l", "delay": 0.1},
                            {"type": "key", "value": "esc", "delay": 0.1},
                            {"type": "key", "value": "delete", "delay": 0.1}
                        ]
                    }]
                    self._save_unlocked()
                    self._ensure_stopall_unlocked()
            except Exception as e:
                messagebox.showerror("错误", f"加载配置失败：{e}")

    def save(self) -> None:
        with self._lock:
            self._save_unlocked()

    def _save_unlocked(self) -> None:
        """内部方法：不加锁，调用方需已持有 self._lock。"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.macros, f, indent=4, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败：{e}")

    def _ensure_stopall_macro(self) -> None:
        with self._lock:
            self._ensure_stopall_unlocked()

    def _ensure_stopall_unlocked(self) -> None:
        """内部方法：不加锁，调用方需已持有 self._lock。"""
        has_stopall = any(
            any(s.get("type") == "STOPALL" for s in m.get("steps", []))
            for m in self.macros
        )
        if not has_stopall:
            stopall_macro: Macro = {
                "name": "全局停止",
                "selected": True,
                "trigger": "ctrl+delete",
                "repeat": 1,
                "locked": ["name", "steps", "delete", "selected", "repeat"],
                "steps": [{"type": "STOPALL"}]
            }
            self.macros.insert(0, stopall_macro)
            self._save_unlocked()

    def is_name_unique(self, name: str, exclude_index: Optional[int] = None) -> bool:
        with self._lock:
            for i, m in enumerate(self.macros):
                if i == exclude_index:
                    continue
                if m.get("name") == name:
                    return False
            return True

    # ── 线程安全的辅助方法（供 UI 层使用）──────────────────────────────

    def get_snapshot(self) -> Tuple[List[Macro], Set[int]]:
        """返回 macros 和 registered 的一致性快照，供 UI 只读遍历。"""
        with self._lock:
            return list(self.macros), set(self.registered)

    def is_any_registered(self) -> bool:
        with self._lock:
            return bool(self.registered)

    def is_index_registered(self, idx: int) -> bool:
        with self._lock:
            return idx in self.registered

    def has_hotkey(self, trigger: str) -> bool:
        with self._lock:
            return trigger in self.hotkeys

    def get_macro(self, idx: int) -> Optional[Macro]:
        """返回指定索引宏的浅拷贝，避免外部直接持有内部引用。"""
        with self._lock:
            if 0 <= idx < len(self.macros):
                return dict(self.macros[idx])
            return None

    def is_field_locked(self, idx: int, field: str) -> bool:
        """检查指定宏的某个字段是否被锁定。索引越界返回 True。"""
        with self._lock:
            if 0 <= idx < len(self.macros):
                return field in self.macros[idx].get("locked", [])
            return True

    def get_macros_count(self) -> int:
        with self._lock:
            return len(self.macros)

    def append_macro(self, macro: Macro) -> int:
        """线程安全地追加宏，返回新索引。"""
        with self._lock:
            idx = len(self.macros)
            self.macros.append(macro)
            self._save_unlocked()
            return idx

    def replace_macro(self, idx: int, macro: Macro) -> None:
        """线程安全地替换指定索引的宏。"""
        with self._lock:
            if 0 <= idx < len(self.macros):
                self.macros[idx] = macro
                self._save_unlocked()

    def save_macro(self, idx: Optional[int], macro: Macro) -> None:
        """线程安全地保存宏：idx 有效则替换，否则追加。"""
        with self._lock:
            if idx is not None and 0 <= idx < len(self.macros):
                self.macros[idx] = macro
            else:
                self.macros.append(macro)
            self._save_unlocked()

    def remove_macro(self, idx: int) -> None:
        """线程安全地删除宏。"""
        with self._lock:
            if 0 <= idx < len(self.macros):
                del self.macros[idx]
                self._save_unlocked()

    def update_selected(self, idx: int, selected: bool) -> None:
        """线程安全地更新宏的选中状态。"""
        with self._lock:
            if 0 <= idx < len(self.macros):
                self.macros[idx]["selected"] = selected
                self._save_unlocked()

    def toggle_selected(self, idx: int) -> Optional[bool]:
        """线程安全地翻转宏的选中状态，返回新值（None 表示索引无效或被锁定）。"""
        with self._lock:
            if 0 <= idx < len(self.macros):
                current = self.macros[idx].get("selected", True)
                self.macros[idx]["selected"] = not current
                self._save_unlocked()
                return not current
            return None

    # ── 热键注册 / 注销 ──────────────────────────────────────────────

    def register_all(self) -> bool:
        with self._lock:
            for _, hid in list(self.hotkeys.items()):
                try:
                    keyboard.remove_hotkey(hid)
                except (ValueError, KeyError) as e:
                    log_error(f"注册前清理热键失败: {e}")
            self.hotkeys.clear()
            self.registered.clear()

            selected_list: List[Tuple[int, Macro]] = []
            for idx, macro in enumerate(self.macros):
                if macro.get("selected", True) and macro.get("trigger"):
                    selected_list.append((idx, macro))

            trigger_map: Dict[str, Tuple[int, Macro]] = {}
            conflicts: List[Tuple[str, str, str]] = []
            for idx, macro in selected_list:
                trig = macro["trigger"]
                if trig in trigger_map:
                    conflicts.append((macro["name"], trig, trigger_map[trig][1]["name"]))
                else:
                    trigger_map[trig] = (idx, macro)

            if conflicts:
                msg = "以下宏使用了相同的触发键，无法同时启用：\n\n"
                for name, trig, existing in conflicts:
                    msg += f'• "{name}" 与 "{existing}" 都使用了 "{trig}"\n'
                msg += "\n请修改宏的触发键后再启用。"
                messagebox.showwarning("触发键冲突", msg)
                return False

            invalid: List[Tuple[str, str, str]] = []
            for idx, macro in selected_list:
                trig = macro["trigger"]
                try:
                    steps = macro.get("steps", [])
                    rep = macro.get("repeat", 1)

                    def action(s=steps, r=rep):
                        if _executing.is_set() and not any(
                            s2.get("type") == "STOPALL" for s2 in s
                        ):
                            return
                        threading.Thread(target=execute_steps, args=(s, r), daemon=True).start()

                    hid = _add_hotkey_safe(trig, action)
                    self.hotkeys[trig] = hid
                    self.registered.add(idx)
                    print(f"已注册：{trig} -> {macro['name']}")
                except (ValueError, RuntimeError) as e:
                    log_error(f"注册热键失败 [{macro['name']} / {trig}]: {e}")
                    invalid.append((macro["name"], trig, str(e)))

            if invalid:
                msg = "以下宏的触发键无效，已被跳过注册：\n\n"
                for name, trig, err in invalid:
                    msg += f"• {name} - {trig}\n  原因：{err}\n\n"
                msg += "请编辑这些宏，使用有效的触发键。"
                messagebox.showwarning("触发键无效", msg)
        return True

    def add_change_callback(self, cb: Callable[[], None]) -> None:
        """注册状态变更回调（热键注销时调用）。回调可能在非主线程执行。"""
        self._change_callbacks.append(cb)

    def _notify_change(self) -> None:
        for cb in self._change_callbacks:
            try:
                cb()
            except Exception:
                pass

    def unregister_all(self) -> None:
        with self._lock:
            for _, hid in list(self.hotkeys.items()):
                try:
                    keyboard.remove_hotkey(hid)
                except (ValueError, KeyError) as e:
                    log_error(f"取消注册热键失败: {e}")
            self.hotkeys.clear()
            self.registered.clear()
        self._notify_change()

    def register_single(self, index: int) -> None:
        with self._lock:
            macro = self.macros[index]
            trigger = macro.get("trigger")
            steps = macro.get("steps", [])
            rep = macro.get("repeat", 1)

            def action(s=steps, r=rep):
                if _executing.is_set():
                    return
                threading.Thread(target=execute_steps, args=(s, r), daemon=True).start()

            hid = _add_hotkey_safe(trigger, action)
            self.hotkeys[trigger] = hid
            self.registered.add(index)
            print(f"简约模式：已注册 {trigger} -> {macro['name']}")

    def unregister_single(self, index: int) -> None:
        with self._lock:
            macro = self.macros[index]
            trigger = macro.get("trigger")
            if trigger and trigger in self.hotkeys and index in self.registered:
                try:
                    keyboard.remove_hotkey(self.hotkeys[trigger])
                    del self.hotkeys[trigger]
                    self.registered.remove(index)
                    print(f"简约模式：已注销 {trigger} -> {macro['name']}")
                except (ValueError, KeyError) as e:
                    log_error(f"简约模式取消注册热键失败: {e}")


mgr = MacroManager()

# 取消标志：STOPALL 置位后，所有正在执行的宏在下一步检查时立即退出
_cancel_event = threading.Event()
# 执行标志：宏步骤执行期间置位，防止合成按键事件误触发其他宏（修饰键状态污染）
_executing = threading.Event()


def send_text_via_wmchar(text):
    """通过 WM_CHAR 逐字符发送 Unicode 文本，不依赖剪贴板和输入法。"""
    import ctypes
    user32 = ctypes.windll.user32
    try:
        hwnd = user32.GetForegroundWindow()
    except Exception:
        hwnd = 0
    if not hwnd:
        # 无前台窗口时回退到剪贴板方式
        _send_text_via_clipboard(text)
        return
    for ch in text:
        user32.PostMessageW(hwnd, 0x0102, ord(ch), 0)


def _send_text_via_clipboard(text):
    """剪贴板回退方案：仅在前台窗口不可用时使用。"""
    try:
        import pyperclip
    except ImportError:
        return
    old = pyperclip.paste()
    try:
        pyperclip.copy(text)
        keyboard.send("ctrl+v")
        time.sleep(0.15)
    finally:
        pyperclip.copy(old)


def execute_steps(steps, repeat=1):
    _cancel_event.clear()
    _executing.set()
    try:
        for _ in range(repeat):
            for step in steps:
                if _cancel_event.is_set():
                    return
                t = step["type"]
                if t == "STOPALL":
                    _cancel_event.set()
                    mgr.unregister_all()
                    return
                if t == "key":
                    keyboard.send(step["value"])
                elif t == "text":
                    send_text_via_wmchar(step["value"])
                elif t == "mouse":
                    act = step["action"]
                    if act == "click":
                        btn = step.get("button", "left")
                        clicks = step.get("clicks", 1)
                        for _ in range(clicks):
                            mouse.click(btn)
                            if clicks > 1:
                                time.sleep(0.05)
                    elif act == "move":
                        mouse.move(step.get("x", 0), step.get("y", 0))
                    elif act == "scroll":
                        mouse.wheel(step.get("dy", 0))
                elif t == "wait":
                    time.sleep(float(step["value"]))
                if step.get("delay", 0) > 0:
                    time.sleep(step["delay"])
    finally:
        _executing.clear()


def setup_crash_handler():
    log_dir = "logs"

    def crash_handler(exc_type, exc_value, exc_tb):
        os.makedirs(log_dir, exist_ok=True)
        filename = os.path.join(log_dir, f"crash_{time.strftime('%Y-%m-%d_%H-%M-%S')}.log")
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"崩溃时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"宏数量：{len(mgr.macros)}\n")
            f.write(f"Python 版本：{sys.version}\n")
            f.write(f"平台：{platform.platform()}\n")
            f.write(f"\n{tb_text}")
        prune_old_logs(log_dir)
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = crash_handler
