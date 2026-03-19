"""
对比分析Skill - 对比不同维度的数据
"""

from typing import Any, Dict, List
from sqlalchemy.orm import Session

from app.agents.skills.base_skill import BaseSkill


class ComparisonAnalysisSkill(BaseSkill):
    """对比分析Skill - 对比不同维度的数据"""
    
    skill_name: str = "comparison_analysis"
    skill_type: str = "analysis"
    description: str = "对比不同维度、时间或类别的数据差异"
    required_inputs: List[str] = ["data", "metric", "dimension"]
    optional_inputs: List[str] = ["group_by"]
    outputs: List[str] = ["comparison", "insights"]
    
    def __init__(self, db: Session = None):
        super().__init__(db)
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行对比分析
        
        Args:
            context: 上下文信息，包含:
                - data: 查询结果数据
                - metric: 对比的指标
                - dimension: 对比的维度
                - group_by: 分组字段
        
        Returns:
            包含对比分析结果的字典
        """
        try:
            data = context.get("data", [])
            metric = context.get("metric", "")
            dimension = context.get("dimension", "")
            
            self.logger.info(f"开始对比分析: {metric} by {dimension}, 数据行数: {len(data)}")
            
            if not data:
                return {
                    "success": True,
                    "comparison": "no_data",
                    "analysis": "没有数据可对比",
                    "differences": []
                }
            
            # 分析对比结果
            comparison_result = self._analyze_comparison(data, metric, dimension)
            
            self.logger.info(f"对比分析完成")
            
            return {
                "success": True,
                "comparison": comparison_result["comparison"],
                "analysis": comparison_result["analysis"],
                "differences": comparison_result.get("differences", []),
                "max_value": comparison_result.get("max_value"),
                "min_value": comparison_result.get("min_value")
            }
            
        except Exception as e:
            self.logger.error(f"对比分析失败: {str(e)}")
            return {
                "success": False,
                "comparison": "error",
                "analysis": f"对比分析失败: {str(e)}",
                "differences": []
            }
    
    def _analyze_comparison(
        self,
        data: List[Dict],
        metric: str,
        dimension: str
    ) -> Dict[str, Any]:
        """
        分析数据对比
        
        Args:
            data: 查询结果数据
            metric: 指标名称
            dimension: 维度名称
        
        Returns:
            对比分析结果
        """
        # 提取各维度的指标值
        dimension_values = {}
        for row in data:
            dim_value = row.get(dimension, "unknown")
            metric_value = row.get(metric, 0)
            
            if dim_value not in dimension_values:
                dimension_values[dim_value] = []
            dimension_values[dim_value].append(metric_value)
        
        # 计算各维度的平均值
        averages = {}
        for dim_value, values in dimension_values.items():
            if values:
                averages[dim_value] = sum(values) / len(values)
        
        if not averages:
            return {
                "comparison": "no_valid_data",
                "analysis": "没有有效的对比数据",
                "differences": []
            }
        
        # 找出最大值和最小值
        max_dim = max(averages, key=averages.get)
        min_dim = min(averages, key=averages.get)
        max_value = averages[max_dim]
        min_value = averages[min_dim]
        
        # 计算差异
        if min_value == 0:
            diff_rate = 0 if max_value == 0 else float('inf')
        else:
            diff_rate = ((max_value - min_value) / min_value) * 100
        
        # 生成差异列表
        differences = []
        for dim_value, avg_value in sorted(averages.items(), key=lambda x: x[1], reverse=True):
            differences.append({
                "dimension": dim_value,
                "average": avg_value,
                "rank": sorted(averages.items(), key=lambda x: x[1], reverse=True).index((dim_value, avg_value)) + 1
            })
        
        # 生成分析文本
        if len(averages) == 2:
            analysis = f"{max_dim}的{metric}最高（{max_value:.2f}），比{min_dim}高{abs(diff_rate):.2f}%"
        else:
            analysis = f"{max_dim}的{metric}最高（{max_value:.2f}），{min_dim}最低（{min_value:.2f}）"
        
        return {
            "comparison": "completed",
            "analysis": analysis,
            "differences": differences,
            "max_value": {"dimension": max_dim, "value": max_value},
            "min_value": {"dimension": min_dim, "value": min_value},
            "diff_rate": diff_rate
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
