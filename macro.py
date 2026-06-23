# -*- coding: utf-8 -*-
"""
按键宏管理器 - 单窗口多面板版本
经典模式和简约模式为同一窗口内的两个面板，通过视图菜单切换
"""

import threading

from config import config as app_config
from core import setup_crash_handler
from ui import MainWindow
from update_checker import check_for_updates


def main():
    setup_crash_handler()
    # 非默认主题时才加载 ttkbootstrap，保持原生外观作为默认
    theme = app_config.get("theme")
    if theme and theme != "default":
        try:
            import ttkbootstrap as tb
            tb.Style(theme=theme)
        except ImportError:
            pass
    app = MainWindow()
    # 启动后 1.5 秒在后台线程检查更新，不阻塞 UI
    if app_config.get("check_update"):
        app.window.after(1500, lambda: threading.Thread(
            target=check_for_updates, args=(app.window,), daemon=True
        ).start())
    app.window.mainloop()


if __name__ == "__main__":
    main()
