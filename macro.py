# -*- coding: utf-8 -*-
"""
按键宏管理器 - 单窗口多面板版本
经典模式和简约模式为同一窗口内的两个面板，通过视图菜单切换
"""

from core import setup_crash_handler
from ui import MainWindow


def main():
    setup_crash_handler()
    app = MainWindow()
    app.window.mainloop()


if __name__ == "__main__":
    main()
