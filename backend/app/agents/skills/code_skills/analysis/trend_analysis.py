"""
趋势分析Skill - 分析数据的趋势变化
"""

from typing import Any, Dict, List
from sqlalchemy.orm import Session

from app.agents.skills.base_skill import BaseSkill


class TrendAnalysisSkill(BaseSkill):
    """趋势分析Skill - 分析数据的趋势变化"""
    
    skill_name: str = "trend_analysis"
    skill_type: str = "analysis"
    description: str = "分析数据的趋势变化，识别上升、下降、平稳等趋势"
    required_inputs: List[str] = ["data", "metric", "time_field"]
    optional_inputs: List[str] = []
    outputs: List[str] = ["trend", "insights"]
    
    def __init__(self, db: Session = None):
        super().__init__(db)
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行趋势分析
        
        Args:
            context: 上下文信息，包含:
                - data: 查询结果数据
                - metric: 分析的指标
                - time_field: 时间字段
        
        Returns:
            包含趋势分析结果的字典
        """
        try:
            data = context.get("data", [])
            metric = context.get("metric", "")
            
            self.logger.info(f"开始趋势分析: {metric}, 数据行数: {len(data)}")
            
            if not data or len(data) < 2:
                return {
                    "success": True,
                    "trend": "insufficient_data",
                    "analysis": "数据不足，无法分析趋势",
                    "direction": "unknown"
                }
            
            # 分析趋势
            trend_result = self._analyze_trend(data, metric)
            
            self.logger.info(f"趋势分析完成: {trend_result}")
            
            return {
                "success": True,
                "trend": trend_result["trend"],
                "analysis": trend_result["analysis"],
                "direction": trend_result["direction"],
                "change_rate": trend_result.get("change_rate", 0)
            }
            
        except Exception as e:
            self.logger.error(f"趋势分析失败: {str(e)}")
            return {
                "success": False,
                "trend": "error",
                "analysis": f"趋势分析失败: {str(e)}",
                "direction": "unknown"
            }
    
    def _analyze_trend(self, data: List[Dict], metric: str) -> Dict[str, Any]:
        """
        分析数据趋势
        
        Args:
            data: 查询结果数据
            metric: 分析的指标名称
        
        Returns:
            趋势分析结果
        """
        # 提取指标值
        values = []
        for row in data:
            if metric in row:
                values.append(row[metric])
        
        if len(values) < 2:
            return {
                "trend": "insufficient_data",
                "analysis": "数据点不足",
                "direction": "unknown"
            }
        
        # 计算变化率
        first_value = values[0]
        last_value = values[-1]
        
        if first_value == 0:
            change_rate = 0 if last_value == 0 else float('inf')
        else:
            change_rate = ((last_value - first_value) / first_value) * 100
        
        # 判断趋势方向
        if change_rate > 5:
            direction = "up"
            trend = "increasing"
            analysis = f"呈上升趋势，增长了{abs(change_rate):.2f}%"
        elif change_rate < -5:
            direction = "down"
            trend = "decreasing"
            analysis = f"呈下降趋势，下降了{abs(change_rate):.2f}%"
        else:
            direction = "stable"
            trend = "stable"
            analysis = "保持平稳，变化幅度在±5%以内"
        
        return {
            "trend": trend,
            "direction": direction,
            "analysis": analysis,
            "change_rate": change_rate,
            "first_value": first_value,
            "last_value": last_value
        }
    
    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """
        验证输入参数
        
        Args:
            context: 上下文信息
        
        Returns:
            是否有效
        """
        if "data" not in context:
            self.logger.error("缺少data参数")
            return False
        
        return True
