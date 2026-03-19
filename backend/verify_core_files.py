"""
验证核心文件的脚本

运行方式：
cd c:/Files/qoderProj/NL2MQL2SQL/backend
python verify_core_files.py
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_file_exists(file_path: str) -> bool:
    """检查文件是否存在"""
    full_path = Path(__file__).parent / file_path
    exists = full_path.exists()
    
    status = "✅" if exists else "❌"
    print(f"{status} {file_path}")
    
    return exists


def verify_phase_1():
    """验证Phase 1: 文档更新"""
    print_header("Phase 1: 文档更新")
    
    files = [
        "../LANGGRAPH_AGENT_DESIGN.md",
        "../LANGGRAPH_IMPLEMENTATION_GUIDE.md"
    ]
    
    all_exist = all([check_file_exists(f) for f in files])
    return all_exist


def verify_phase_2():
    """验证Phase 2: Skill基础架构"""
    print_header("Phase 2: Skill基础架构")
    
    # 检查文件存在
    files = [
        "app/agents/skills/__init__.py",
        "app/agents/skills/base_skill.py",
        "app/agents/skills/markdown_parser.py",
        "app/agents/skills/markdown_executor.py",
        "app/agents/skills/skill_loader.py",
        "app/agents/skills/code_skills/__init__.py",
        "app/agents/skills/code_skills/metadata/__init__.py",
        "app/agents/skills/code_skills/mql/__init__.py",
        "app/agents/skills/code_skills/sql/__init__.py",
        "app/agents/skills/code_skills/execution/__init__.py",
        "app/agents/skills/code_skills/analysis/__init__.py"
    ]
    
    all_exist = all([check_file_exists(f) for f in files])
    
    if not all_exist:
        return False
    
    # 测试导入
    print("\n测试导入...")
    try:
        from app.agents.skills.base_skill import BaseSkill
        print("✅ BaseSkill 导入成功")
        
        from app.agents.skills.markdown_parser import MarkdownSkill
        print("✅ MarkdownSkill 导入成功")
        
        from app.agents.skills.markdown_executor import MarkdownSkillExecutor
        print("✅ MarkdownSkillExecutor 导入成功")
        
        from app.agents.skills.skill_loader import SkillLoader
        print("✅ SkillLoader 导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False


def verify_phase_3():
    """验证Phase 3: LLM智能路由器"""
    print_header("Phase 3: LLM智能路由器")
    
    # 检查文件存在
    file_exists = check_file_exists("app/agents/routers/llm_router.py")
    
    if not file_exists:
        return False
    
    # 测试导入
    print("\n测试导入...")
    try:
        from app.agents.routers.llm_router import LLMRouter
        print("✅ LLMRouter 导入成功")
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False


def verify_phase_4():
    """验证Phase 4: 4个粗粒度节点"""
    print_header("Phase 4: 4个粗粒度节点")
    
    # 检查文件存在
    files = [
        "app/agents/state/__init__.py",
        "app/agents/state/query_state.py",
        "app/agents/nodes/__init__.py",
        "app/agents/nodes/base_node.py",
        "app/agents/nodes/preparation_node.py",
        "app/agents/nodes/generation_node.py",
        "app/agents/nodes/execution_node.py",
        "app/agents/nodes/interpretation_node.py"
    ]
    
    all_exist = all([check_file_exists(f) for f in files])
    
    if not all_exist:
        return False
    
    # 测试导入
    print("\n测试导入...")
    try:
        from app.agents.state.query_state import QueryState
        print("✅ QueryState 导入成功")
        
        from app.agents.nodes.base_node import BaseNode
        print("✅ BaseNode 导入成功")
        
        from app.agents.nodes.preparation_node import PreparationNode
        print("✅ PreparationNode 导入成功")
        
        from app.agents.nodes.generation_node import GenerationNode
        print("✅ GenerationNode 导入成功")
        
        from app.agents.nodes.execution_node import ExecutionNode
        print("✅ ExecutionNode 导入成功")
        
        from app.agents.nodes.interpretation_node import InterpretationNode
        print("✅ InterpretationNode 导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_integration():
    """验证集成（无数据库）"""
    print_header("集成验证（无数据库）")
    
    try:
        print("\n测试SkillLoader初始化（无数据库）...")
        from app.agents.skills.skill_loader import SkillLoader
        
        loader = SkillLoader(db=None)
        print(f"✅ SkillLoader初始化成功: {loader}")
        
        print("\n测试LLMRouter初始化（无数据库）...")
        from app.agents.routers.llm_router import LLMRouter
        
        router = LLMRouter(loader, db=None)
        print(f"✅ LLMRouter初始化成功: {router}")
        
        print("\n测试节点初始化（无数据库）...")
        from app.agents.nodes.preparation_node import PreparationNode
        from app.agents.nodes.generation_node import GenerationNode
        from app.agents.nodes.execution_node import ExecutionNode
        from app.agents.nodes.interpretation_node import InterpretationNode
        
        prep_node = PreparationNode(db=None)
        print(f"✅ PreparationNode初始化成功: {prep_node}")
        
        gen_node = GenerationNode(db=None)
        print(f"✅ GenerationNode初始化成功: {gen_node}")
        
        exec_node = ExecutionNode(db=None)
        print(f"✅ ExecutionNode初始化成功: {exec_node}")
        
        interp_node = InterpretationNode(db=None)
        print(f"✅ InterpretationNode初始化成功: {interp_node}")
        
        return True
    except Exception as e:
        print(f"❌ 集成验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "🔍" * 30)
    print("  企业级LangGraph架构核心文件验证")
    print("🔍" * 30)
    
    results = {}
    
    # 验证各个阶段
    results["Phase 1"] = verify_phase_1()
    results["Phase 2"] = verify_phase_2()
    results["Phase 3"] = verify_phase_3()
    results["Phase 4"] = verify_phase_4()
    results["集成验证"] = verify_integration()
    
    # 打印总结
    print_header("验证总结")
    
    for phase, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{phase}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n" + "🎉" * 30)
        print("  所有验证通过！核心文件已就绪！")
        print("🎉" * 30)
        print("\n下一步：")
        print("1. 创建核心Skills（metadata_retrieval, mql_generation等）")
        print("2. 创建Markdown Skill示例")
        print("3. 创建工作流和Agent")
    else:
        print("\n" + "⚠️" * 30)
        print("  部分验证失败，请检查上述错误信息")
        print("⚠️" * 30)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
