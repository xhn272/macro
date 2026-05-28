# -*- coding: utf-8 -*-
"""
按键宏管理器 - 多窗口版本
经典模式和简约模式为独立窗口，通过视图菜单切换
"""

import json
import os
import sys
import time
import ctypes
import platform
import tkinter as tk
from tkinter import messagebox, ttk

import keyboard
import mouse
from about_text import ABOUT_TEXT

# ---------- 常量 ----------
CONFIG_FILE = "macros.json"

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
    "左键单击", "左键双击", "右键单击",
    "移动到", "滚动向上", "滚动向下"
]

# ---------- 宏管理器 ----------
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


def log_error(msg):
    os.makedirs("logs", exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    with open(os.path.join("logs", f"error_{timestamp}.log"), "w", encoding="utf-8") as f:
        f.write(f"错误时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Python 版本：{sys.version}\n")
        f.write(f"平台：{platform.platform()}\n")
        f.write(f"\n{msg}")


# ---------- 管理员检查 ----------
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def check_admin_gui(parent):
    if not is_admin():
        messagebox.showwarning(
            "权限警告",
            "未以管理员身份运行，可能无法在某些窗口中模拟按键。\n"
            "建议以管理员身份重新运行本程序。",
            parent=parent
        )

_admin_warned = False


# ---------- 执行步骤 ----------
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


# ---------- 编辑宏窗口 ----------
class EditMacroDialog:
    def __init__(self, parent, macro_index, on_save_callback):
        self.parent = parent
        self.macro_index = macro_index
        self.on_save = on_save_callback

        if macro_index is not None:
            self.macro = mgr.macros[macro_index].copy()
        else:
            self.macro = {"name": "新宏", "selected": True, "trigger": "", "repeat": 1, "steps": []}

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑宏" if macro_index is not None else "新建宏")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        self.dialog.minsize(600, 400)

        paned = ttk.PanedWindow(self.dialog, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ---------- 左侧：宏编辑区域 ----------
        self.left_frame = ttk.Frame(paned)
        paned.add(self.left_frame, weight=2)

        basic_frame = ttk.LabelFrame(self.left_frame, text="基本信息", padding="8")
        basic_frame.pack(fill=tk.X, pady=(0, 8))

        # 名称
        row1 = ttk.Frame(basic_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="名称：", width=8).pack(side=tk.LEFT)
        self.name_var = tk.StringVar(value=self.macro["name"])
        self.name_entry = ttk.Entry(row1, textvariable=self.name_var)
        self.name_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # 触发键 + 录制按钮
        row2 = ttk.Frame(basic_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="触发键：", width=8).pack(side=tk.LEFT)
        self.trigger_var = tk.StringVar(value=self.macro["trigger"])
        self.trigger_combo = ttk.Combobox(row2, textvariable=self.trigger_var, values=ALL_KEYS)
        self.trigger_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.trigger_combo.bind("<<ComboboxSelected>>", self.on_trigger_base_selected)
        self.record_btn = ttk.Button(row2, text="录制", command=self._record_hotkey, width=6)
        self.record_btn.pack(side=tk.LEFT, padx=5)

        # 修饰键
        mod_frame = ttk.Frame(basic_frame)
        mod_frame.pack(fill=tk.X, pady=2)
        ttk.Label(mod_frame, text="修饰键：", width=8).pack(side=tk.LEFT)
        self.ctrl_var = tk.BooleanVar()
        self.alt_var = tk.BooleanVar()
        self.shift_var = tk.BooleanVar()
        self.win_var = tk.BooleanVar()
        cb_frame = ttk.Frame(mod_frame)
        cb_frame.pack(side=tk.LEFT, padx=5)
        self.mod_cbs = []
        cb = ttk.Checkbutton(cb_frame, text="Ctrl", variable=self.ctrl_var, command=self.update_trigger_from_modifiers)
        cb.pack(side=tk.LEFT, padx=5); self.mod_cbs.append(cb)
        cb = ttk.Checkbutton(cb_frame, text="Alt", variable=self.alt_var, command=self.update_trigger_from_modifiers)
        cb.pack(side=tk.LEFT, padx=5); self.mod_cbs.append(cb)
        cb = ttk.Checkbutton(cb_frame, text="Shift", variable=self.shift_var, command=self.update_trigger_from_modifiers)
        cb.pack(side=tk.LEFT, padx=5); self.mod_cbs.append(cb)
        cb = ttk.Checkbutton(cb_frame, text="Win", variable=self.win_var, command=self.update_trigger_from_modifiers)
        cb.pack(side=tk.LEFT, padx=5); self.mod_cbs.append(cb)

        # 循环次数
        row4 = ttk.Frame(basic_frame)
        row4.pack(fill=tk.X, pady=2)
        ttk.Label(row4, text="循环次数：", width=8).pack(side=tk.LEFT)
        self.repeat_var = tk.IntVar(value=self.macro.get("repeat", 1))
        self.repeat_spinbox = ttk.Spinbox(row4, from_=1, to=999, textvariable=self.repeat_var, width=8)
        self.repeat_spinbox.pack(side=tk.LEFT, padx=5)
        ttk.Label(row4, text="次").pack(side=tk.LEFT)

        # 步骤列表区域
        steps_frame = ttk.LabelFrame(self.left_frame, text="执行步骤", padding="8")
        steps_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        list_container = ttk.Frame(steps_frame)
        list_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.steps_listbox = tk.Listbox(list_container, height=6, width=40, font=('Consolas', 10))
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.steps_listbox.yview)
        self.steps_listbox.configure(yscrollcommand=scrollbar.set)
        self.steps_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        right_panel = ttk.Frame(steps_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))

        step_btn_frame = ttk.LabelFrame(right_panel, text="步骤操作", padding="5")
        step_btn_frame.pack(fill=tk.X, pady=(0, 5))
        self.step_buttons = []
        btn = ttk.Button(step_btn_frame, text="添加步骤", command=self.add_step, width=12)
        btn.pack(pady=2, padx=5, fill=tk.X); self.step_buttons.append(btn)
        btn = ttk.Button(step_btn_frame, text="编辑步骤", command=self.edit_step, width=12)
        btn.pack(pady=2, padx=5, fill=tk.X); self.step_buttons.append(btn)
        btn = ttk.Button(step_btn_frame, text="删除步骤", command=self.delete_step, width=12)
        btn.pack(pady=2, padx=5, fill=tk.X); self.step_buttons.append(btn)
        btn = ttk.Button(step_btn_frame, text="上移", command=self.move_step_up, width=12)
        btn.pack(pady=2, padx=5, fill=tk.X); self.step_buttons.append(btn)
        btn = ttk.Button(step_btn_frame, text="下移", command=self.move_step_down, width=12)
        btn.pack(pady=2, padx=5, fill=tk.X); self.step_buttons.append(btn)

        macro_btn_frame = ttk.LabelFrame(right_panel, text="宏操作", padding="5")
        macro_btn_frame.pack(fill=tk.X)
        ttk.Button(macro_btn_frame, text="保存宏", command=self.save, width=12).pack(pady=2, padx=5, fill=tk.X)
        ttk.Button(macro_btn_frame, text="取消", command=self.dialog.destroy, width=12).pack(pady=2, padx=5, fill=tk.X)

        # ---------- 右侧：步骤编辑区域 ----------
        self.right_frame = ttk.Frame(paned)
        paned.add(self.right_frame, weight=1)

        step_editor_container = ttk.LabelFrame(self.right_frame, text="编辑步骤", padding="5")
        step_editor_container.pack(fill=tk.BOTH, expand=True)

        self.right_placeholder = ttk.Label(step_editor_container,
                                           text='请从左侧选择一个步骤\n点击"添加步骤"或"编辑步骤"',
                                           font=('Microsoft YaHei', 12), anchor=tk.CENTER)
        self.right_placeholder.pack(fill=tk.BOTH, expand=True)

        self.step_editor = ttk.Frame(step_editor_container)
        self._build_step_editor(self.step_editor)
        self.step_editor.pack(fill=tk.BOTH, expand=True)
        self.step_editor.pack_forget()

        self.current_step_index = None
        self.refresh_steps_list()
        self.parse_trigger_modifiers()
        self._adjust_window_size()
        self._apply_locks()

    # ---------- 辅助方法 ----------
    def _adjust_window_size(self):
        """动态调整窗口大小，确保左右内容完整显示"""
        try:
            self.dialog.update_idletasks()
            left_height = self.left_frame.winfo_reqheight()
            right_height = self.right_frame.winfo_reqheight()
            max_height = max(left_height, right_height) + 30
            deco_height = self.dialog.winfo_rooty() - self.dialog.winfo_y()
            total_height = max_height + deco_height + 10
            current_width = self.dialog.winfo_width()
            if current_width < 600:
                current_width = 650
            self.dialog.geometry(f"{current_width}x{total_height}")
            self.dialog.minsize(600, total_height)
        except Exception as e:
            log_error(f"调整编辑窗口高度时出错: {e}")

    # locked 字段可用值: "name" "trigger" "steps" "delete" "selected" "repeat"
    def _apply_locks(self):
        locked = self.macro.get("locked", [])
        if not locked:
            return
        if "name" in locked:
            self.name_entry.config(state=tk.DISABLED)
        if "trigger" in locked:
            self.trigger_combo.config(state=tk.DISABLED)
            self.record_btn.config(state=tk.DISABLED)
            for cb in self.mod_cbs:
                cb.config(state=tk.DISABLED)
        if "steps" in locked:
            for btn in self.step_buttons:
                btn.config(state=tk.DISABLED)
        if "repeat" in locked:
            self.repeat_spinbox.config(state=tk.DISABLED)

    def parse_trigger_modifiers(self):
        trigger = self.trigger_var.get().strip().lower()
        if not trigger:
            return
        parts = trigger.split('+')
        if len(parts) > 1:
            mods = parts[:-1]
            self.ctrl_var.set(False)
            self.alt_var.set(False)
            self.shift_var.set(False)
            self.win_var.set(False)
            for mod in mods:
                mod = mod.strip()
                if mod == 'ctrl':
                    self.ctrl_var.set(True)
                elif mod == 'alt':
                    self.alt_var.set(True)
                elif mod == 'shift':
                    self.shift_var.set(True)
                elif mod in ('win', 'cmd'):
                    self.win_var.set(True)

    def _record_hotkey(self):
        import threading
        record_dialog = tk.Toplevel(self.dialog)
        record_dialog.title("录制热键")
        record_dialog.transient(self.dialog)
        record_dialog.grab_set()
        record_dialog.geometry("300x150")
        record_dialog.resizable(False, False)

        label = ttk.Label(record_dialog,
                          text="请按下您想要的热键组合\n（例如 Ctrl+C、Alt+F4 等）\n按下后自动完成录制",
                          font=('Microsoft YaHei', 10), justify=tk.CENTER)
        label.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

        result = [None]

        def do_record():
            try:
                hotkey = keyboard.read_hotkey(suppress=False)
                result[0] = hotkey
            except Exception as e:
                log_error(f"录制热键时出错: {e}")
                result[0] = None
            finally:
                self.dialog.after(0, finish_record)

        def finish_record():
            if record_dialog.winfo_exists():
                record_dialog.destroy()
            if result[0]:
                self.trigger_var.set(result[0])
                self.parse_trigger_modifiers()
                self.update_trigger_from_modifiers()

        def cancel():
            record_dialog.destroy()

        threading.Thread(target=do_record, daemon=True).start()
        ttk.Button(record_dialog, text="取消", command=cancel).pack(pady=10)

    def on_trigger_base_selected(self, event=None):
        self.update_trigger_from_modifiers()

    def update_trigger_from_modifiers(self):
        current = self.trigger_combo.get().strip()
        if '+' in current:
            base = current.split('+')[-1].strip()
        else:
            base = current
        if not base:
            return
        mods = []
        if self.ctrl_var.get():
            mods.append("ctrl")
        if self.alt_var.get():
            mods.append("alt")
        if self.shift_var.get():
            mods.append("shift")
        if self.win_var.get():
            mods.append("win")
        new = "+".join(mods) + "+" + base if mods else base
        self.trigger_var.set(new)

    def refresh_steps_list(self):
        self.steps_listbox.delete(0, tk.END)
        for step in self.macro["steps"]:
            desc = self._format_step(step)
            self.steps_listbox.insert(tk.END, desc)

    def _format_step(self, step):
        t = step["type"]
        if t == "STOPALL":
            desc = "特殊: 全局停止"
        elif t == "key":
            desc = f"按键: {step['value']}"
        elif t == "mouse":
            act = step["action"]
            if act == "click":
                btn = step.get("button", "left")
                clicks = step.get("clicks", 1)
                desc = f"鼠标: {btn}{'双击' if clicks == 2 else '单击'}"
            elif act == "move":
                desc = f"鼠标: 移动到 ({step.get('x', 0)},{step.get('y', 0)})"
            elif act == "scroll":
                dy = step.get("dy", 0)
                direction = "向上" if dy > 0 else "向下"
                desc = f"鼠标: 滚动{direction} {abs(dy)}行"
            else:
                desc = "鼠标: 未知"
        else:  # wait
            desc = f"等待: {step['value']}秒"

        # 添加执行后延迟信息（如果有）
        if step.get("delay", 0) > 0:
            desc += f" (延迟 {step['delay']}秒)"
        return desc

    def add_step(self):
        self.current_step_index = None
        self._clear_edit_form()
        self._show_editor()
        self.edit_type_var.set("按键")
        self.on_edit_type_change()

    def edit_step(self):
        sel = self.steps_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一个步骤")
            return
        self.current_step_index = sel[0]
        step = self.macro["steps"][self.current_step_index]
        self._load_step_to_edit(step)
        self._show_editor()

    def delete_step(self):
        sel = self.steps_listbox.curselection()
        if not sel:
            return
        del self.macro["steps"][sel[0]]
        self.refresh_steps_list()
        if self.current_step_index is not None and self.current_step_index >= len(self.macro["steps"]):
            self.cancel_edit()

    def move_step_up(self):
        sel = self.steps_listbox.curselection()
        if not sel or sel[0] == 0:
            return
        idx = sel[0]
        self.macro["steps"][idx], self.macro["steps"][idx - 1] = self.macro["steps"][idx - 1], self.macro["steps"][idx]
        self.refresh_steps_list()
        self.steps_listbox.selection_set(idx - 1)

    def move_step_down(self):
        sel = self.steps_listbox.curselection()
        if not sel or sel[0] == len(self.macro["steps"]) - 1:
            return
        idx = sel[0]
        self.macro["steps"][idx], self.macro["steps"][idx + 1] = self.macro["steps"][idx + 1], self.macro["steps"][idx]
        self.refresh_steps_list()
        self.steps_listbox.selection_set(idx + 1)

    def _build_step_editor(self, parent):
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scrollable = ttk.Frame(canvas)
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 设置列权重，使第二列可扩展，便于右对齐下拉框
        scrollable.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(scrollable, text="步骤类型：").grid(row=row, column=0, sticky=tk.W, padx=(10, 0), pady=8)
        self.edit_type_var = tk.StringVar(value="按键")
        type_combo = ttk.Combobox(scrollable, textvariable=self.edit_type_var,
                                  values=["按键", "等待", "鼠标"], state="readonly", width=10)
        # 下拉框右对齐：使用 sticky=tk.E，并确保列1有足够空间
        type_combo.grid(row=row, column=1, sticky=tk.E, padx=(0, 10), pady=8)
        type_combo.bind("<<ComboboxSelected>>", self.on_edit_type_change)
        row += 1

        self.edit_value_frame = ttk.Frame(scrollable)
        self.edit_value_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W + tk.E, padx=10, pady=5)
        self.edit_value_frame.columnconfigure(0, weight=1)

        self.edit_key_combo = ttk.Combobox(self.edit_value_frame, values=ALL_KEYS, width=25)
        self.edit_mouse_frame = ttk.Frame(self.edit_value_frame)
        self.edit_mouse_action = tk.StringVar()
        self.edit_mouse_combo = ttk.Combobox(self.edit_mouse_frame, textvariable=self.edit_mouse_action,
                                             values=MOUSE_ACTIONS, state="readonly", width=14)
        self.edit_mouse_combo.pack(side=tk.LEFT, padx=2)
        self.edit_mouse_combo.bind("<<ComboboxSelected>>", self.on_edit_mouse_action_changed)
        self.edit_mouse_param_frame = ttk.Frame(self.edit_mouse_frame)
        self.edit_mouse_param_frame.pack(side=tk.LEFT, padx=5)
        self.edit_wait_entry = ttk.Entry(self.edit_value_frame, width=25)

        self.edit_hint = ttk.Label(scrollable, text="", foreground="gray")
        self.edit_hint.grid(row=row + 1, column=0, columnspan=2, sticky=tk.W, padx=10, pady=2)

        row += 2
        self.edit_mod_frame = ttk.Frame(scrollable)
        self.edit_mod_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=10, pady=5)
        self.edit_ctrl = tk.BooleanVar()
        self.edit_alt = tk.BooleanVar()
        self.edit_shift = tk.BooleanVar()
        self.edit_win = tk.BooleanVar()
        ttk.Checkbutton(self.edit_mod_frame, text="Ctrl", variable=self.edit_ctrl, command=self.update_edit_key).pack(
            side=tk.LEFT, padx=2)
        ttk.Checkbutton(self.edit_mod_frame, text="Alt", variable=self.edit_alt, command=self.update_edit_key).pack(
            side=tk.LEFT, padx=2)
        ttk.Checkbutton(self.edit_mod_frame, text="Shift", variable=self.edit_shift, command=self.update_edit_key).pack(
            side=tk.LEFT, padx=2)
        ttk.Checkbutton(self.edit_mod_frame, text="Win", variable=self.edit_win, command=self.update_edit_key).pack(
            side=tk.LEFT, padx=2)
        self.edit_mod_frame.grid_remove()

        # 延迟行（等待类型时隐藏）
        row += 1
        self.delay_frame = ttk.Frame(scrollable)
        self.delay_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=10, pady=8)
        ttk.Label(self.delay_frame, text="执行后延迟(秒)：").pack(side=tk.LEFT)
        self.edit_delay_var = tk.StringVar(value="0")
        delay_entry = ttk.Entry(self.delay_frame, textvariable=self.edit_delay_var, width=8)
        delay_entry.pack(side=tk.LEFT, padx=5)

        row += 1
        self.edit_coord_label = ttk.Label(scrollable, text="", foreground="blue")
        self.edit_coord_label.grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=10, pady=2)

        row += 1
        btn_frame = ttk.Frame(scrollable)
        btn_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=20, padx=10)
        ttk.Button(btn_frame, text="保存步骤", command=self.save_step).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消编辑", command=self.cancel_edit).pack(side=tk.LEFT, padx=10)

        self.mouse_tracking = False
        self.after_id = None
        self.edit_mouse_param_inner = None

    def _show_editor(self):
        self.right_placeholder.pack_forget()
        self.step_editor.pack(fill=tk.BOTH, expand=True)
        self._adjust_window_size()

    def _hide_editor(self):
        self.step_editor.pack_forget()
        self.right_placeholder.pack(fill=tk.BOTH, expand=True)
        self._adjust_window_size()

    def _clear_edit_form(self):
        self.edit_type_var.set("按键")
        self.on_edit_type_change()
        self.edit_key_combo.set("")
        self.edit_wait_entry.delete(0, tk.END)
        self.edit_mouse_action.set("")
        self.edit_delay_var.set("0")
        self.edit_ctrl.set(False)
        self.edit_alt.set(False)
        self.edit_shift.set(False)
        self.edit_win.set(False)
        self.stop_mouse_tracking()

    def _load_step_to_edit(self, step):
        self._clear_edit_form()
        typ = step["type"]
        if typ == "key":
            self.edit_type_var.set("按键")
        elif typ == "wait":
            self.edit_type_var.set("等待")
        else:
            self.edit_type_var.set("鼠标")
        self.on_edit_type_change()
        if typ == "key":
            self.edit_key_combo.set(step["value"])
            self._parse_edit_key_modifiers(step["value"])
        elif typ == "mouse":
            act = step["action"]
            if act == "click":
                btn = step.get("button", "left")
                clicks = step.get("clicks", 1)
                if clicks == 2:
                    self.edit_mouse_action.set("左键双击" if btn == "left" else "右键双击")
                else:
                    self.edit_mouse_action.set("左键单击" if btn == "left" else "右键单击")
            elif act == "move":
                self.edit_mouse_action.set("移动到")
            elif act == "scroll":
                dy = step.get("dy", 0)
                self.edit_mouse_action.set("滚动向上" if dy > 0 else "滚动向下")
            self.on_edit_mouse_action_changed()
            if act == "move":
                self.edit_mouse_x_entry.delete(0, tk.END)
                self.edit_mouse_x_entry.insert(0, str(step.get("x", 0)))
                self.edit_mouse_y_entry.delete(0, tk.END)
                self.edit_mouse_y_entry.insert(0, str(step.get("y", 0)))
            elif act == "scroll":
                self.edit_mouse_scroll_entry.delete(0, tk.END)
                self.edit_mouse_scroll_entry.insert(0, str(abs(step.get("dy", 1))))
        else:
            self.edit_wait_entry.insert(0, str(step["value"]))
        self.edit_delay_var.set(str(step.get("delay", 0)))

    def on_edit_type_change(self, event=None):
        typ_text = self.edit_type_var.get()
        if typ_text == "按键":
            typ = "key"
        elif typ_text == "等待":
            typ = "wait"
        elif typ_text == "鼠标":
            typ = "mouse"
        else:
            typ = "key"
        self.edit_key_combo.pack_forget()
        self.edit_mouse_frame.pack_forget()
        self.edit_wait_entry.pack_forget()
        self.edit_mod_frame.grid_remove()
        self.edit_hint.config(text="")
        self.stop_mouse_tracking()
        if typ == "key":
            self.edit_key_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.edit_mod_frame.grid()
            self.edit_hint.config(text="例如：ctrl+c, f2, enter")
            self.delay_frame.grid()  # 显示延迟行
        elif typ == "mouse":
            self.edit_mouse_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.edit_hint.config(text="选择鼠标动作并设置参数")
            self.delay_frame.grid()  # 显示延迟行
        else:  # wait
            self.edit_wait_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.edit_hint.config(text="等待秒数，如 0.5")
            self.delay_frame.grid_remove()  # 隐藏延迟行

    def on_edit_mouse_action_changed(self, event=None):
        if self.edit_mouse_param_inner:
            self.edit_mouse_param_inner.destroy()
        act = self.edit_mouse_action.get()
        if not act:
            return
        self.stop_mouse_tracking()
        self.edit_mouse_param_inner = ttk.Frame(self.edit_mouse_param_frame)
        self.edit_mouse_param_inner.pack()
        if act == "移动到":
            ttk.Label(self.edit_mouse_param_inner, text="X:").pack(side=tk.LEFT)
            self.edit_mouse_x_entry = ttk.Entry(self.edit_mouse_param_inner, width=5)
            self.edit_mouse_x_entry.pack(side=tk.LEFT, padx=2)
            self.edit_mouse_x_entry.insert(0, "500")
            ttk.Label(self.edit_mouse_param_inner, text="Y:").pack(side=tk.LEFT)
            self.edit_mouse_y_entry = ttk.Entry(self.edit_mouse_param_inner, width=5)
            self.edit_mouse_y_entry.pack(side=tk.LEFT, padx=2)
            self.edit_mouse_y_entry.insert(0, "300")
            self.start_mouse_tracking()
        elif act in ("滚动向上", "滚动向下"):
            ttk.Label(self.edit_mouse_param_inner, text="行数:").pack(side=tk.LEFT)
            self.edit_mouse_scroll_entry = ttk.Entry(self.edit_mouse_param_inner, width=5)
            self.edit_mouse_scroll_entry.pack(side=tk.LEFT, padx=2)
            self.edit_mouse_scroll_entry.insert(0, "1")
            self.edit_coord_label.config(text="")
        else:
            self.edit_coord_label.config(text="")

    def _parse_edit_key_modifiers(self, key_str):
        k = key_str.strip().lower()
        if not k:
            return
        parts = k.split('+')
        if len(parts) > 1:
            mods = parts[:-1]
            self.edit_ctrl.set(False)
            self.edit_alt.set(False)
            self.edit_shift.set(False)
            self.edit_win.set(False)
            for m in mods:
                m = m.strip()
                if m == 'ctrl':
                    self.edit_ctrl.set(True)
                elif m == 'alt':
                    self.edit_alt.set(True)
                elif m == 'shift':
                    self.edit_shift.set(True)
                elif m in ('win', 'cmd'):
                    self.edit_win.set(True)
        else:
            # 没有修饰键时全部置为 False
            self.edit_ctrl.set(False)
            self.edit_alt.set(False)
            self.edit_shift.set(False)
            self.edit_win.set(False)

    def update_edit_key(self):
        if self.edit_type_var.get() != "按键":  # 修正：使用中文选项
            return
        cur = self.edit_key_combo.get().strip()
        if '+' in cur:
            base = cur.split('+')[-1].strip()
        else:
            base = cur
        if not base:
            return
        mods = []
        if self.edit_ctrl.get():
            mods.append("ctrl")
        if self.edit_alt.get():
            mods.append("alt")
        if self.edit_shift.get():
            mods.append("shift")
        if self.edit_win.get():
            mods.append("win")
        new = "+".join(mods) + "+" + base if mods else base
        self.edit_key_combo.set(new)

    def start_mouse_tracking(self):
        if self.mouse_tracking:
            return
        self.mouse_tracking = True
        self.update_mouse_coords()

    def stop_mouse_tracking(self):
        if self.after_id:
            self.dialog.after_cancel(self.after_id)
            self.after_id = None
        self.mouse_tracking = False
        try:
            if self.edit_coord_label.winfo_exists():
                self.edit_coord_label.config(text="")
        except tk.TclError:
            pass

    def update_mouse_coords(self):
        if not self.mouse_tracking:
            return
        try:
            x, y = mouse.get_position()
            self.edit_coord_label.config(text=f"当前鼠标位置: X={x}, Y={y}")
        except Exception as e:
            log_error(f"获取鼠标位置失败: {e}")
            self.edit_coord_label.config(text="获取鼠标位置失败")
        self.after_id = self.dialog.after(100, self.update_mouse_coords)

    def save_step(self):
        typ_text = self.edit_type_var.get()
        delay_str = self.edit_delay_var.get().strip()
        if not delay_str:
            delay = 0.0
        else:
            try:
                delay = float(delay_str)
            except ValueError:
                messagebox.showerror("错误", "延迟必须为数字")
                return
        if delay < 0:
            messagebox.showerror("错误", "延迟不能为负数")
            return

        if typ_text == "按键":
            value = self.edit_key_combo.get().strip()
            if not value:
                messagebox.showerror("错误", "请输入按键")
                return
            step = {"type": "key", "value": value, "delay": delay}
        elif typ_text == "等待":
            value = self.edit_wait_entry.get().strip()
            if not value:
                messagebox.showerror("错误", "请输入等待时间")
                return
            try:
                value = float(value)
                if value < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("错误", "等待时间必须为数字（秒）")
                return
            step = {"type": "wait", "value": value, "delay": delay}
        else:
            act = self.edit_mouse_action.get()
            if not act:
                messagebox.showerror("错误", "请选择鼠标动作")
                return
            if act == "左键单击":
                step = {"type": "mouse", "action": "click", "button": "left", "clicks": 1, "delay": delay}
            elif act == "左键双击":
                step = {"type": "mouse", "action": "click", "button": "left", "clicks": 2, "delay": delay}
            elif act == "右键单击":
                step = {"type": "mouse", "action": "click", "button": "right", "clicks": 1, "delay": delay}
            elif act == "右键双击":
                step = {"type": "mouse", "action": "click", "button": "right", "clicks": 2, "delay": delay}
            elif act == "移动到":
                try:
                    x = int(self.edit_mouse_x_entry.get())
                    y = int(self.edit_mouse_y_entry.get())
                except ValueError:
                    messagebox.showerror("错误", "坐标必须为整数")
                    return
                step = {"type": "mouse", "action": "move", "x": x, "y": y, "delay": delay}
            elif act == "滚动向上":
                try:
                    rows = int(self.edit_mouse_scroll_entry.get())
                except ValueError:
                    messagebox.showerror("错误", "行数必须为整数")
                    return
                step = {"type": "mouse", "action": "scroll", "dy": rows, "delay": delay}
            elif act == "滚动向下":
                try:
                    rows = int(self.edit_mouse_scroll_entry.get())
                except ValueError:
                    messagebox.showerror("错误", "行数必须为整数")
                    return
                step = {"type": "mouse", "action": "scroll", "dy": -rows, "delay": delay}
            else:
                messagebox.showerror("错误", "未知鼠标动作")
                return

        if self.current_step_index is None:
            self.macro["steps"].append(step)
        else:
            self.macro["steps"][self.current_step_index] = step
        self.refresh_steps_list()
        self.cancel_edit()

    def cancel_edit(self):
        self.current_step_index = None
        self._hide_editor()
        self._clear_edit_form()

    def save(self):
        name = self.name_var.get().strip()
        trigger = self.trigger_var.get().strip()
        if not name:
            messagebox.showerror("错误", "名称不能为空")
            return
        if not trigger:
            messagebox.showerror("错误", "触发键不能为空")
            return

        for i, m in enumerate(mgr.macros):
            if self.macro_index is not None and i == self.macro_index:
                continue
            if m.get("name") == name:
                messagebox.showerror('错误', f'宏名称"{name}"已存在，请使用其他名称')
                return

        self.macro["name"] = name
        self.macro["trigger"] = trigger
        self.macro["repeat"] = self.repeat_var.get()
        if self.macro_index is not None:
            mgr.macros[self.macro_index] = self.macro
        else:
            mgr.macros.append(self.macro)
        self.on_save()
        self.dialog.destroy()


# ---------- 经典模式主窗口 ----------
class ClassicMainWindow:
    def __init__(self):
        self.window = tk.Tk()
        check_admin_gui(self.window)
        self.window.title("按键宏管理器")
        self.window.geometry("850x500")
        self.window.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.window.report_callback_exception = self._on_tk_error

        menubar = tk.Menu(self.window)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="重新加载配置", command=self.reload_config)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit_app)
        menubar.add_cascade(label="文件", menu=file_menu)

        self.search_visible = tk.BooleanVar(value=False)

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="视图", menu=view_menu)
        view_menu.add_command(label="经典", state=tk.DISABLED)
        view_menu.add_command(label="简约", command=self.switch_to_simple)
        view_menu.add_separator()
        view_menu.add_checkbutton(label="搜索框", variable=self.search_visible, command=self.toggle_search)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于", command=self.show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)

        self.window.config(menu=menubar)

        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=0)
        main_frame.rowconfigure(0, weight=1)

        # 左侧宏列表
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self.refresh_list())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(search_frame, text="X", width=2, command=self.clear_search).pack(side=tk.LEFT, padx=(5, 0))
        self.search_frame = search_frame
        self.search_frame.pack_forget()

        style = ttk.Style()
        style.configure("Treeview", font=('TkDefaultFont', 12))
        style.configure("Treeview.Heading", font=('TkDefaultFont', 12, 'bold'))

        columns = ("选择", "名称", "触发键", "步骤数")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("选择", text="选择")
        self.tree.heading("名称", text="名称")
        self.tree.heading("触发键", text="触发键")
        self.tree.heading("步骤数", text="步骤数")
        self.tree.column("选择", width=50, anchor="center")
        self.tree.column("名称", width=240)
        self.tree.column("触发键", width=130)
        self.tree.column("步骤数", width=40, anchor="center")

        self.tree.tag_configure("selected", foreground="green")
        self.tree.tag_configure("disabled", foreground="black")
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-1>", self.on_click)

        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 右侧按钮区域
        right_frame = ttk.Frame(main_frame, width=150)
        right_frame.grid(row=0, column=1, sticky="ns", padx=(0, 5))
        right_frame.pack_propagate(False)

        group1 = ttk.LabelFrame(right_frame, text="宏管理", relief="ridge", borderwidth=2)
        group1.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(group1, text="新增", command=self.new_macro, width=12).pack(pady=2, padx=5, fill=tk.X)
        ttk.Button(group1, text="编辑", command=self.edit_selected, width=12).pack(pady=2, padx=5, fill=tk.X)
        ttk.Button(group1, text="拷贝", command=self.copy_macro, width=12).pack(pady=2, padx=5, fill=tk.X)
        ttk.Button(group1, text="删除", command=self.delete_macro, width=12).pack(pady=2, padx=5, fill=tk.X)

        group2 = ttk.LabelFrame(right_frame, text="状态控制", relief="ridge", borderwidth=2)
        group2.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(group2, text="启用勾选", command=self.apply_selected, width=12).pack(pady=2, padx=5, fill=tk.X)
        ttk.Button(group2, text="停用所有", command=self.disable_all, width=12).pack(pady=2, padx=5, fill=tk.X)
        ttk.Button(group2, text="刷新列表", command=self.refresh_list, width=12).pack(pady=2, padx=5, fill=tk.X)

        group3 = ttk.LabelFrame(right_frame, text="批量选择", relief="ridge", borderwidth=2)
        group3.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(group3, text="全选", command=self.select_all, width=12).pack(pady=2, padx=5, fill=tk.X)
        ttk.Button(group3, text="全不选", command=self.select_none, width=12).pack(pady=2, padx=5, fill=tk.X)
        ttk.Button(group3, text="反选", command=self.invert_selection, width=12).pack(pady=2, padx=5, fill=tk.X)

        mgr.load()
        self.refresh_list()

    # ---------- 辅助方法 ----------
    def _is_name_unique(self, name, exclude_index=None):
        for i, m in enumerate(mgr.macros):
            if i == exclude_index:
                continue
            if m.get("name") == name:
                return False
        return True

    # ---------- 宏列表操作 ----------
    def refresh_list(self):
        filter_text = self.search_var.get().strip().lower()
        for row in self.tree.get_children():
            self.tree.delete(row)
        for idx, m in enumerate(mgr.macros):
            if filter_text and filter_text not in m["name"].lower():
                continue
            check = "☑" if m.get("selected", True) else "☐"
            steps_cnt = len(m.get("steps", []))
            registered = idx in mgr.registered
            tag = "selected" if registered else "disabled"
            self.tree.insert("", tk.END, iid=str(idx), values=(check, m["name"], m["trigger"], steps_cnt), tags=(tag,))

    def save_and_refresh(self):
        mgr.save()
        self.refresh_list()

    def reload_config(self):
        mgr.load()
        self.refresh_list()

    def get_selected_index(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def on_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell" and self.tree.identify_column(event.x) == "#1":
            item = self.tree.identify_row(event.y)
            if item:
                idx = int(item)
                if "selected" in mgr.macros[idx].get("locked", []):
                    return
                mgr.macros[idx]["selected"] = not mgr.macros[idx].get("selected", True)
                self.tree.set(item, column="#1", value="☑" if mgr.macros[idx]["selected"] else "☐")
                mgr.save()

    def on_double_click(self, event):
        idx = self.get_selected_index()
        if idx is not None:
            EditMacroDialog(self.window, idx, self.save_and_refresh)

    def new_macro(self):
        if mgr.registered:
            messagebox.showwarning('操作被禁止', '请先停用所有宏（点击"停用所有"按钮）后再新增宏。')
            return
        base_name = "新宏"
        name = base_name
        suffix = 1
        while not self._is_name_unique(name):
            suffix += 1
            name = f"{base_name}{suffix}"
        macro = {"name": name, "selected": False, "trigger": "", "repeat": 1, "steps": []}
        mgr.macros.append(macro)
        self.refresh_list()
        EditMacroDialog(self.window, len(mgr.macros) - 1, self.save_and_refresh)

    def edit_selected(self):
        if mgr.registered:
            messagebox.showwarning('操作被禁止', '请先停用所有宏（点击"停用所有"按钮）后再编辑宏。')
            return
        idx = self.get_selected_index()
        if idx is None:
            messagebox.showinfo("提示", "请先选择一个宏")
            return
        EditMacroDialog(self.window, idx, self.save_and_refresh)

    def copy_macro(self):
        if mgr.registered:
            messagebox.showwarning('操作被禁止', '请先停用所有宏（点击"停用所有"按钮）后再拷贝宏。')
            return
        idx = self.get_selected_index()
        if idx is None:
            messagebox.showinfo("提示", "请先选择一个宏")
            return
        import copy
        original = mgr.macros[idx]
        base_name = original.get("name", "宏") + " - 副本"
        name = base_name
        suffix = 1
        while not self._is_name_unique(name):
            suffix += 1
            name = f"{base_name}{suffix}"
        new_macro = copy.deepcopy(original)
        new_macro["name"] = name
        new_macro["selected"] = False
        new_macro.pop("locked", None)
        mgr.macros.append(new_macro)
        mgr.save()
        self.refresh_list()
        messagebox.showinfo('提示', f'已复制宏"{original['name']}"为"{name}"')

    def delete_macro(self):
        if mgr.registered:
            messagebox.showwarning('操作被禁止', '请先停用所有宏（点击"停用所有"按钮）后再删除宏。')
            return
        idx = self.get_selected_index()
        if idx is None:
            messagebox.showinfo("提示", "请先选择一个宏")
            return
        if "delete" in mgr.macros[idx].get("locked", []):
            messagebox.showwarning("操作被禁止", f'宏"{mgr.macros[idx]["name"]}"已被锁定，无法删除。')
            return
        if messagebox.askyesno("确认", f"确定要删除宏 [{mgr.macros[idx]['name']}] 吗？"):
            del mgr.macros[idx]
            self.save_and_refresh()
            self.apply_selected()

    def clear_search(self):
        self.search_var.set("")

    def toggle_search(self):
        if self.search_visible.get():
            self.search_frame.pack(fill=tk.X, pady=(0, 5), before=self.tree)
        else:
            self.search_frame.pack_forget()
            self.search_var.set("")

    def _get_visible_indices(self):
        filter_text = self.search_var.get().strip().lower()
        visible = []
        for idx, m in enumerate(mgr.macros):
            if not filter_text or filter_text in m["name"].lower():
                visible.append(idx)
        return visible

    def select_all(self):
        for idx in self._get_visible_indices():
            m = mgr.macros[idx]
            if "selected" not in m.get("locked", []):
                m["selected"] = True
        mgr.save()
        self.refresh_list()

    def select_none(self):
        for idx in self._get_visible_indices():
            m = mgr.macros[idx]
            if "selected" not in m.get("locked", []):
                m["selected"] = False
        mgr.save()
        self.refresh_list()

    def invert_selection(self):
        for idx in self._get_visible_indices():
            m = mgr.macros[idx]
            if "selected" not in m.get("locked", []):
                m["selected"] = not m.get("selected", True)
        mgr.save()
        self.refresh_list()

    def apply_selected(self):
        if mgr.register_all():
            self.refresh_list()
            messagebox.showinfo("提示", "已根据当前勾选状态更新热键")

    def disable_all(self):
        mgr.unregister_all()
        self.refresh_list()
        messagebox.showinfo("提示", "已停用所有宏")

    def show_about(self):
        messagebox.showinfo("关于", ABOUT_TEXT, parent=self.window)

    def switch_to_simple(self):
        mgr.unregister_all()
        self.window.destroy()
        create_main_window("simple")

    def _on_tk_error(self, exc_type, exc_value, exc_tb):
        import traceback
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        log_error(f"UI回调异常:\n{tb_text}")
        messagebox.showerror("错误", f"发生未预期的错误：\n{exc_value}")
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    def quit_app(self):
        mgr.unregister_all()
        self.window.quit()
        sys.exit(0)


# ---------- 简约模式主窗口 ----------
class SimpleMainWindow:
    def __init__(self):
        self.window = tk.Tk()
        check_admin_gui(self.window)
        self.window.title("按键宏管理器")
        self.window.geometry("500x400")
        self.window.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.window.report_callback_exception = self._on_tk_error

        menubar = tk.Menu(self.window)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="重新加载配置", command=self.reload_config)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit_app)
        menubar.add_cascade(label="文件", menu=file_menu)

        self.search_visible = tk.BooleanVar(value=False)

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="视图", menu=view_menu)
        view_menu.add_command(label="经典", command=self.switch_to_classic)
        view_menu.add_command(label="简约", state=tk.DISABLED)
        view_menu.add_separator()
        view_menu.add_checkbutton(label="搜索框", variable=self.search_visible, command=self.toggle_search)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于", command=self.show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)

        self.window.config(menu=menubar)

        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=3, uniform="simple_split")
        main_frame.columnconfigure(1, weight=2, uniform="simple_split")
        main_frame.rowconfigure(0, weight=1)

        # 右侧信息面板（grid + uniform 保持比例固定）
        self.right_frame = ttk.Frame(main_frame)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.right_frame.columnconfigure(0, weight=1)
        self.right_frame.rowconfigure(0, weight=1)

        # 左侧：宏名称列表
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self.refresh_list())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(search_frame, text="X", width=2, command=self.clear_search).pack(side=tk.LEFT, padx=(5, 0))
        self.search_frame = search_frame
        self.search_frame.pack_forget()

        style = ttk.Style()
        style.configure("Treeview", font=('TkDefaultFont', 12))
        self.tree = ttk.Treeview(left_frame, columns=("名称",), show="headings", selectmode="browse")
        self.tree.heading("名称", text="宏名称")
        self.tree.column("名称", width=210, anchor="w", stretch=True)
        self.tree.tag_configure("selected", foreground="green")
        self.tree.tag_configure("disabled", foreground="black")
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.placeholder = ttk.Label(self.right_frame, text="请从左侧选择宏", font=('Microsoft YaHei', 12),
                                     anchor=tk.CENTER)
        self.placeholder.grid(row=0, column=0, sticky="nsew")

        self.info_frame = ttk.LabelFrame(self.right_frame, text="宏信息", padding="8")
        self.info_frame.grid(row=0, column=0, sticky="nsew")
        self.info_frame.grid_remove()

        self.name_label = ttk.Label(self.info_frame, text="名称: ", font=('TkDefaultFont', 10))
        self.name_label.pack(anchor=tk.W, pady=3)
        self.trigger_label = ttk.Label(self.info_frame, text="触发键: ")
        self.trigger_label.pack(anchor=tk.W, pady=3)
        self.repeat_label = ttk.Label(self.info_frame, text="循环次数: ")
        self.repeat_label.pack(anchor=tk.W, pady=3)
        self.steps_label = ttk.Label(self.info_frame, text="步骤数: ")
        self.steps_label.pack(anchor=tk.W, pady=3)

        btn_frame = ttk.Frame(self.info_frame)
        btn_frame.pack(fill=tk.X, pady=8)
        self.enable_btn = ttk.Button(btn_frame, text="启用", command=self.enable_macro, width=8)
        self.enable_btn.pack(side=tk.LEFT, padx=3)
        self.disable_btn = ttk.Button(btn_frame, text="停止", command=self.disable_macro, width=8)
        self.disable_btn.pack(side=tk.LEFT, padx=3)

        mgr.load()
        self.refresh_list()

    @staticmethod
    def _truncate_name(name, max_len=16):
        if len(name) > max_len:
            return name[:max_len - 1] + "…"
        return name

    def refresh_list(self):
        filter_text = self.search_var.get().strip().lower()
        for row in self.tree.get_children():
            self.tree.delete(row)
        for idx, m in enumerate(mgr.macros):
            if filter_text and filter_text not in m["name"].lower():
                continue
            registered = idx in mgr.registered
            tag = "selected" if registered else "disabled"
            display_name = self._truncate_name(m["name"])
            self.tree.insert("", tk.END, iid=str(idx), values=(display_name,), tags=(tag,))

    def clear_search(self):
        self.search_var.set("")

    def toggle_search(self):
        if self.search_visible.get():
            self.search_frame.pack(fill=tk.X, pady=(0, 5), before=self.tree)
        else:
            self.search_frame.pack_forget()
            self.search_var.set("")

    def _update_macro_status(self, idx):
        if not self.tree.exists(str(idx)):
            return
        registered = idx in mgr.registered
        tag = "selected" if registered else "disabled"
        self.tree.item(str(idx), tags=(tag,))

    def reload_config(self):
        mgr.load()
        mgr.unregister_all()
        self.refresh_list()
        self.info_frame.grid_remove()
        self.placeholder.grid()

    def on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            self.info_frame.grid_remove()
            self.placeholder.grid()
            return
        idx = int(sel[0])
        macro = mgr.macros[idx]
        wrap_len = self.info_frame.winfo_width() - 20 if self.info_frame.winfo_width() > 20 else 180
        self.name_label.config(text=f"名称: {macro.get('name', '')}", wraplength=wrap_len)
        self.trigger_label.config(text=f"触发键: {macro.get('trigger', '')}", wraplength=wrap_len)
        self.repeat_label.config(text=f"循环次数: {macro.get('repeat', 1)}", wraplength=wrap_len)
        self.steps_label.config(text=f"步骤数: {len(macro.get('steps', []))}", wraplength=wrap_len)
        registered = idx in mgr.registered
        if registered:
            self.enable_btn.config(state=tk.DISABLED)
            self.disable_btn.config(state=tk.NORMAL)
        else:
            self.enable_btn.config(state=tk.NORMAL)
            self.disable_btn.config(state=tk.DISABLED)
        self.placeholder.grid_remove()
        self.info_frame.grid()

    def enable_macro(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        macro = mgr.macros[idx]
        if "selected" in macro.get("locked", []):
            messagebox.showwarning("操作被禁止", f'宏"{macro["name"]}"已被锁定，无法更改启用状态。')
            return
        trigger = macro.get("trigger")
        if not trigger:
            messagebox.showerror("错误", "该宏未设置触发键，无法启用")
            return

        conflict_idx = None
        if trigger in mgr.hotkeys:
            for i, m in enumerate(mgr.macros):
                if m.get("trigger") == trigger and i in mgr.registered:
                    conflict_idx = i
                    break
            if conflict_idx is not None:
                conflict_name = mgr.macros[conflict_idx].get("name", "未知宏")
                if not messagebox.askyesno('热键冲突',
                                           f'触发键"{trigger}"已被宏"{conflict_name}"占用。\n\n是否覆盖（将停止原宏）？'):
                    return
                mgr.unregister_single(conflict_idx)
                self._update_macro_status(conflict_idx)

        try:
            mgr.register_single(idx)
        except ValueError as e:
            messagebox.showerror('错误', f'触发键"{trigger}"无效：{e}')
            return
        self._update_macro_status(idx)
        self.enable_btn.config(state=tk.DISABLED)
        self.disable_btn.config(state=tk.NORMAL)

    def disable_macro(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        macro = mgr.macros[idx]
        if "selected" in macro.get("locked", []):
            messagebox.showwarning("操作被禁止", f'宏"{macro["name"]}"已被锁定，无法更改启用状态。')
            return
        mgr.unregister_single(idx)
        self._update_macro_status(idx)
        self.enable_btn.config(state=tk.NORMAL)
        self.disable_btn.config(state=tk.DISABLED)

    def switch_to_classic(self):
        mgr.unregister_all()
        self.window.destroy()
        create_main_window("classic")

    def show_about(self):
        messagebox.showinfo("关于", ABOUT_TEXT, parent=self.window)

    def _on_tk_error(self, exc_type, exc_value, exc_tb):
        import traceback
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        log_error(f"UI回调异常:\n{tb_text}")
        messagebox.showerror("错误", f"发生未预期的错误：\n{exc_value}")
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    def quit_app(self):
        mgr.unregister_all()
        self.window.quit()
        sys.exit(0)


# ---------- 窗口创建函数 ----------
def create_main_window(mode):
    if mode == "classic":
        app = ClassicMainWindow()
    else:
        app = SimpleMainWindow()
    app.window.mainloop()


def setup_crash_handler():
    log_dir = "logs"

    def crash_handler(exc_type, exc_value, exc_tb):
        import traceback
        os.makedirs(log_dir, exist_ok=True)
        filename = os.path.join(log_dir, f"crash_{time.strftime('%Y-%m-%d_%H-%M-%S')}.log")
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"崩溃时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"宏数量：{len(mgr.macros)}\n")
            f.write(f"Python 版本：{sys.version}\n")
            f.write(f"平台：{platform.platform()}\n")
            f.write(f"\n{tb_text}")
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = crash_handler


def main():
    setup_crash_handler()
    create_main_window("classic")


if __name__ == "__main__":
    main()
