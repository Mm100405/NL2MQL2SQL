"""
简化的测试查询 - 不依赖模型配置
"""

import sys
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

print("="*60)
print("  简化测试 - 验证架构功能")
print("="*60 + "\n")

# 测试1: 导入测试
print("1. 导入测试...")
try:
    from app.agents.skills.base_skill import BaseSkill
    from app.agents.skills.skill_loader import SkillLoader
    from app.agents.routers.llm_router import LLMRouter
    from app.agents.state.query_state import QueryState
    from app.agents.nodes.preparation_node import PreparationNode
    from app.agents.nodes.generation_node import GenerationNode
    from app.agents.nodes.execution_node import ExecutionNode
    from app.agents.nodes.interpretation_node import InterpretationNode
    from app.agents.workflows.mql_query_workflow import MQLQueryWorkflow
    from app.agents.mql_agent import MQLAgent
    print("[OK] 所有模块导入成功\n")
except Exception as e:
    print(f"[FAIL] 导入失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试2: Skill功能测试
print("2. Skill功能测试...")
try:
    loader = SkillLoader()
    code_skills = loader.load_code_skills()

    print(f"[OK] 加载了 {len(code_skills)} 个代码Skills:")
    for skill_name, skill_instance in code_skills.items():
        print(f"    - {skill_name}: {skill_instance.description}")
    print()
except Exception as e:
    print(f"[FAIL] Skill加载失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试3: 工作流构建测试
print("3. 工作流构建测试...")
try:
    workflow = MQLQueryWorkflow(db_session=None)
    graph = workflow.get_graph()

    nodes = list(graph.nodes)
    edges = list(graph.edges)

    print(f"[OK] 工作流构建成功:")
    print(f"    节点数: {len(nodes)}")
    print(f"    边数: {len(edges)}")
    print(f"    流程: {' -> '.join([n[0] for n in edges])}")
    print()
except Exception as e:
    print(f"[FAIL] 工作流构建失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试4: Agent初始化测试
print("4. Agent初始化测试...")
try:
    from app.database import get_db
    db = next(get_db())

    agent = MQLAgent(db_session=db)
    print("[OK] Agent初始化成功")
    print(f"    工作流类型: {type(agent.workflow).__name__}")
    db.close()
    print()
except Exception as e:
    print(f"[FAIL] Agent初始化失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试5: 状态创建测试
print("5. 状态创建测试...")
try:
    initial_state = QueryState(
        query="测试查询",
        user_id="test_user"
    )
    print("[OK] 状态创建成功")
    print(f"    查询: {initial_state.get('query', 'N/A')}")
    print(f"    用户: {initial_state.get('user_id', 'N/A')}")
    print()
except Exception as e:
    print(f"[FAIL] 状态创建失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试6: 节点初始化测试
print("6. 节点初始化测试...")
try:
    from app.database import get_db
    db = next(get_db())

    prep_node = PreparationNode(db)
    gen_node = GenerationNode(db)
    exec_node = ExecutionNode(db)
    interp_node = InterpretationNode(db)

    print("[OK] 所有节点初始化成功:")
    print(f"    - PreparationNode: {prep_node.node_name}")
    print(f"    - GenerationNode: {gen_node.node_name}")
    print(f"    - ExecutionNode: {exec_node.node_name}")
    print(f"    - InterpretationNode: {interp_node.node_name}")
    print()

    db.close()
except Exception as e:
    print(f"[FAIL] 节点初始化失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 总结
print("="*60)
print("  测试总结")
print("="*60 + "\n")

tests = [
    "导入测试",
    "Skill功能测试",
    "工作流构建测试",
    "Agent初始化测试",
    "状态创建测试",
    "节点初始化测试"
]

print("所有测试通过:")
for test in tests:
    print(f"  [OK] {test}")

print("\n" + "="*60)
print("  架构验证完成！")
print("="*60)
print("\n说明:")
print("  - 架构基础功能正常")
print("  - 所有组件可以正常初始化")
print("  - 工作流构建成功")
print("\n下一步:")
print("  1. 在前端配置模型（设置 -> 模型配置）")
print("  2. 启动后端服务")
print("  3. 启动前端服务")
print("  4. 在前端进行查询测试")
print("\n配置指南:")
print("  - 前端地址: http://localhost:5173")
print("  - 后端API: http://localhost:8000")
print("  - 文档地址: http://localhost:8000/docs")
print("  - 模型配置: 前端 -> 设置 -> 模型配置")
print("\n支持的模型:")
print("  - OpenAI: GPT-4, GPT-3.5 Turbo (需要API Key)")
print("  - Ollama: llama3, mistral, etc. (本地运行，无需API Key)")
