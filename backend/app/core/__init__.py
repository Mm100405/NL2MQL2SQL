"""
核心模块

提供应用核心功能，如日志配置、配置管理等。
"""
from .logging_config import setup_logging, get_log_config

__all__ = ['setup_logging', 'get_log_config']
