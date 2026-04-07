"""
日志配置中心

提供统一的日志配置管理，解决 uvicorn 覆盖日志配置的问题。
使用直接操作 root logger 的方式，不依赖 dictConfig。
"""

import os
import sys
import json
import time
import logging
import logging.handlers
from typing import Dict, Any
from datetime import datetime


# 缓存配置，供 monkey-patch 回调使用
_cached_config: Dict[str, Any] = {}
_cached_logging_config: Dict[str, Any] = {}
_cached_third_party_level: int = logging.WARNING
_cached_third_party_overrides: Dict[str, int] = {}


class ThirdPartyLogFilter(logging.Filter):
    """过滤第三方库日志：非 app.* 的 logger 如果级别低于阈值则丢弃"""

    def filter(self, record: logging.LogRecord) -> bool:
        name = record.name
        # app.* 和 uvicorn 不拦截
        if name.startswith('app.') or name.startswith('uvicorn'):
            return True
        # 检查单独覆盖
        # 从最精确匹配到最短前缀
        parts = name.split('.')
        for i in range(len(parts), 0, -1):
            prefix = '.'.join(parts[:i])
            if prefix in _cached_third_party_overrides:
                return record.levelno >= _cached_third_party_overrides[prefix]
        # 兜底：统一第三方级别
        return record.levelno >= _cached_third_party_level


class JSONFormatter(logging.Formatter):
    """JSON 格式化器，用于文件日志"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        if hasattr(record, 'extra') and record.extra:
            log_data.update(record.extra)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class TimedRotatingFileHandlerWithCleanup(logging.handlers.TimedRotatingFileHandler):
    """按日期滚动 + 大小限制 + 自动清理的文件处理器"""

    def __init__(
        self,
        filename: str,
        maxBytes: int = 10 * 1024 * 1024,
        backupCount: int = 20,
        encoding: str = 'utf-8',
        delay: bool = False,
        when: str = 'midnight',
        retention_days: int = 7,
    ):
        super().__init__(filename, when=when, encoding=encoding, delay=delay)
        self.maxBytes = maxBytes
        self.backupCount = backupCount
        self.retention_days = retention_days

    def shouldRollover(self, record: logging.LogRecord) -> bool:
        if super().shouldRollover(record):
            return True
        if self.stream and os.path.isfile(self.baseFilename):
            if os.path.getsize(self.baseFilename) >= self.maxBytes:
                return True
        return False

    def doRollover(self):
        super().doRollover()
        self._cleanup_old_logs()

    def _cleanup_old_logs(self):
        log_dir = os.path.dirname(self.baseFilename)
        base_name = os.path.basename(self.baseFilename).replace('.log', '')

        log_files = []
        try:
            for f in os.listdir(log_dir):
                if f.startswith(base_name):
                    file_path = os.path.join(log_dir, f)
                    log_files.append((file_path, os.path.getmtime(file_path)))
        except Exception:
            return

        log_files.sort(key=lambda x: x[1], reverse=True)

        if len(log_files) > self.backupCount:
            for file_path, _ in log_files[self.backupCount:]:
                try:
                    os.remove(file_path)
                except Exception:
                    pass

        cutoff_time = time.time() - (self.retention_days * 86400)
        for file_path, mtime in log_files:
            if mtime < cutoff_time:
                try:
                    os.remove(file_path)
                except Exception:
                    pass


def get_log_config() -> Dict[str, Any]:
    """从环境变量读取日志配置"""
    # 解析自定义第三方日志配置，格式: "包名:级别,包名:级别"
    # 示例: "litellm:ERROR,httpx:DEBUG,sqlalchemy.engine:WARNING"
    third_party_overrides: Dict[str, str] = {}
    raw = os.getenv('LOG_THIRD_PARTY_OVERRIDES', '')
    if raw:
        for item in raw.split(','):
            item = item.strip()
            if ':' in item:
                pkg, level = item.split(':', 1)
                third_party_overrides[pkg.strip()] = level.strip().upper()

    return {
        'log_level': os.getenv('LOG_LEVEL', 'INFO').upper(),
        'file_enabled': os.getenv('LOG_FILE_ENABLED', 'true').lower() == 'true',
        'file_dir': os.getenv('LOG_FILE_DIR', 'logs'),
        'file_max_size': int(os.getenv('LOG_FILE_MAX_SIZE', '10')) * 1024 * 1024,
        'file_backup_count': int(os.getenv('LOG_FILE_BACKUP_COUNT', '20')),
        'file_retention_days': int(os.getenv('LOG_FILE_RETENTION_DAYS', '7')),
        'third_party_level': os.getenv('LOG_THIRD_PARTY_LEVEL', 'WARNING').upper(),
        'log_format': os.getenv('LOG_FORMAT', 'json').lower(),
        'third_party_overrides': third_party_overrides,
    }


def _apply_logging_config():
    """核心逻辑：直接操作 root logger，确保配置不被覆盖"""
    global _cached_config, _cached_logging_config

    config = get_log_config()
    _cached_config = config

    # 缓存第三方日志配置，供 Filter 使用
    global _cached_third_party_level, _cached_third_party_overrides
    _cached_third_party_level = getattr(logging, config['third_party_level'], logging.WARNING)
    _cached_third_party_overrides = {}
    for pkg, level_str in config.get('third_party_overrides', {}).items():
        level = getattr(logging, level_str, None)
        if level and isinstance(level, int):
            _cached_third_party_overrides[pkg] = level

    # 创建全局 Filter 实例
    third_party_filter = ThirdPartyLogFilter()

    # ---- 直接操作 root logger ----
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # root 设为 DEBUG，由 Filter 控制实际输出
    root.handlers.clear()

    # Console handler
    console_fmt = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_fmt)
    console_handler.addFilter(third_party_filter)
    root.addHandler(console_handler)

    # File handler
    if config['file_enabled']:
        log_dir = os.path.join(os.path.dirname(__file__), '..', '..', config['file_dir'])
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'app.log')
        file_handler = TimedRotatingFileHandlerWithCleanup(
            filename=log_file,
            maxBytes=config['file_max_size'],
            backupCount=config['file_backup_count'],
            retention_days=config['file_retention_days'],
            encoding='utf-8',
        )
        file_handler.setFormatter(JSONFormatter())
        file_handler.addFilter(third_party_filter)
        root.addHandler(file_handler)

    # 已知的第三方库也显式设置级别（双重保险）
    for name in [
        'sqlalchemy.engine', 'sqlalchemy.pool',
        'httpx', 'httpcore', 'aiohttp', 'asyncio', 'multipart',
        'LiteLLM', 'litellm',
    ]:
        logging.getLogger(name).setLevel(_cached_third_party_level)

    # 自定义覆盖（优先级最高）
    for pkg, level in _cached_third_party_overrides.items():
        logging.getLogger(pkg).setLevel(level)

    # 打印启动信息
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("日志系统初始化完成")
    logger.info(f"日志级别: {config['log_level']}")
    logger.info(f"第三方库日志级别: {config['third_party_level']}")
    logger.info(f"文件日志: {'启用' if config['file_enabled'] else '禁用'}")
    if config['file_enabled']:
        logger.info(f"日志目录: {os.path.abspath(log_dir)}")
        logger.info(f"日志格式: {config['log_format']}")
    logger.info("=" * 60)


def setup_logging():
    """
    配置日志系统 + 防止 uvicorn 覆盖

    必须在应用启动前（所有其他导入之前）调用此函数。
    同时 monkey-patch uvicorn 的 configure_logging，确保 uvicorn 启动后不会覆盖。
    """
    _apply_logging_config()

    # Monkey-patch uvicorn，使其启动时重新应用我们的配置
    try:
        import uvicorn.config
        uvicorn.config.Config.configure_logging = lambda self: _apply_logging_config()
    except ImportError:
        pass
