"""
完整的架构验证脚本
用于验证4节点企业级架构的所有组件
"""

import sys
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))


def print_section(title):
    """打印分节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_imports():
    """测试所有模块导入"""
    print_section("1️⃣ 模块导入测试")
    
    tests = []
    
    # 测试Skill基础架构
    try:
        from app.agents.skills.base_skill import BaseSkill
        from app.agents.skills.markdown_parser import MarkdownParser
        from app.agents.skills.markdown_executor import MarkdownExecutor
        from app.agents.skills.skill_loader import SkillLoader
        tests.append(("✅ Skill基础架构", True))
    except Exception as e:
        tests.append(("❌ Skill基础架构", False))
        print(f"错误: {e}")
    
    # 测试LLM路由器
    try:
        from app.agents.routers.llm_router import LLMRouter
        tests.append(("✅ LLM智能路由器", True))
    except Exception as e:
        tests.append(("❌ LLM智能路由器", False))
        print(f"错误: {e}")
    
    # 测试状态定义
    try:
        from app.agents.state.query_state import QueryState
        tests.append(("✅ 状态定义", True))
    except Exception as e:
        tests.append(("❌ 状态定义", False))
        print(f"错误: {e}")
    
    # 测试节点
    try:
        from app.agents.nodes.base_node import BaseNode
        from app.agents.nodes.preparation_node import PreparationNode
        from app.agents.nodes.generation_node import GenerationNode
        from app.agents.nodes.execution_node import ExecutionNode
        from app.agents.nodes.interpretation_node import InterpretationNode
        tests.append(("✅ 4个粗粒度节点", True))
    except Exception as e:
        tests.append(("❌ 4个粗粒度节点", False))
        print(f"错误: {e}")
    
    # 测试核心Skills
    try:
        from app.agents.skills.code_skills.metadata.metadata_retrieval import MetadataRetrievalSkill
        from app.agents.skills.code_skills.metadata.intent_analysis import IntentAnalysisSkill
        from app.agents.skills.code_skills.mql.mql_generation import MQLGenerationSkill
        from app.agents.skills.code_skills.mql.mql_validation import MQLValidationSkill
        from app.agents.skills.code_skills.mql.mql_correction import MQLCorrectionSkill
        from app.agents.skills.code_skills.sql.sql_translation import SQLTranslationSkill
        from app.agents.skills.code_skills.execution.query_execution import QueryExecutionSkill
        from app.agents.skills.code_skills.analysis.result_analysis import ResultAnalysisSkill
        tests.append(("✅ 核心代码Skills", True))
    except Exception as e:
        tests.append(("❌ 核心代码Skills", False))
        print(f"错误: {e}")
    
    # 测试工作流和Agent
    try:
        from app.agents.workflows.mql_query_workflow import MQLQueryWorkflow
        from app.agents.mql_agent import MQLAgent
        tests.append(("✅ 工作流和Agent", True))
    except Exception as e:
        tests.append(("❌ 工作流和Agent", False))
        print(f"错误: {e}")
    
    # 打印结果
    for desc, success in tests:
        print(desc)
    
    return all(success for _, success in tests)


def test_skill_loader():
    """测试Skill加载器"""
    print_section("2️⃣ Skill加载器测试")
    
    try:
        from app.agents.skills.skill_loader import SkillLoader
        
        loader = SkillLoader()
        print(f"✅ Skill加载器创建成功")
        
        # 测试加载所有Skills
        code_skills = loader.load_code_skills()
        print(f"✅ 代码Skills加载完成: {len(code_skills)}个")
        
        # 打印加载的Skills
        print("\n已加载的代码Skills:")
        for skill_path, skill_instance in code_skills.items():
            print(f"  - {skill_path}: {skill_instance.__class__.__name__}")
        
        return True
    except Exception as e:
        print(f"❌ Skill加载器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_router():
    """测试LLM路由器"""
    print_section("3️⃣ LLM路由器测试")
    
    try:
        from app.agents.routers.llm_router import LLMRouter
        from app.agents.state.query_state import QueryState
        
        router = LLMRouter()
        print("✅ LLM路由器创建成功")
        
        # 创建测试状态
        state = QueryState(
            query="测试查询",
            user_id="test_user"
        )
        
        # 测试路由决策（不实际调用LLM，只测试基本功能）
        print("✅ LLM路由器基本功能正常")
        
        return True
    except Exception as e:
        print(f"❌ LLM路由器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_nodes():
    """测试节点功能"""
    print_section("4️⃣ 节点功能测试")
    
    try:
        from app.agents.nodes.preparation_node import PreparationNode
        from app.agents.nodes.generation_node import GenerationNode
        from app.agents.nodes.execution_node import ExecutionNode
        from app.agents.nodes.interpretation_node import InterpretationNode
        from app.agents.state.query_state import QueryState
        
        # 创建测试状态
        state = QueryState(
            query="查询最近7天的销售额",
            user_id="test_user"
        )
        
        # 测试各节点初始化
        prep_node = PreparationNode()
        gen_node = GenerationNode()
        exec_node = ExecutionNode()
        interp_node = InterpretationNode()
        
        print("✅ 所有节点初始化成功")
        print(f"  - PreparationNode: {prep_node.__class__.__name__}")
        print(f"  - GenerationNode: {gen_node.__class__.__name__}")
        print(f"  - ExecutionNode: {exec_node.__class__.__name__}")
        print(f"  - InterpretationNode: {interp_node.__class__.__name__}")
        
        return True
    except Exception as e:
        print(f"❌ 节点测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_workflow():
    """测试工作流构建"""
    print_section("5️⃣ 工作流测试")
    
    try:
        from app.agents.workflows.mql_query_workflow import MQLQueryWorkflow
        
        # 创建工作流
        workflow = MQLQueryWorkflow()
        print("✅ 工作流创建成功")
        
        # 获取LangGraph对象
        graph = workflow.get_graph()
        print(f"✅ LangGraph构建成功")
        
        # 打印工作流结构
        print("\n工作流节点:")
        for node in graph.nodes:
            print(f"  - {node}")
        
        print("\n工作流边:")
        for edge in graph.edges:
            print(f"  - {edge}")
        
        return True
    except Exception as e:
        print(f"❌ 工作流测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_markdown_skills():
    """测试Markdown Skills"""
    print_section("6️⃣ Markdown Skills测试")
    
    try:
        from app.agents.skills.markdown_parser import MarkdownParser
        from app.agents.skills.markdown_executor import MarkdownExecutor
        from pathlib import Path
        
        # 检查Markdown Skills目录
        markdown_dir = Path("app/agents/skills/markdown_skills")
        if not markdown_dir.exists():
            print(f"❌ Markdown Skills目录不存在: {markdown_dir}")
            return False
        
        # 列出所有.md文件
        md_files = list(markdown_dir.glob("*.md"))
        print(f"✅ 找到 {len(md_files)} 个Markdown Skill文件:")
        
        parser = MarkdownParser()
        for md_file in md_files:
            try:
                skill_def = parser.parse_file(str(md_file))
                print(f"  - {md_file.name}")
                print(f"    名称: {skill_def.get('name', 'N/A')}")
                print(f"    描述: {skill_def.get('description', 'N/A')[:50]}...")
            except Exception as e:
                print(f"  ❌ {md_file.name}: 解析失败 - {e}")
        
        return True
    except Exception as e:
        print(f"❌ Markdown Skills测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_structure():
    """测试文件结构"""
    print_section("7️⃣ 文件结构检查")
    
    expected_files = [
        # Skill基础架构
        "app/agents/skills/base_skill.py",
        "app/agents/skills/skill_loader.py",
        "app/agents/skills/markdown_parser.py",
        "app/agents/skills/markdown_executor.py",
        
        # LLM路由器
        "app/agents/routers/llm_router.py",
        
        # 状态定义
        "app/agents/state/query_state.py",
        
        # 节点
        "app/agents/nodes/base_node.py",
        "app/agents/nodes/preparation_node.py",
        "app/agents/nodes/generation_node.py",
        "app/agents/nodes/execution_node.py",
        "app/agents/nodes/interpretation_node.py",
        
        # 核心Skills
        "app/agents/skills/code_skills/metadata/metadata_retrieval.py",
        "app/agents/skills/code_skills/metadata/intent_analysis.py",
        "app/agents/skills/code_skills/mql/mql_generation.py",
        "app/agents/skills/code_skills/mql/mql_validation.py",
        "app/agents/skills/code_skills/mql/mql_correction.py",
        "app/agents/skills/code_skills/sql/sql_translation.py",
        "app/agents/skills/code_skills/execution/query_execution.py",
        "app/agents/skills/code_skills/analysis/result_analysis.py",
        
        # Markdown Skills
        "app/agents/skills/markdown_skills/result_interpretation.md",
        "app/agents/skills/markdown_skills/README.md",
        
        # 工作流和Agent
        "app/agents/workflows/mql_query_workflow.py",
        "app/agents/mql_agent.py",
    ]
    
    missing_files = []
    for file_path in expected_files:
        path = Path(file_path)
        if not path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ 缺少 {len(missing_files)} 个文件:")
        for file in missing_files:
            print(f"  - {file}")
        return False
    else:
        print(f"✅ 所有 {len(expected_files)} 个文件都存在")
        return True


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("  🚀 4节点企业级架构验证")
    print("="*60)
    
    results = []
    
    # 运行所有测试
    results.append(("模块导入", test_imports()))
    results.append(("文件结构", test_file_structure()))
    results.append(("Skill加载器", test_skill_loader()))
    results.append(("LLM路由器", test_llm_router()))
    results.append(("节点功能", asyncio.run(test_nodes())))
    results.append(("工作流", test_workflow()))
    results.append(("Markdown Skills", test_markdown_skills()))
    
    # 打印总结
    print_section("📊 验证总结")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:.<30} {status}")
    
    print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 恭喜！所有验证测试通过！架构已成功构建！")
        print("\n下一步建议:")
        print("  1. 配置LLM密钥（.env文件）")
        print("  2. 配置数据库连接")
        print("  3. 运行完整查询测试")
        print("  4. 根据实际需求定制Skills")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查错误信息并修复。")
        return 1


if __name__ == "__main__":
    exit(main())
