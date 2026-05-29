# 按键宏管理器

一个 Windows 键盘宏管理工具，支持按键序列、鼠标操作和循环执行，通过热键触发。使用 Python/tkinter 构建，需管理员权限运行以确保在各类应用中正常模拟输入。

## 文件结构

| 文件 | 说明 |
|---|---|
| `macro.py` | 程序入口，创建主窗口并启动事件循环 |
| `constants.py` | 常量定义：按键列表、鼠标动作映射等数据 |
| `utils.py` | 工具函数：热键修饰键解析、日志记录、管理员权限检查 |
| `core.py` | 宏管理核心：加载/保存配置、热键注册/注销、步骤执行引擎、崩溃日志 |
| `edit_dialog.py` | 宏编辑对话框 GUI：新建/修改宏的基本信息与执行步骤 |
| `ui.py` | 主窗口及经典模式、简约模式两个面板的完整 GUI |
| `about_text.py` | 关于对话框的文本内容 |

## 运行

```bash
pip install keyboard mouse
python macro.py
```

建议以管理员身份运行，否则某些应用中可能无法正常模拟按键。

## 宏数据格式

宏以 JSON 格式保存在 `macros.json` 中。每种步骤类型：

- **按键** — `{"type": "key", "value": "ctrl+c", "delay": 0.1}`
- **鼠标** — `{"type": "mouse", "action": "click", "button": "left", "clicks": 1}`
- **等待** — `{"type": "wait", "value": 0.5}`
- **全局停止** — `{"type": "STOPALL"}`（立即停用所有热键）

`locked` 字段可按需锁定名称、触发键、步骤等属性，防止误改。
