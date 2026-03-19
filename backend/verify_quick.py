"""
快速验证脚本 - 验证核心导入和基本功能
"""

import sys
import io
from pathlib import Path

# 设置标准输出编码为UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

print("开始快速验证...\n")

# 测试1: 基础导入
print("1. 测试基础导入...")
try:
    from app.agents.skills.base_skill import BaseSkill
    from app.agents.skills.skill_loader import SkillLoader
    from app.agents.routers.llm_router import LLMRouter
    from app.agents.state.query_state import QueryState
    print("[OK] 基础导入成功\n")
except Exception as e:
    print(f"[FAIL] 基础导入失败: {e}\n")
    sys.exit(1)

# 测试2: 节点导入
print("2. 测试节点导入...")
try:
    from app.agents.nodes.preparation_node import PreparationNode
    from app.agents.nodes.generation_node import GenerationNode
    from app.agents.nodes.execution_node import ExecutionNode
    from app.agents.nodes.interpretation_node import InterpretationNode
    print("[OK] 节点导入成功\n")
except Exception as e:
    print(f"[FAIL] 节点导入失败: {e}\n")
    sys.exit(1)

# 测试3: Skills导入
print("3. 测试核心Skills导入...")
try:
    from app.agents.skills.code_skills.metadata.metadata_retrieval import MetadataRetrievalSkill
    from app.agents.skills.code_skills.metadata.intent_analysis import IntentAnalysisSkill
    from app.agents.skills.code_skills.mql.mql_generation import MQLGenerationSkill
    from app.agents.skills.code_skills.mql.mql_validation import MQLValidationSkill
    from app.agents.skills.code_skills.mql.mql_correction import MQLCorrectionSkill
    from app.agents.skills.code_skills.sql.sql_translation import SQLTranslationSkill
    from app.agents.skills.code_skills.execution.query_execution import QueryExecutionSkill
    from app.agents.skills.code_skills.analysis.result_analysis import ResultAnalysisSkill
    print("[OK] 核心Skills导入成功\n")
except Exception as e:
    print(f"[FAIL] 核心Skills导入失败: {e}\n")
    sys.exit(1)

# 测试4: 工作流和Agent导入
print("4. 测试工作流和Agent导入...")
try:
    from app.agents.workflows.mql_query_workflow import MQLQueryWorkflow
    from app.agents.mql_agent import MQLAgent
    print("[OK] 工作流和Agent导入成功\n")
except Exception as e:
    print(f"[FAIL] 工作流和Agent导入失败: {e}\n")
    sys.exit(1)

# 测试5: Skill加载器
print("5. 测试Skill加载器...")
try:
    loader = SkillLoader()
    code_skills = loader.load_code_skills()
    print(f"[OK] Skill加载器正常，加载了 {len(code_skills)} 个代码Skills\n")
except Exception as e:
    print(f"[FAIL] Skill加载器测试失败: {e}\n")
    sys.exit(1)

# 测试6: 工作流构建
print("6. 测试工作流构建...")
try:
    workflow = MQLQueryWorkflow()
    graph = workflow.get_graph()
    print(f"[OK] 工作流构建成功\n")
except Exception as e:
    print(f"[FAIL] 工作流构建失败: {e}\n")
    sys.exit(1)

print("="*50)
print("快速验证完成！所有核心组件正常！")
print("="*50)
print("\n下一步:")
print("  运行完整验证: python verify_full_architecture.py")
print("  或直接测试查询: python test_query.py")
