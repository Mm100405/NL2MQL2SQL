#!/usr/bin/env python3
"""
获取本机 IP 地址工具
用于快速获取本机在局域网中的 IP 地址
"""

import socket
import platform
import subprocess


def get_local_ip():
    """获取本机局域网 IP 地址"""
    try:
        # 创建一个 UDP socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 尝试连接到一个外部地址（不会实际发送数据）
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # 备用方案：获取主机名并解析
        hostname = socket.gethostname()
        try:
            ip = socket.gethostbyname(hostname)
            return ip
        except Exception:
            return "无法获取 IP"


def get_system_info():
    """获取系统信息"""
    system = platform.system()
    hostname = socket.gethostname()

    print("=" * 50)
    print("  NL2MQL2SQL - 本机信息查询工具")
    print("=" * 50)
    print(f"系统: {system}")
    print(f"主机名: {hostname}")
    print(f"局域网 IP: {get_local_ip()}")
    print("=" * 50)
    print()
    print("访问地址：")
    print(f"  前端: http://{get_local_ip()}:5173")
    print(f"  后端: http://{get_local_ip()}:8011")
    print(f"  API 文档: http://{get_local_ip()}:8011/docs")
    print()
    print("本地访问：")
    print(f"  前端: http://localhost:5173")
    print(f"  后端: http://localhost:8011")
    print(f"  API 文档: http://localhost:8011/docs")
    print()


if __name__ == '__main__':
    get_system_info()
