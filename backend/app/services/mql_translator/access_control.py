"""
access_control.py - 访问控制预留骨架

当前状态：无用户体系，预留接口。

计划：
- Phase 1: 行级/列级权限控制（基于视图）
- Phase 2: 用户/角色权限体系
- Phase 3: 数据源级别的访问控制

使用方式（未来）：
    access_control = AccessControl(enabled=True)
    access_control.check_permission(user_id, dataset_id, action="read")
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PermissionAction(str, Enum):
    """权限动作"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class ResourceType(str, Enum):
    """资源类型"""
    DATASET = "dataset"
    VIEW = "view"
    METRIC = "metric"
    DIMENSION = "dimension"
    DATASOURCE = "datasource"


@dataclass
class Permission:
    """权限定义"""
    user_id: str
    resource_type: ResourceType
    resource_id: str
    actions: List[PermissionAction]
    conditions: Optional[Dict[str, Any]] = None  # 行级过滤条件


@dataclass
class AccessDecision:
    """访问决策"""
    allowed: bool
    reason: str
    filtered_conditions: Optional[Dict[str, Any]] = None


class AccessControl:
    """
    访问控制器

    预留骨架，当前未启用用户体系时，所有操作默认放行。
    """

    def __init__(self, enabled: bool = False):
        """
        初始化访问控制器

        Args:
            enabled: 是否启用访问控制（当前为 False）
        """
        self.enabled = enabled
        self._permissions: Dict[str, List[Permission]] = {}  # user_id -> permissions

        if not self.enabled:
            logger.info("Access control is disabled, all operations will be allowed")

    def check_permission(
        self,
        user_id: str,
        resource_type: ResourceType,
        resource_id: str,
        action: PermissionAction = PermissionAction.READ,
    ) -> AccessDecision:
        """
        检查用户权限

        Args:
            user_id: 用户 ID
            resource_type: 资源类型
            resource_id: 资源 ID
            action: 操作类型

        Returns:
            AccessDecision
        """
        if not self.enabled:
            # 未启用时全部放行
            return AccessDecision(allowed=True, reason="Access control disabled")

        # 查找用户权限
        user_permissions = self._permissions.get(user_id, [])
        for perm in user_permissions:
            if (
                perm.resource_type == resource_type
                and perm.resource_id == resource_id
                and action in perm.actions
            ):
                return AccessDecision(
                    allowed=True,
                    reason=f"Permission granted for {action} on {resource_type}/{resource_id}",
                    filtered_conditions=perm.conditions,
                )

        return AccessDecision(
            allowed=False,
            reason=f"No permission for {action} on {resource_type}/{resource_id}",
        )

    def add_permission(self, permission: Permission):
        """添加权限"""
        if permission.user_id not in self._permissions:
            self._permissions[permission.user_id] = []
        self._permissions[permission.user_id].append(permission)

    def revoke_permission(
        self,
        user_id: str,
        resource_type: ResourceType,
        resource_id: str,
    ):
        """撤销权限"""
        if user_id in self._permissions:
            self._permissions[user_id] = [
                p for p in self._permissions[user_id]
                if not (p.resource_type == resource_type and p.resource_id == resource_id)
            ]

    def get_row_level_filter(
        self,
        user_id: str,
        resource_type: ResourceType,
        resource_id: str,
    ) -> Optional[str]:
        """
        获取行级过滤条件

        用于在 SQL 查询中自动添加 WHERE 条件。

        Returns:
            SQL 条件字符串，如 "region = '华东' AND department = '销售'"
        """
        decision = self.check_permission(
            user_id, resource_type, resource_id, PermissionAction.READ
        )
        if decision.allowed and decision.filtered_conditions:
            # 将条件转换为 SQL WHERE 子句
            conditions = []
            for key, value in decision.filtered_conditions.items():
                if isinstance(value, str):
                    conditions.append(f"{key} = '{value}'")
                else:
                    conditions.append(f"{key} = {value}")
            return " AND ".join(conditions)
        return None

    def filter_mql_access(
        self,
        user_id: str,
        mql: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        过滤 MQL 中的受限资源

        返回过滤后的 MQL，自动移除用户无权限访问的资源。
        """
        if not self.enabled:
            return mql

        # 深拷贝 MQL
        filtered_mql = mql.copy()

        # 过滤维度
        if "dimensions" in filtered_mql:
            allowed_dimensions = []
            for dim in filtered_mql["dimensions"]:
                # 检查维度权限
                decision = self.check_permission(
                    user_id, ResourceType.DIMENSION, dim, PermissionAction.READ
                )
                if decision.allowed:
                    allowed_dimensions.append(dim)
            filtered_mql["dimensions"] = allowed_dimensions

        # 过滤指标
        if "metrics" in filtered_mql:
            allowed_metrics = []
            if "metricDefinitions" not in filtered_mql:
                filtered_mql["metricDefinitions"] = {}

            for metric in filtered_mql["metrics"]:
                decision = self.check_permission(
                    user_id, ResourceType.METRIC, metric, PermissionAction.READ
                )
                if decision.allowed:
                    allowed_metrics.append(metric)

            filtered_mql["metrics"] = allowed_metrics

        return filtered_mql


# 全局访问控制器实例
_global_access_control: Optional[AccessControl] = None


def get_access_control() -> AccessControl:
    """获取全局访问控制器实例"""
    global _global_access_control
    if _global_access_control is None:
        _global_access_control = AccessControl(enabled=False)
    return _global_access_control
