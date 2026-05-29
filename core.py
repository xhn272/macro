# -*- coding: utf-8 -*-
"""宏管理器核心：MacroManager、步骤执行、崩溃处理。"""

import json
import os
import sys
import time
import traceback
import platform
from tkinter import messagebox

import keyboard
import mouse

from constants import CONFIG_FILE
from utils import log_error, _prune_old_logs


class MacroManager:
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.macros = []
        self.hotkeys = {}
        self.registered = set()

    def load(self):
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
                    self.save()
                self._ensure_stopall_macro()
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
                self.save()
                self._ensure_stopall_macro()
        except Exception as e:
            messagebox.showerror("错误", f"加载配置失败：{e}")

    def save(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.macros, f, indent=4, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败：{e}")

    def _ensure_stopall_macro(self):
        has_stopall = any(
            any(s.get("type") == "STOPALL" for s in m.get("steps", []))
            for m in self.macros
        )
        if not has_stopall:
            stopall_macro = {
                "name": "全局停止",
                "selected": True,
                "trigger": "ctrl+delete",
                "repeat": 1,
                "locked": ["name", "steps", "delete", "selected", "repeat"],
                "steps": [{"type": "STOPALL"}]
            }
            self.macros.insert(0, stopall_macro)
            self.save()

    def is_name_unique(self, name, exclude_index=None):
        for i, m in enumerate(self.macros):
            if i == exclude_index:
                continue
            if m.get("name") == name:
                return False
        return True

    def register_all(self):
        for _, hid in list(self.hotkeys.items()):
            try:
                keyboard.remove_hotkey(hid)
            except Exception as e:
                log_error(f"注册前清理热键失败: {e}")
        self.hotkeys.clear()
        self.registered.clear()

        selected_list = []
        for idx, macro in enumerate(self.macros):
            if macro.get("selected", True) and macro.get("trigger"):
                selected_list.append((idx, macro))

        trigger_map = {}
        conflicts = []
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

        invalid = []
        for idx, macro in selected_list:
            trig = macro["trigger"]
            try:
                steps = macro.get("steps", [])
                rep = macro.get("repeat", 1)

                def action(s=steps, r=rep):
                    execute_steps(s, r)

                hid = keyboard.add_hotkey(trig, action)
                self.hotkeys[trig] = hid
                self.registered.add(idx)
                print(f"已注册：{trig} -> {macro['name']}")
            except Exception as e:
                log_error(f"注册热键失败 [{macro['name']} / {trig}]: {e}")
                invalid.append((macro["name"], trig, str(e)))

        if invalid:
            msg = "以下宏的触发键无效，已被跳过注册：\n\n"
            for name, trig, err in invalid:
                msg += f"• {name} - {trig}\n  原因：{err}\n\n"
            msg += "请编辑这些宏，使用有效的触发键。"
            messagebox.showwarning("触发键无效", msg)
        return True

    def unregister_all(self):
        for _, hid in list(self.hotkeys.items()):
            try:
                keyboard.remove_hotkey(hid)
            except Exception as e:
                log_error(f"取消注册热键失败: {e}")
        self.hotkeys.clear()
        self.registered.clear()

    def register_single(self, index):
        macro = self.macros[index]
        trigger = macro.get("trigger")
        steps = macro.get("steps", [])
        rep = macro.get("repeat", 1)

        def action(s=steps, r=rep):
            execute_steps(s, r)

        hid = keyboard.add_hotkey(trigger, action)
        self.hotkeys[trigger] = hid
        self.registered.add(index)
        print(f"简约模式：已注册 {trigger} -> {macro['name']}")

    def unregister_single(self, index):
        macro = self.macros[index]
        trigger = macro.get("trigger")
        if trigger and trigger in self.hotkeys and index in self.registered:
            try:
                keyboard.remove_hotkey(self.hotkeys[trigger])
                del self.hotkeys[trigger]
                self.registered.remove(index)
                print(f"简约模式：已注销 {trigger} -> {macro['name']}")
            except Exception as e:
                log_error(f"简约模式取消注册热键失败: {e}")


mgr = MacroManager()


def execute_steps(steps, repeat=1):
    for _ in range(repeat):
        for step in steps:
            t = step["type"]
            if t == "STOPALL":
                mgr.unregister_all()
                return
            if t == "key":
                keyboard.send(step["value"])
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
        _prune_old_logs(log_dir)
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = crash_handler
