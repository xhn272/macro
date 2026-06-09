# -*- coding: utf-8 -*-
"""主窗口界面：经典模式与简约模式两个面板的完整 GUI，支持模式切换与宏列表管理。"""

import copy
import sys
import traceback
import tkinter as tk
from tkinter import messagebox, ttk

from about_text import ABOUT_TEXT
from core import mgr
from edit_dialog import EditMacroDialog
from utils import check_admin_gui, log_error


class SearchBar:
    """搜索框组件，封装搜索输入、清除按钮和显示/隐藏逻辑。"""

    def __init__(self, parent, on_change, before_widget):
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(self.frame, text="搜索:").pack(side=tk.LEFT, padx=(0, 5))
        self.var = tk.StringVar()
        self.entry = ttk.Entry(self.frame, textvariable=self.var)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def on_change_preserve_focus(*a):
            on_change()
            self.entry.focus_set()

        self.var.trace("w", on_change_preserve_focus)
        ttk.Button(self.frame, text="X", width=2, command=self.clear).pack(side=tk.LEFT, padx=(5, 0))
        self.before_widget = before_widget
        self.frame.pack_forget()

    def clear(self):
        self.var.set("")

    def show(self):
        self.frame.pack(fill=tk.X, pady=(0, 5), before=self.before_widget)

    def hide(self):
        self.frame.pack_forget()
        self.var.set("")

    def focus(self):
        self.entry.focus_set()


# ---------- 主窗口 ----------
class MainWindow:
    """拥有单一 Tk 实例，管理经典/简约两个面板的切换。"""

    def __init__(self):
        self.window = tk.Tk()
        check_admin_gui(self.window)
        self.window.title("按键宏管理器")
        self.window.geometry("850x500")
        self.window.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.window.report_callback_exception = self._on_tk_error

        mgr.load()

        self._build_menubar()

        self.panel_container = ttk.Frame(self.window)
        self.panel_container.pack(fill=tk.BOTH, expand=True)

        self.classic_panel = ClassicPanel(self.panel_container, self)
        self.simple_panel = SimplePanel(self.panel_container, self)

        self.current_mode = "classic"
        self.classic_panel.show()
        self.classic_panel.refresh_list()
        self._update_view_menu()

        # 热键注销时自动刷新 UI（STOPALL 等在后台线程触发）
        mgr.add_change_callback(lambda: self.window.after_idle(self.current_panel.refresh_list))

    def _build_menubar(self):
        menubar = tk.Menu(self.window)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="重新加载配置", command=self.reload_config)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit_app)
        menubar.add_cascade(label="文件", menu=file_menu)

        self.view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="视图", menu=self.view_menu)
        self.view_menu.add_command(label="经典", command=lambda: self.switch_mode("classic"))
        self.view_menu.add_command(label="简约", command=lambda: self.switch_mode("simple"))
        self.view_menu.add_separator()

        self.search_visible = tk.BooleanVar(value=False)
        self.view_menu.add_checkbutton(label="搜索框", variable=self.search_visible,
                                        command=self.toggle_search)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于", command=self.show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)

        self.window.config(menu=menubar)
        self.window.event_add('<<Find>>', '<Control-f>', '<Control-F>')
        self.window.bind_all('<<Find>>', lambda e: self.show_search())

    def _update_view_menu(self):
        self.view_menu.entryconfig("经典", state=tk.DISABLED if self.current_mode == "classic" else tk.NORMAL)
        self.view_menu.entryconfig("简约", state=tk.DISABLED if self.current_mode == "simple" else tk.NORMAL)

    @property
    def current_panel(self):
        return self.classic_panel if self.current_mode == "classic" else self.simple_panel

    def switch_mode(self, mode):
        if mode == self.current_mode:
            return
        mgr.unregister_all()
        self.search_visible.set(False)

        # 保存经典模式窗口尺寸
        if self.current_mode == "classic":
            self._classic_geometry = self.window.geometry()

        # 隐藏当前面板
        if self.current_mode == "classic":
            self.classic_panel.hide()
        else:
            self.simple_panel.hide()

        # 显示新面板并适配窗口大小
        if mode == "classic":
            self.classic_panel.show()
            self.classic_panel.refresh_list()
            geo = getattr(self, '_classic_geometry', None)
            self.window.geometry(geo if geo else "850x500")
        else:
            self.simple_panel.show()
            self.simple_panel.refresh_list()
            self.window.geometry("500x360")

        self.current_mode = mode
        self._update_view_menu()

    def reload_config(self):
        mgr.load()
        mgr.unregister_all()
        self.search_visible.set(False)
        self.current_panel.refresh_list()

    def toggle_search(self):
        self.current_panel.toggle_search()

    def show_search(self):
        self.search_visible.set(True)
        self.current_panel.toggle_search()
        self.current_panel.search_bar.focus()

    def show_about(self):
        messagebox.showinfo("关于", ABOUT_TEXT, parent=self.window)

    def _on_tk_error(self, exc_type, exc_value, exc_tb):
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        log_error(f"UI回调异常:\n{tb_text}")
        messagebox.showerror("错误", f"发生未预期的错误：\n{exc_value}")
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    def quit_app(self):
        mgr.unregister_all()
        self.window.quit()
        sys.exit(0)


# ---------- 经典模式面板 ----------
class ClassicPanel:
    def __init__(self, parent, main_window):
        self.main_window = main_window
        self.window = main_window.window

        self.container = ttk.Frame(parent)

        main_frame = ttk.Frame(self.container, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=0)
        main_frame.rowconfigure(0, weight=1)

        # 经典模式 - 左侧宏列表
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        style = ttk.Style()
        style.configure("Treeview", font=('TkDefaultFont', 12))
        style.configure("Treeview.Heading", font=('TkDefaultFont', 12, 'bold'))

        # Treeview 必须在 SearchBar 之前创建，因为 SearchBar 需要引用它
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

        self.search_bar = SearchBar(left_frame, self.refresh_list, self.tree)

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

    def show(self):
        self.container.pack(fill=tk.BOTH, expand=True)

    def hide(self):
        self.container.pack_forget()

    def refresh_list(self):
        filter_text = self.search_bar.var.get().strip().lower()
        macros, registered = mgr.get_snapshot()
        existing = set(self.tree.get_children())
        for idx, m in enumerate(macros):
            if filter_text and filter_text not in m["name"].lower():
                continue
            iid = str(idx)
            check = "☑" if m.get("selected", True) else "☐"
            steps_cnt = len(m.get("steps", []))
            tag = "selected" if idx in registered else "disabled"
            values = (check, m["name"], m["trigger"], steps_cnt)
            if iid in existing:
                if self.tree.item(iid, "values") != values or self.tree.item(iid, "tags") != (tag,):
                    self.tree.item(iid, values=values, tags=(tag,))
                existing.discard(iid)
            else:
                self.tree.insert("", tk.END, iid=iid, values=values, tags=(tag,))
        for iid in existing:
            self.tree.delete(iid)

    def save_and_refresh(self):
        mgr.save()
        self.refresh_list()

    def get_selected_index(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def on_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell" and self.tree.identify_column(event.x) == "#1":
            if mgr.is_any_registered():
                return
            item = self.tree.identify_row(event.y)
            if item:
                idx = int(item)
                macro = mgr.get_macro(idx)
                if macro is None:
                    return
                if "selected" in macro.get("locked", []):
                    return
                new_val = mgr.toggle_selected(idx)
                if new_val is not None:
                    self.tree.set(item, column="#1", value="☑" if new_val else "☐")

    def on_double_click(self, event):
        if mgr.is_any_registered():
            return
        idx = self.get_selected_index()
        if idx is not None:
            EditMacroDialog(self.window, idx, self.save_and_refresh)

    def new_macro(self):
        if mgr.is_any_registered():
            messagebox.showwarning('操作被禁止', '请先停用所有宏（点击"停用所有"按钮）后再新增宏。')
            return
        # 不预创建宏，传 None 让对话框以"新建"模式打开，点取消不会残留空宏
        EditMacroDialog(self.window, None, self.save_and_refresh)

    def edit_selected(self):
        if mgr.is_any_registered():
            messagebox.showwarning('操作被禁止', '请先停用所有宏（点击"停用所有"按钮）后再编辑宏。')
            return
        idx = self.get_selected_index()
        if idx is None:
            messagebox.showinfo("提示", "请先选择一个宏")
            return
        EditMacroDialog(self.window, idx, self.save_and_refresh)

    def copy_macro(self):
        if mgr.is_any_registered():
            messagebox.showwarning('操作被禁止', '请先停用所有宏（点击"停用所有"按钮）后再拷贝宏。')
            return
        idx = self.get_selected_index()
        if idx is None:
            messagebox.showinfo("提示", "请先选择一个宏")
            return
        original = mgr.get_macro(idx)
        if original is None:
            return
        base_name = original.get("name", "宏") + " - 副本"
        name = base_name
        suffix = 1
        while not mgr.is_name_unique(name):
            suffix += 1
            name = f"{base_name}{suffix}"
        new_macro = copy.deepcopy(original)
        new_macro["name"] = name
        new_macro["selected"] = False
        new_macro.pop("locked", None)
        mgr.append_macro(new_macro)
        self.refresh_list()
        messagebox.showinfo('提示', f'已复制宏"{original["name"]}"为"{name}"')

    def delete_macro(self):
        if mgr.is_any_registered():
            messagebox.showwarning('操作被禁止', '请先停用所有宏（点击"停用所有"按钮）后再删除宏。')
            return
        idx = self.get_selected_index()
        if idx is None:
            messagebox.showinfo("提示", "请先选择一个宏")
            return
        macro = mgr.get_macro(idx)
        if macro is None:
            return
        if "delete" in macro.get("locked", []):
            messagebox.showwarning("操作被禁止", f'宏"{macro["name"]}"已被锁定，无法删除。')
            return
        if messagebox.askyesno("确认", f"确定要删除宏 [{macro['name']}] 吗？"):
            mgr.remove_macro(idx)
            self.save_and_refresh()

    def toggle_search(self):
        if self.main_window.search_visible.get():
            self.search_bar.show()
        else:
            self.search_bar.hide()

    def _get_visible_indices(self):
        filter_text = self.search_bar.var.get().strip().lower()
        macros, _ = mgr.get_snapshot()
        visible = []
        for idx, m in enumerate(macros):
            if not filter_text or filter_text in m["name"].lower():
                visible.append(idx)
        return visible

    def select_all(self):
        for idx in self._get_visible_indices():
            if not mgr.is_field_locked(idx, "selected"):
                mgr.update_selected(idx, True)
        self.refresh_list()

    def select_none(self):
        for idx in self._get_visible_indices():
            if not mgr.is_field_locked(idx, "selected"):
                mgr.update_selected(idx, False)
        self.refresh_list()

    def invert_selection(self):
        for idx in self._get_visible_indices():
            if not mgr.is_field_locked(idx, "selected"):
                macro = mgr.get_macro(idx)
                if macro is not None:
                    mgr.update_selected(idx, not macro.get("selected", True))
        self.refresh_list()

    def apply_selected(self):
        if mgr.register_all():
            self.refresh_list()
            messagebox.showinfo("提示", "已根据当前勾选状态更新热键")

    def disable_all(self):
        mgr.unregister_all()
        self.refresh_list()
        messagebox.showinfo("提示", "已停用所有宏")


# ---------- 简约模式面板 ----------
class SimplePanel:
    def __init__(self, parent, main_window):
        self.main_window = main_window
        self.window = main_window.window

        self.container = ttk.Frame(parent)

        main_frame = ttk.Frame(self.container, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=3, uniform="simple_split")
        main_frame.columnconfigure(1, weight=2, uniform="simple_split")
        main_frame.rowconfigure(0, weight=1)

        self.right_frame = ttk.Frame(main_frame)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.right_frame.columnconfigure(0, weight=1)
        self.right_frame.rowconfigure(0, weight=1)

        # 简约模式 - 左侧宏名称列表
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        style = ttk.Style()
        style.configure("Treeview", font=('TkDefaultFont', 12))

        # Treeview 必须在 SearchBar 之前创建，因为 SearchBar 需要引用它
        self.tree = ttk.Treeview(left_frame, columns=("名称",), show="headings", selectmode="browse")
        self.tree.heading("名称", text="宏名称")
        self.tree.column("名称", width=210, anchor="w", stretch=True)
        self.tree.tag_configure("selected", foreground="green")
        self.tree.tag_configure("disabled", foreground="black")
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.search_bar = SearchBar(left_frame, self.refresh_list, self.tree)

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

    def show(self):
        self.container.pack(fill=tk.BOTH, expand=True)

    def hide(self):
        self.container.pack_forget()

    @staticmethod
    def _truncate_name(name, max_len=16):
        if len(name) > max_len:
            return name[:max_len - 1] + "…"
        return name

    def refresh_list(self):
        filter_text = self.search_bar.var.get().strip().lower()
        macros, registered = mgr.get_snapshot()
        existing = set(self.tree.get_children())
        for idx, m in enumerate(macros):
            if filter_text and filter_text not in m["name"].lower():
                continue
            iid = str(idx)
            tag = "selected" if idx in registered else "disabled"
            values = (self._truncate_name(m["name"]),)
            if iid in existing:
                if self.tree.item(iid, "values") != values or self.tree.item(iid, "tags") != (tag,):
                    self.tree.item(iid, values=values, tags=(tag,))
                existing.discard(iid)
            else:
                self.tree.insert("", tk.END, iid=iid, values=values, tags=(tag,))
        for iid in existing:
            self.tree.delete(iid)

    def toggle_search(self):
        if self.main_window.search_visible.get():
            self.search_bar.show()
        else:
            self.search_bar.hide()

    def _update_macro_status(self, idx):
        if not self.tree.exists(str(idx)):
            return
        tag = "selected" if mgr.is_index_registered(idx) else "disabled"
        self.tree.item(str(idx), tags=(tag,))

    def on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            self.info_frame.grid_remove()
            self.placeholder.grid()
            return
        idx = int(sel[0])
        macro = mgr.get_macro(idx)
        if macro is None:
            return
        wrap_len = self.info_frame.winfo_width() - 20 if self.info_frame.winfo_width() > 20 else 180
        self.name_label.config(text=f"名称: {macro.get('name', '')}", wraplength=wrap_len)
        self.trigger_label.config(text=f"触发键: {macro.get('trigger', '')}", wraplength=wrap_len)
        self.repeat_label.config(text=f"循环次数: {macro.get('repeat', 1)}", wraplength=wrap_len)
        self.steps_label.config(text=f"步骤数: {len(macro.get('steps', []))}", wraplength=wrap_len)
        if mgr.is_index_registered(idx):
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
        macro = mgr.get_macro(idx)
        if macro is None:
            return
        trigger = macro.get("trigger")
        if not trigger:
            messagebox.showerror("错误", "该宏未设置触发键，无法启用")
            return

        conflict_idx = None
        if mgr.has_hotkey(trigger):
            macros_snap, registered_snap = mgr.get_snapshot()
            for i, m in enumerate(macros_snap):
                if m.get("trigger") == trigger and i in registered_snap:
                    conflict_idx = i
                    break
            if conflict_idx is not None:
                conflict_macro = mgr.get_macro(conflict_idx)
                conflict_name = conflict_macro.get("name", "未知宏") if conflict_macro else "未知宏"
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
        macro = mgr.get_macro(idx)
        if macro is None:
            return
        mgr.unregister_single(idx)
        self._update_macro_status(idx)
        self.enable_btn.config(state=tk.NORMAL)
        self.disable_btn.config(state=tk.DISABLED)
