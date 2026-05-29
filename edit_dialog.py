# -*- coding: utf-8 -*-
"""宏编辑对话框：新建或修改宏的名称、触发键、执行步骤等信息。"""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

import keyboard
import mouse

from constants import ALL_KEYS, MOUSE_ACTIONS, MOUSE_CLICK_MAP, MOUSE_CLICK_REVERSE
from utils import _parse_modifiers, _build_modifier_key, log_error
from core import mgr


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
        _parse_modifiers(self.trigger_var.get(), self.ctrl_var, self.alt_var, self.shift_var, self.win_var)

    def _record_hotkey(self):
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
        new = _build_modifier_key(current, self.ctrl_var, self.alt_var, self.shift_var, self.win_var)
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

        scrollable.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(scrollable, text="步骤类型：").grid(row=row, column=0, sticky=tk.W, padx=(10, 0), pady=8)
        self.edit_type_var = tk.StringVar(value="按键")
        type_combo = ttk.Combobox(scrollable, textvariable=self.edit_type_var,
                                  values=["按键", "等待", "鼠标"], state="readonly", width=10)
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
                self.edit_mouse_action.set(MOUSE_CLICK_REVERSE.get((btn, clicks), "左键单击"))
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
            self.delay_frame.grid()
        elif typ == "mouse":
            self.edit_mouse_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.edit_hint.config(text="选择鼠标动作并设置参数")
            self.delay_frame.grid()
        else:  # wait
            self.edit_wait_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.edit_hint.config(text="等待秒数，如 0.5")
            self.delay_frame.grid_remove()

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
        _parse_modifiers(key_str, self.edit_ctrl, self.edit_alt, self.edit_shift, self.edit_win)

    def update_edit_key(self):
        if self.edit_type_var.get() != "按键":
            return
        cur = self.edit_key_combo.get().strip()
        new = _build_modifier_key(cur, self.edit_ctrl, self.edit_alt, self.edit_shift, self.edit_win)
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
            if act in MOUSE_CLICK_MAP:
                btn, clicks = MOUSE_CLICK_MAP[act]
                step = {"type": "mouse", "action": "click", "button": btn, "clicks": clicks, "delay": delay}
            elif act == "移动到":
                try:
                    x = int(self.edit_mouse_x_entry.get())
                    y = int(self.edit_mouse_y_entry.get())
                except ValueError:
                    messagebox.showerror("错误", "坐标必须为整数")
                    return
                step = {"type": "mouse", "action": "move", "x": x, "y": y, "delay": delay}
            elif act in ("滚动向上", "滚动向下"):
                try:
                    rows = int(self.edit_mouse_scroll_entry.get())
                except ValueError:
                    messagebox.showerror("错误", "行数必须为整数")
                    return
                step = {"type": "mouse", "action": "scroll", "dy": rows if act == "滚动向上" else -rows, "delay": delay}
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

        if not mgr.is_name_unique(name, self.macro_index):
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
