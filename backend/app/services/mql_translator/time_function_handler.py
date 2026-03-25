"""
time_function_handler.py - 时间函数处理模块

利用 ibis + sqlglot 实现多数据源时间函数自动适配：

MQL 时间函数 → ibis 表达式 → sqlglot AST → 目标方言 SQL

支持的时间函数：
- TODAY() - 今天
- YESTERDAY() - 昨天
- TOMORROW() - 明天
- LAST_N_DAYS(n) - 最近 N 天
- LAST_N_MONTHS(n) - 最近 N 月
- LAST_N_YEARS(n) - 最近 N 年
- NEXT_N_DAYS(n) - 未来 N 天
- NEXT_N_MONTHS(n) - 未来 N 月
- THIS_WEEK() - 本周
- THIS_MONTH() - 本月
- THIS_QUARTER() - 本季
- THIS_YEAR() - 本年
- ADD_MONTHS(date, n) - 日期加减 N 月
"""

import re
import logging
from typing import Any, Optional, List, Union

import ibis
import ibis.expr.types as ir
import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)


# MQL 时间函数定义
MQL_TIME_FUNCTIONS = {
    "TODAY": {"args": [], "desc": "今天", "example": "TODAY()"},
    "YESTERDAY": {"args": [], "desc": "昨天", "example": "YESTERDAY()"},
    "TOMORROW": {"args": [], "desc": "明天", "example": "TOMORROW()"},
    "LAST_N_DAYS": {"args": ["n"], "desc": "最近 N 天", "example": "LAST_N_DAYS(30)"},
    "LAST_N_MONTHS": {"args": ["n"], "desc": "最近 N 月", "example": "LAST_N_MONTHS(3)"},
    "LAST_N_YEARS": {"args": ["n"], "desc": "最近 N 年", "example": "LAST_N_YEARS(1)"},
    "NEXT_N_DAYS": {"args": ["n"], "desc": "未来 N 天", "example": "NEXT_N_DAYS(7)"},
    "NEXT_N_MONTHS": {"args": ["n"], "desc": "未来 N 月", "example": "NEXT_N_MONTHS(3)"},
    "THIS_WEEK": {"args": [], "desc": "本周开始", "example": "THIS_WEEK()"},
    "THIS_MONTH": {"args": [], "desc": "本月开始", "example": "THIS_MONTH()"},
    "THIS_QUARTER": {"args": [], "desc": "本季开始", "example": "THIS_QUARTER()"},
    "THIS_YEAR": {"args": [], "desc": "本年开始", "example": "THIS_YEAR()"},
    "ADD_MONTHS": {"args": ["date", "n"], "desc": "日期加减 N 月", "example": "ADD_MONTHS([日期], -1)"},
}


class TimeFunctionHandler:
    """
    时间函数处理器
    
    使用 ibis 构建时间表达式，然后转换为目标方言 SQL。
    
    使用方式:
        handler = TimeFunctionHandler(dialect="mysql")
        sql = handler.parse_and_render("LAST_N_DAYS(30)")
        # 结果: "CURRENT_DATE - INTERVAL 30 DAY" (MySQL)
        
        handler = TimeFunctionHandler(dialect="clickhouse")
        sql = handler.parse_and_render("LAST_N_DAYS(30)")
        # 结果: "today() - 30" (ClickHouse)
    """
    
    # ibis 方言映射
    IBIS_DIALECT_MAP = {
        "mysql": "mysql",
        "postgresql": "postgres",
        "postgres": "postgres",
        "clickhouse": "clickhouse",
        "duckdb": "duckdb",
        "sqlite": "sqlite",
        "bigquery": "bigquery",
        "snowflake": "snowflake",
        "mssql": "mssql",
    }
    
    def __init__(self, dialect: str = "mysql"):
        """
        Args:
            dialect: 目标 SQL 方言 (mysql, postgresql, clickhouse, duckdb, etc.)
        """
        self.dialect = dialect.lower()
        self._ibis_dialect = self.IBIS_DIALECT_MAP.get(self.dialect, self.dialect)
    
    def is_mql_time_function(self, value: str) -> bool:
        """检查字符串是否为 MQL 时间函数"""
        if not isinstance(value, str):
            return False
        pattern = r'^(' + '|'.join(MQL_TIME_FUNCTIONS.keys()) + r')\s*\('
        return bool(re.match(pattern, value.strip(), re.IGNORECASE))
    
    def parse_and_render(self, func_str: str) -> str:
        """
        解析 MQL 时间函数字符串并转换为目标方言 SQL
        
        Args:
            func_str: MQL 时间函数字符串，如 "TODAY()", "LAST_N_DAYS(30)"
        
        Returns:
            SQL 字符串（目标方言）
        
        Examples:
            >>> handler = TimeFunctionHandler("mysql")
            >>> handler.parse_and_render("TODAY()")
            'CURRENT_DATE'
            >>> handler.parse_and_render("LAST_N_DAYS(30)")
            'CURRENT_DATE - INTERVAL 30 DAY'
            
            >>> handler = TimeFunctionHandler("clickhouse")
            >>> handler.parse_and_render("TODAY()")
            'today()'
            >>> handler.parse_and_render("LAST_N_DAYS(30)")
            'today() - 30'
        """
        try:
            # 解析函数名和参数
            func_name, args = self._parse_function(func_str)
            
            # 构建 ibis 表达式
            ibis_expr = self._build_ibis_expr(func_name, args)
            
            # 转换为 SQL
            return self._ibis_to_sql(ibis_expr)
        except Exception as e:
            logger.warning(f"Failed to parse time function '{func_str}': {e}")
            return func_str  # 返回原值作为 fallback
    
    def _parse_function(self, func_str: str) -> tuple:
        """解析函数名和参数"""
        func_str = func_str.strip()
        
        # 匹配函数名和参数
        match = re.match(r'^(\w+)\s*\(\s*(.*?)\s*\)$', func_str, re.DOTALL)
        if not match:
            raise ValueError(f"Invalid function format: {func_str}")
        
        func_name = match.group(1).upper()
        args_str = match.group(2).strip()
        
        # 解析参数
        args = self._parse_args(args_str) if args_str else []
        
        return func_name, args
    
    def _parse_args(self, args_str: str) -> List[str]:
        """解析参数列表，处理嵌套函数和字符串"""
        args = []
        current = ""
        depth = 0
        in_string = False
        string_char = None
        
        for char in args_str:
            if char in ('"', "'") and not in_string:
                in_string = True
                string_char = char
                current += char
            elif char == string_char and in_string:
                in_string = False
                string_char = None
                current += char
            elif char == '(' and not in_string:
                depth += 1
                current += char
            elif char == ')' and not in_string:
                depth -= 1
                current += char
            elif char == ',' and depth == 0 and not in_string:
                args.append(current.strip())
                current = ""
            else:
                current += char
        
        if current.strip():
            args.append(current.strip())
        
        return args
    
    def _build_ibis_expr(self, func_name: str, args: List[str]) -> ir.Expr:
        """根据函数名和参数构建 ibis 表达式
        
        注意：ibis 12.0.0+ API 变化：
        - ibis.current_date() -> ibis.now().date()
        - ibis.date_trunc() -> ibis.timestamp_trunc() 或其他
        """
        
        # 获取当前日期（兼容 ibis 12.0.0+）
        try:
            # ibis 12.0.0+
            current_date = ibis.now().date()
        except AttributeError:
            # 旧版本
            current_date = ibis.current_date()
        
        if func_name == "TODAY":
            return current_date
        
        elif func_name == "YESTERDAY":
            return current_date - ibis.interval(days=1)
        
        elif func_name == "TOMORROW":
            return current_date + ibis.interval(days=1)
        
        elif func_name == "LAST_N_DAYS":
            n = int(args[0]) if args else 30
            return current_date - ibis.interval(days=n)
        
        elif func_name == "LAST_N_MONTHS":
            n = int(args[0]) if args else 1
            return current_date - ibis.interval(months=n)
        
        elif func_name == "LAST_N_YEARS":
            n = int(args[0]) if args else 1
            return current_date - ibis.interval(years=n)
        
        elif func_name == "NEXT_N_DAYS":
            n = int(args[0]) if args else 1
            return current_date + ibis.interval(days=n)
        
        elif func_name == "NEXT_N_MONTHS":
            n = int(args[0]) if args else 1
            return current_date + ibis.interval(months=n)
        
        elif func_name == "THIS_WEEK":
            # MySQL: DATE_SUB(CURRENT_DATE, INTERVAL WEEKDAY(CURRENT_DATE) DAY)
            return "THIS_WEEK_PLACEHOLDER"
        
        elif func_name == "THIS_MONTH":
            # MySQL: DATE_FORMAT(CURRENT_DATE, '%Y-%m-01')
            return "THIS_MONTH_PLACEHOLDER"
        
        elif func_name == "THIS_QUARTER":
            # MySQL: DATE_FORMAT(CURRENT_DATE, '%Y-%m-01') (简化)
            return "THIS_QUARTER_PLACEHOLDER"
        
        elif func_name == "THIS_YEAR":
            # MySQL: DATE_FORMAT(CURRENT_DATE, '%Y-01-01')
            return "THIS_YEAR_PLACEHOLDER"
        
        elif func_name == "ADD_MONTHS":
            # args: [date_expr, n]
            date_expr = args[0] if len(args) > 0 else "CURRENT_DATE"
            n = int(args[1]) if len(args) > 1 else 0
            
            # 如果 date_expr 是 MQL 字段引用，需要特殊处理
            if date_expr.startswith('[') and date_expr.endswith(']'):
                # 字段引用，直接传递（后续在 expression_parser 中处理）
                return f"ADD_MONTHS_PLACEHOLDER({date_expr}, {n})"
            
            # 尝试解析为日期
            try:
                if self.is_mql_time_function(date_expr):
                    inner_expr = self._build_ibis_expr(*self._parse_function(date_expr))
                    return inner_expr + ibis.interval(months=n)
                else:
                    # 假设是日期字符串或 CURRENT_DATE
                    return current_date + ibis.interval(months=n)
            except:
                return current_date + ibis.interval(months=n)
        
        else:
            raise ValueError(f"Unknown MQL time function: {func_name}")
    
    def _ibis_to_sql(self, ibis_expr: Union[ir.Expr, str]) -> str:
        """将 ibis 表达式转换为目标方言 SQL"""
        
        # 处理占位符字符串
        if isinstance(ibis_expr, str):
            # 使用对应方言的渲染方法处理占位符
            if self._ibis_dialect == "mysql":
                return self._render_mysql(ibis_expr)
            elif self._ibis_dialect in ("postgres", "postgresql"):
                return self._render_postgres(ibis_expr)
            elif self._ibis_dialect == "clickhouse":
                return self._render_clickhouse(ibis_expr)
            elif self._ibis_dialect == "duckdb":
                return self._render_duckdb(ibis_expr)
            return ibis_expr
        
        try:
            # 方法1：使用 ibis 内置编译
            # 创建一个内存表来编译表达式
            if self._ibis_dialect == "clickhouse":
                # ClickHouse 特殊处理
                return self._render_clickhouse(ibis_expr)
            elif self._ibis_dialect == "mysql":
                return self._render_mysql(ibis_expr)
            elif self._ibis_dialect in ("postgres", "postgresql"):
                return self._render_postgres(ibis_expr)
            elif self._ibis_dialect == "duckdb":
                return self._render_duckdb(ibis_expr)
            else:
                # 通用渲染
                return str(ibis_expr)
        except Exception as e:
            logger.warning(f"Failed to compile ibis expression: {e}")
            return str(ibis_expr)
    
    def _render_mysql(self, expr: Union[ir.Expr, str]) -> str:
        """渲染为 MySQL 方言"""
        expr_str = str(expr)
        
        # 处理占位符
        if expr_str == "THIS_WEEK_PLACEHOLDER":
            return "DATE_SUB(CURRENT_DATE, INTERVAL WEEKDAY(CURRENT_DATE) DAY)"
        if expr_str == "THIS_MONTH_PLACEHOLDER":
            return "DATE_FORMAT(CURRENT_DATE, '%Y-%m-01')"
        if expr_str == "THIS_QUARTER_PLACEHOLDER":
            return "DATE_FORMAT(CURRENT_DATE, '%Y-%m-01')"
        if expr_str == "THIS_YEAR_PLACEHOLDER":
            return "DATE_FORMAT(CURRENT_DATE, '%Y-01-01')"
        
        # ibis 12.0.0 格式处理
        # DateSub(Date(TimestampNow()), 30D): Date(TimestampNow()) - 30 D -> CURRENT_DATE - INTERVAL 30 DAY
        date_sub_match = re.search(r'DateSub\(Date\(TimestampNow\(\)\),\s*(\d+)([DYM])\)', expr_str)
        if date_sub_match:
            n = date_sub_match.group(1)
            unit = date_sub_match.group(2)
            unit_map = {'D': 'DAY', 'M': 'MONTH', 'Y': 'YEAR'}
            return f"CURRENT_DATE - INTERVAL {n} {unit_map.get(unit, 'DAY')}"
        
        # DateAdd(Date(TimestampNow()), 30D): Date(TimestampNow()) + 30 D -> CURRENT_DATE + INTERVAL 30 DAY
        date_add_match = re.search(r'DateAdd\(Date\(TimestampNow\(\)\),\s*(\d+)([DYM])\)', expr_str)
        if date_add_match:
            n = date_add_match.group(1)
            unit = date_add_match.group(2)
            unit_map = {'D': 'DAY', 'M': 'MONTH', 'Y': 'YEAR'}
            return f"CURRENT_DATE + INTERVAL {n} {unit_map.get(unit, 'DAY')}"
        
        # Date(TimestampNow()) -> CURRENT_DATE
        expr_str = re.sub(r'Date\(TimestampNow\(\)\)', 'CURRENT_DATE', expr_str)
        
        # TimestampTrunc(TimestampNow(), 'month') -> DATE_FORMAT(CURRENT_DATE, '%Y-%m-01')
        trunc_match = re.search(r"TimestampTrunc\(TimestampNow\(\),\s*'(\w+)'\)", expr_str)
        if trunc_match:
            unit = trunc_match.group(1)
            format_map = {
                'day': "CURRENT_DATE",
                'week': "DATE_SUB(CURRENT_DATE, INTERVAL WEEKDAY(CURRENT_DATE) DAY)",
                'month': "DATE_FORMAT(CURRENT_DATE, '%Y-%m-01')",
                'quarter': "DATE_FORMAT(CURRENT_DATE, '%Y-%m-01')",
                'year': "DATE_FORMAT(CURRENT_DATE, '%Y-01-01')",
            }
            return format_map.get(unit, 'CURRENT_DATE')
        
        # 旧版 ibis 格式转换
        expr_str = expr_str.replace("current_date()", "CURRENT_DATE")
        expr_str = expr_str.replace("current_timestamp()", "CURRENT_TIMESTAMP")
        
        # 处理 interval 格式: INTERVAL '30' DAY -> INTERVAL 30 DAY (MySQL 不需要引号)
        # 匹配各种引号格式
        expr_str = re.sub(r"INTERVAL\s*'(\d+)'\s*(\w+)", r"INTERVAL \1 \2", expr_str)
        expr_str = re.sub(r'INTERVAL\s*"(\d+)"\s*(\w+)', r"INTERVAL \1 \2", expr_str)
        
        # 处理 date_trunc -> DATE_FORMAT
        if "date_trunc" in expr_str.lower():
            expr_str = self._convert_date_trunc_to_mysql(expr_str)
        
        return expr_str
    
    def _render_postgres(self, expr: ir.Expr) -> str:
        """渲染为 PostgreSQL 方言"""
        expr_str = str(expr)
        
        expr_str = expr_str.replace("current_date()", "CURRENT_DATE")
        expr_str = expr_str.replace("current_timestamp()", "CURRENT_TIMESTAMP")
        
        # PostgreSQL interval 格式: INTERVAL '30 days'
        expr_str = re.sub(r"INTERVAL (\d+) (\w+)", r"INTERVAL '\1 \2'", expr_str)
        
        return expr_str
    
    def _render_clickhouse(self, expr: ir.Expr) -> str:
        """渲染为 ClickHouse 方言"""
        expr_str = str(expr)
        
        expr_str = expr_str.replace("current_date()", "today()")
        expr_str = expr_str.replace("current_timestamp()", "now()")
        
        # ClickHouse interval: today() - 30 (简化写法)
        expr_str = re.sub(r"today\(\) - INTERVAL (\d+) DAY", r"today() - \1", expr_str)
        expr_str = re.sub(r"today\(\) \+ INTERVAL (\d+) DAY", r"today() + \1", expr_str)
        
        # date_trunc -> dateTrunc
        expr_str = re.sub(r"date_trunc\(([^,]+),\s*([^)]+)\)", r"dateTrunc(\2, '\1')", expr_str)
        
        return expr_str
    
    def _render_duckdb(self, expr: ir.Expr) -> str:
        """渲染为 DuckDB 方言"""
        expr_str = str(expr)
        
        expr_str = expr_str.replace("current_date()", "current_date")
        expr_str = expr_str.replace("current_timestamp()", "current_timestamp")
        
        # DuckDB interval 格式
        expr_str = re.sub(r"INTERVAL (\d+) (\w+)", r"INTERVAL '\1 \2'", expr_str)
        
        return expr_str
    
    def _convert_date_trunc_to_mysql(self, expr_str: str) -> str:
        """将 date_trunc 转换为 MySQL 的 DATE_FORMAT"""
        # 提取 date_trunc 参数
        match = re.search(r"date_trunc\('(\w+)',\s*([^)]+)\)", expr_str)
        if match:
            unit = match.group(1).lower()
            date_expr = match.group(2)
            
            format_map = {
                "day": f"DATE_FORMAT({date_expr}, '%Y-%m-%d')",
                "week": f"DATE_FORMAT({date_expr} - INTERVAL WEEKDAY({date_expr}) DAY, '%Y-%m-%d')",
                "month": f"DATE_FORMAT({date_expr}, '%Y-%m-01')",
                "quarter": f"DATE_FORMAT({date_expr}, '%Y-%m-01')",  # 简化处理
                "year": f"DATE_FORMAT({date_expr}, '%Y-01-01')",
            }
            
            return format_map.get(unit, expr_str)
        
        return expr_str
    
    def format_column_date(self, column: str, format_type: str = "YYYY-MM-DD") -> str:
        """
        格式化日期列（用于 SELECT 子句）
        
        Args:
            column: 列名
            format_type: 格式化类型 (YYYY-MM-DD, YYYY-MM, YYYY, YYYY-WW, etc.)
        
        Returns:
            格式化后的 SQL 表达式
        """
        format_map = {
            "mysql": {
                "YYYY-MM-DD": f"DATE_FORMAT({column}, '%Y-%m-%d')",
                "YYYY-MM": f"DATE_FORMAT({column}, '%Y-%m')",
                "YYYY": f"DATE_FORMAT({column}, '%Y')",
                "YYYY-WW": f"DATE_FORMAT({column}, '%Y-%v')",
                "YYYY-MM-DD HH:mm:ss": f"DATE_FORMAT({column}, '%Y-%m-%d %H:%i:%s')",
                "YYYY-MM-DD HH:mm": f"DATE_FORMAT({column}, '%Y-%m-%d %H:%i')",
            },
            "postgresql": {
                "YYYY-MM-DD": f"TO_CHAR({column}, 'YYYY-MM-DD')",
                "YYYY-MM": f"TO_CHAR({column}, 'YYYY-MM')",
                "YYYY": f"TO_CHAR({column}, 'YYYY')",
                "YYYY-WW": f"TO_CHAR({column}, 'IYYY-IW')",
                "YYYY-MM-DD HH:mm:ss": f"TO_CHAR({column}, 'YYYY-MM-DD HH24:MI:SS')",
                "YYYY-MM-DD HH:mm": f"TO_CHAR({column}, 'YYYY-MM-DD HH24:MI')",
            },
            "clickhouse": {
                "YYYY-MM-DD": f"formatDateTime({column}, '%Y-%m-%d')",
                "YYYY-MM": f"formatDateTime({column}, '%Y-%m')",
                "YYYY": f"formatDateTime({column}, '%Y')",
                "YYYY-WW": f"formatDateTime({column}, '%G-%V')",
                "YYYY-MM-DD HH:mm:ss": f"formatDateTime({column}, '%Y-%m-%d %H:%M:%S')",
                "YYYY-MM-DD HH:mm": f"formatDateTime({column}, '%Y-%m-%d %H:%M')",
            },
            "duckdb": {
                "YYYY-MM-DD": f"strftime({column}, '%Y-%m-%d')",
                "YYYY-MM": f"strftime({column}, '%Y-%m')",
                "YYYY": f"strftime({column}, '%Y')",
                "YYYY-WW": f"strftime({column}, '%G-%V')",
                "YYYY-MM-DD HH:mm:ss": f"strftime({column}, '%Y-%m-%d %H:%M:%S')",
                "YYYY-MM-DD HH:mm": f"strftime({column}, '%Y-%m-%d %H:%M')",
            },
        }
        
        dialect_formats = format_map.get(self.dialect, format_map["mysql"])
        return dialect_formats.get(format_type, column)


class TimeFilterBuilder:
    """
    时间过滤条件构建器
    
    将 MQL filter 中的时间条件构建为 SQL 表达式。
    
    使用方式:
        builder = TimeFilterBuilder(dialect="mysql")
        sql = builder.build_filter("order_date", ">=", "LAST_N_DAYS(30)")
        # 结果: "order_date >= CURRENT_DATE - INTERVAL 30 DAY"
    """
    
    def __init__(self, dialect: str = "mysql"):
        self.dialect = dialect
        self.time_handler = TimeFunctionHandler(dialect)
    
    def build_filter(self, field: str, op: str, value: Any) -> str:
        """
        构建时间过滤 SQL
        
        Args:
            field: 字段名
            op: 操作符 (>=, <=, >, <, =, !=)
            value: 值 (可能是 MQL 时间函数如 "LAST_N_DAYS(30)" 或日期字符串)
        
        Returns:
            SQL 表达式字符串
        """
        # 判断值是否为 MQL 时间函数
        if isinstance(value, str) and self.time_handler.is_mql_time_function(value):
            # 解析 MQL 时间函数为 SQL
            sql_value = self.time_handler.parse_and_render(value)
        elif isinstance(value, str):
            # 字符串值，添加引号
            sql_value = f"'{value}'"
        else:
            # 其他类型
            sql_value = str(value)
        
        # 构建比较表达式
        return f"{field} {op} {sql_value}"
    
    def build_date_range_filter(
        self, 
        field: str, 
        start_value: str = None, 
        end_value: str = None,
        start_inclusive: bool = True,
        end_inclusive: bool = True
    ) -> str:
        """
        构建日期范围过滤
        
        Args:
            field: 字段名
            start_value: 起始值 (MQL 时间函数或日期字符串)
            end_value: 结束值 (MQL 时间函数或日期字符串)
            start_inclusive: 起始值是否包含
            end_inclusive: 结束值是否包含
        
        Returns:
            SQL 表达式字符串
        """
        conditions = []
        
        if start_value:
            op = ">=" if start_inclusive else ">"
            conditions.append(self.build_filter(field, op, start_value))
        
        if end_value:
            op = "<=" if end_inclusive else "<"
            conditions.append(self.build_filter(field, op, end_value))
        
        if not conditions:
            return "1=1"
        
        return " AND ".join(conditions)


# 便捷函数
def parse_time_function(func_str: str, dialect: str = "mysql") -> str:
    """
    解析 MQL 时间函数为目标方言 SQL
    
    Args:
        func_str: MQL 时间函数字符串
        dialect: 目标 SQL 方言
    
    Returns:
        SQL 字符串
    """
    handler = TimeFunctionHandler(dialect)
    return handler.parse_and_render(func_str)


def get_supported_time_functions() -> dict:
    """获取支持的 MQL 时间函数列表"""
    return MQL_TIME_FUNCTIONS.copy()