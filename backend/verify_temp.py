"""
临时验证脚本 - 使用-S参数跳过sitecustomize
"""

# 添加项目路径
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("="*60)
print("  架构验证")
print("="*60 + "\n")

print("1. 测试基础导入...")
try:
    from app.agents.skills.base_skill import BaseSkill
    from app.agents.skills.skill_loader import SkillLoader
    from app.agents.routers.llm_router import LLMRouter
    from app.agents.state.query_state import QueryState
    print("[OK] 基础导入成功\n")
except Exception as e:
    print(f"[FAIL] 基础导入失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("2. 测试节点导入...")
try:
    from app.agents.nodes.preparation_node import PreparationNode
    from app.agents.nodes.generation_node import GenerationNode
    from app.agents.nodes.execution_node import ExecutionNode
    from app.agents.nodes.interpretation_node import InterpretationNode
    print("[OK] 节点导入成功\n")
except Exception as e:
    print(f"[FAIL] 节点导入失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

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
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("4. 测试工作流和Agent导入...")
try:
    from app.agents.workflows.mql_query_workflow import MQLQueryWorkflow
    from app.agents.mql_agent import MQLAgent
    print("[OK] 工作流和Agent导入成功\n")
except Exception as e:
    print(f"[FAIL] 工作流和Agent导入失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("5. 测试Skill加载器...")
try:
    loader = SkillLoader()
    code_skills = loader.load_code_skills()
    print(f"[OK] Skill加载器正常，加载了 {len(code_skills)} 个代码Skills\n")
except Exception as e:
    print(f"[FAIL] Skill加载器测试失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("6. 测试工作流构建...")
try:
    workflow = MQLQueryWorkflow(db_session=None)
    graph = workflow.get_graph()
    print(f"[OK] 工作流构建成功\n")
except Exception as e:
    print(f"[FAIL] 工作流构建失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("="*60)
print("快速验证完成！所有核心组件正常！")
print("="*60)
print("\n下一步:")
print("  运行完整验证: python -S verify_full_architecture.py")
print("  或直接测试查询: python -S test_query.py")
