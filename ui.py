# -*- coding: utf-8 -*-
"""主窗口界面：经典模式与简约模式两个面板的完整 GUI，支持模式切换与宏列表管理。"""

import copy
import os
import sys
import traceback
import tkinter as tk
from tkinter import messagebox, ttk

from about_text import ABOUT_TEXT
from config import config as app_config
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


def _refresh_treeview(tree, search_bar, make_values):
    """Treeview 增量刷新：遍历宏列表，按需增删改条目。

    make_values(idx, macro, registered) -> tuple — 生成 values 元组。
    """
    filter_text = search_bar.var.get().strip().lower()
    macros, registered = mgr.get_snapshot()
    existing = set(tree.get_children())
    for idx, m in enumerate(macros):
        if filter_text and filter_text not in m["name"].lower():
            continue
        iid = str(idx)
        tag = "selected" if idx in registered else "disabled"
        values = make_values(idx, m, registered)
        if iid in existing:
            if tree.item(iid, "values") != values or tree.item(iid, "tags") != (tag,):
                tree.item(iid, values=values, tags=(tag,))
            existing.discard(iid)
        else:
            tree.insert("", tk.END, iid=iid, values=values, tags=(tag,))
    for iid in existing:
        tree.delete(iid)


# ---------- 设置对话框 ----------
class SettingsDialog:
    """独立的设置窗口，允许用户修改可配置项并持久化到 config.json。"""

    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("设置")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        main = ttk.Frame(self.dialog, padding="10")
        main.pack(fill=tk.BOTH, expand=True)

        self.check_update_var = tk.BooleanVar(value=app_config.get("check_update"))
        ttk.Checkbutton(main, text="启动时检查更新", variable=self.check_update_var).pack(
            anchor=tk.W, pady=5)

        log_frame = ttk.Frame(main)
        log_frame.pack(fill=tk.X, pady=5)
        ttk.Label(log_frame, text="日志保留数量：").pack(side=tk.LEFT)
        self.log_keep_var = tk.IntVar(value=app_config.get("log_keep"))
        ttk.Spinbox(log_frame, from_=1, to=999, textvariable=self.log_keep_var,
                    width=6).pack(side=tk.LEFT, padx=5)
        ttk.Label(log_frame, text="个").pack(side=tk.LEFT)

        log_btn_frame = ttk.Frame(main)
        log_btn_frame.pack(fill=tk.X, pady=(2, 0))
        ttk.Button(log_btn_frame, text="打开日志目录", command=self.open_log_dir).pack(
            side=tk.LEFT, padx=(0, 5))
        ttk.Button(log_btn_frame, text="清理所有日志", command=self.clear_logs).pack(
            side=tk.LEFT)

        backup_frame = ttk.Frame(main)
        backup_frame.pack(fill=tk.X, pady=5)
        ttk.Label(backup_frame, text="备份保留数量：").pack(side=tk.LEFT)
        self.backup_keep_var = tk.IntVar(value=app_config.get("backup_keep"))
        ttk.Spinbox(backup_frame, from_=1, to=99, textvariable=self.backup_keep_var,
                    width=6).pack(side=tk.LEFT, padx=5)
        ttk.Label(backup_frame, text="份").pack(side=tk.LEFT)
        ttk.Button(backup_frame, text="立即备份", command=self.manual_backup).pack(
            side=tk.RIGHT, padx=(5, 0))

        note = ttk.Label(main, text="注：宏配置文件路径需直接编辑 config.json 修改。",
                         foreground="gray")
        note.pack(anchor=tk.W, pady=(10, 0))

        btn_frame = ttk.Frame(main)
        btn_frame.pack(pady=(15, 0))
        ttk.Button(btn_frame, text="保存", command=self.save, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.dialog.destroy,
                   width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="恢复默认", command=self.restore_defaults,
                   width=10).pack(side=tk.LEFT, padx=5)

        self.dialog.bind("<Return>", lambda e: self.save())
        self.dialog.bind("<Escape>", lambda e: self.dialog.destroy())

    def save(self):
        app_config.set("check_update", self.check_update_var.get())
        app_config.set("log_keep", self.log_keep_var.get())
        app_config.set("backup_keep", self.backup_keep_var.get())
        app_config.save()
        self.dialog.destroy()

    def open_log_dir(self):
        log_dir = os.path.abspath("logs")
        if os.path.isdir(log_dir):
            os.startfile(log_dir)
        else:
            messagebox.showinfo("提示", "日志目录尚不存在。", parent=self.dialog)

    def clear_logs(self):
        log_dir = os.path.abspath("logs")
        if not os.path.isdir(log_dir):
            messagebox.showinfo("提示", "没有日志需要清理。", parent=self.dialog)
            return
        files = [f for f in os.listdir(log_dir) if f.endswith(".log")]
        if not files:
            messagebox.showinfo("提示", "没有日志需要清理。", parent=self.dialog)
            return
        if not messagebox.askyesno("确认", f"确定要删除所有 {len(files)} 个日志文件吗？",
                                   parent=self.dialog):
            return
        for f in files:
            os.remove(os.path.join(log_dir, f))
        messagebox.showinfo("提示", f"已清理 {len(files)} 个日志文件。", parent=self.dialog)

    def manual_backup(self):
        from core import mgr
        mgr.force_backup()
        messagebox.showinfo("提示", "备份完成。", parent=self.dialog)

    def restore_defaults(self):
        from config import DEFAULTS
        self.check_update_var.set(DEFAULTS["check_update"])
        self.log_keep_var.set(DEFAULTS["log_keep"])
        self.backup_keep_var.set(DEFAULTS["backup_keep"])


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
        file_menu.add_command(label="设置", command=self.show_settings)
        file_menu.add_command(label="重新加载配置", command=self.reload_config)
        file_menu.add_command(label="恢复配置...", command=self.restore_config)
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

        self.view_menu.add_separator()
        themes_menu = tk.Menu(self.view_menu, tearoff=0)
        self.view_menu.add_cascade(label="主题", menu=themes_menu)
        self.theme_var = tk.StringVar(value=app_config.get("theme"))
        THEMES = [
            ("默认", "default"),
            ("darkly（暗色）", "darkly"),
            ("cyborg（暗色）", "cyborg"),
        ]
        for label, name in THEMES:
            themes_menu.add_radiobutton(
                label=label, variable=self.theme_var, value=name,
                command=lambda n=name: self.switch_theme(n))

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
        macros, _ = mgr.get_snapshot()
        info = ABOUT_TEXT + f"""

运行信息：
• 配置文件：{os.path.abspath(app_config.get('macros_file'))}
• 日志目录：{os.path.abspath('logs')}
• 宏数量：{len(macros)}
• Python {sys.version}"""
        messagebox.showinfo("关于", info, parent=self.window)

    def show_settings(self):
        SettingsDialog(self.window)

    def switch_theme(self, theme):
        if theme == "default":
            ttk.Style().theme_use("vista")
        else:
            try:
                import ttkbootstrap as tb
                tb.Style(theme=theme)
            except ImportError:
                messagebox.showwarning("提示", "未安装 ttkbootstrap 库，无法切换主题。",
                                       parent=self.window)
                self.theme_var.set("default")
                return
        app_config.set("theme", theme)
        app_config.save()

    def restore_config(self):
        if mgr.is_any_registered():
            messagebox.showwarning("操作被禁止", "请先停用所有宏后再恢复配置。")
            return
        file_path = tk.filedialog.askopenfilename(
            title="选择备份文件",
            initialdir=os.path.abspath("backups"),
            filetypes=[("JSON 备份文件", "*.json.bak"), ("JSON 文件", "*.json"),
                       ("所有文件", "*.*")],
        )
        if not file_path:
            return
        if not messagebox.askyesno("确认", "确定要恢复配置吗？\n\n当前所有宏将被替换为备份文件中的内容。",
                                   parent=self.window):
            return
        try:
            mgr.restore_from_file(file_path)
            messagebox.showinfo("提示", "配置恢复成功。", parent=self.window)
            self.current_panel.refresh_list()
        except ValueError as e:
            messagebox.showerror("错误", str(e), parent=self.window)

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
        def make_values(idx, m, registered):
            check = "☑" if m.get("selected", True) else "☐"
            return check, m["name"], m["trigger"], len(m.get("steps", []))
        _refresh_treeview(self.tree, self.search_bar, make_values)

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

        self.info_frame = ttk.LabelFrame(self.right_frame, text="宏信息")
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
        def make_values(idx, m, registered):
            return (self._truncate_name(m["name"]),)
        _refresh_treeview(self.tree, self.search_bar, make_values)

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
