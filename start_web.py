#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Web 渲染器启动脚本
"""

import sys
import webbrowser
import time
import threading
from pathlib import Path

def check_dependencies():
    """检查依赖"""
    missing = []
    
    try:
        import flask
        print(f"✓ Flask {flask.__version__}")
    except ImportError:
        missing.append("flask")
    
    try:
        import flask_socketio
        print(f"✓ Flask-SocketIO 已安装")
    except ImportError:
        missing.append("flask-socketio")
    
    try:
        from PIL import Image
        import PIL
        print(f"✓ Pillow {PIL.__version__}")
    except ImportError:
        missing.append("pillow")
    
    if missing:
        print(f"\n缺少依赖: {', '.join(missing)}")
        print("请运行: pip install " + " ".join(missing))
        return False
    
    return True

def setup_directories():
    """创建必要的目录"""
    dirs = ['objects', 'brdfs', 'renders', 'templates', 'static']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"✓ 目录 {dir_name}")

def open_browser():
    """延迟打开浏览器"""
    time.sleep(2)
    webbrowser.open('http://localhost:8080')

def main():
    print("=== 光度立体渲染器 Web 版本 ===\n")
    
    # 检查依赖
    print("检查依赖...")
    if not check_dependencies():
        return
    
    # 设置目录
    print("\n设置目录...")
    setup_directories()
    
    # 启动浏览器（延迟）
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # 启动 Web 应用
    print("\n启动 Web 服务器...")
    print("服务器地址: http://localhost:8080")
    print("按 Ctrl+C 停止服务器\n")
    
    try:
        import web_render
        web_render.main()
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动失败: {e}")

if __name__ == "__main__":
    main()