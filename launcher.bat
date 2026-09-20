@echo off
chcp 936 > nul  # 解决中文乱码（可选，根据需要保留）
title 漫画切割器启动器
color 0A

REM 检查是否存在虚拟环境
if not exist myenv (
    echo 创建虚拟环境...
    python -m venv myenv
    if errorlevel 1 (
        echo 创建虚拟环境失败！请确保已安装 Python。
        goto :end
    )
    echo 虚拟环境创建成功。
) else (
    echo 找到现有虚拟环境。
)

REM 激活虚拟环境
echo 激活虚拟环境...
call myenv\Scripts\activate

REM 检查是否需要安装依赖
if exist requirements.txt (
    echo 安装项目依赖...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo 安装依赖失败！请检查网络连接或 requirements.txt 文件。
        goto :end
    )
    echo 依赖安装完成。
) else (
    echo 未找到 requirements.txt 文件，跳过依赖安装。
)

REM 运行主程序（主程序关闭后，批处理会自动退出）
echo 启动漫画切割器...
python src/main.py

:end
REM 移除 pause 命令，主程序结束后批处理直接关闭