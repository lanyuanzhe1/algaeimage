---
name: conda-bash-path-fix
description: Git Bash 无法 conda activate 的根因与修复
metadata:
  type: reference
---

## 问题

在 Git Bash（MSYS2）中执行 `conda activate ican` 报 `conda: command not found`。

## 根因

Git Bash 使用独立的 Unix-style PATH，不继承 Windows 系统 `%PATH%`。本机的 conda 安装在 `A:\Anaconda_envs\`，但该路径未出现在 bash PATH 中。

`$CONDA_EXE` 当前指向 `/opt/homebrew/bin/conda`（macOS Homebrew 路径），可能是从 Mac 同步过来的 dotfile 残留，在 Windows 上无效。

## 绕过方式

直接用 conda 环境的 Python 解释器完整路径：
```bash
"A:/Anaconda_envs/envs/ican/python.exe" -m uvicorn ...
"A:/Anaconda_envs/envs/ican/python.exe" camera_grabber.py --fps 5
```

## 永久修复（待执行）

在 `~/.bashrc` 中添加：
```bash
export PATH="A:/Anaconda_envs:A:/Anaconda_envs/Scripts:$PATH"
```

然后 `source ~/.bashrc`，之后 `conda activate ican` 即可正常使用。

## 相关

- [[project_context]] — conda 环境路径 `A:\Anaconda_envs\envs\ican`
- [[demo-workflow-architecture]] — 样机启动流程用到 conda Python
