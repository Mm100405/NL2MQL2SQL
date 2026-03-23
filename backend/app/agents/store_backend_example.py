"""
StoreBackend Skills 管理系统完整示例

演示如何使用基于 StoreBackend 的动态 Skill 管理系统
"""

import asyncio
import os
from app.agents.deep_agents.skill_registry import SkillRegistry, get_skill_registry
from app.agents.deep_agents.enhanced_manager import EnhancedDeepAgentsManager
from app.agents.deep_agents.config import deep_agents_config


# ==================== 示例 1: 基础使用 ====================

async def example_1_basic_usage():
    """示例 1: 基础使用"""
    print("\n" + "="*60)
    print("示例 1: 基础使用")
    print("="*60)
    
    # 1. 创建 Skill 注册表
    registry = SkillRegistry()
    
    # 2. 从本地加载 Skill
    result = await registry.load_skill_from_local(
        skill_id="web-search",
        local_path="backend/app/agents/external_skills/web_search/SKILL.md"
    )
    print(f"✅ 加载 web-search: {result['message']}")
    
    # 3. 从本地加载另一个 Skill
    result = await registry.load_skill_from_local(
        skill_id="code-analyzer",
        local_path="backend/app/agents/external_skills/code_analyzer/SKILL.md"
    )
    print(f"✅ 加载 code-analyzer: {result['message']}")
    
    # 4. 列出已加载的 Skills
    skills = registry.list_skills()
    print(f"\n📋 已加载 Skills ({len(skills)}):")
    for skill in skills:
        print(f"  - {skill['skill_id']}: {skill['description']}")
    
    # 5. 获取统计信息
    stats = registry.get_stats()
    print(f"\n📊 统计信息:")
    print(f"  总计: {stats['total_skills']} Skills")
    print(f"  本地: {stats['local_skills']} Skills")
    print(f"  URL: {stats['url_skills']} Skills")


# ==================== 示例 2: 批量加载 ====================

async def example_2_batch_loading():
    """示例 2: 批量加载"""
    print("\n" + "="*60)
    print("示例 2: 批量加载")
    print("="*60)
    
    # 1. 创建 Skill 注册表
    registry = SkillRegistry()
    
    # 2. 批量加载目录中的所有 Skills
    result = await registry.load_skills_from_directory(
        directory="backend/app/agents/external_skills"
    )
    
    print(f"\n✅ 批量加载结果:")
    print(f"  成功: {len(result['loaded'])}")
    print(f"  跳过: {len(result['skipped'])}")
    print(f"  失败: {len(result['failed'])}")
    
    if result['loaded']:
        print(f"\n✅ 已加载 Skills:")
        for skill_id in result['loaded']:
            print(f"  - {skill_id}")


# ==================== 示例 3: URL 加载 ====================

async def example_3_url_loading():
    """示例 3: 从 URL 加载"""
    print("\n" + "="*60)
    print("示例 3: 从 URL 加载")
    print("="*60)
    
    # 1. 创建 Skill 注册表
    registry = SkillRegistry()
    
    # 2. 从 URL 加载官方 Skill
    skill_url = "https://raw.githubusercontent.com/langchain-ai/deepagents/refs/heads/main/libs/cli/examples/skills/langgraph-docs/SKILL.md"
    
    result = await registry.load_skill_from_url(
        skill_id="langgraph-docs",
        url=skill_url
    )
    
    if result['success']:
        print(f"✅ 成功加载 langgraph-docs Skill")
        print(f"  描述: {result['skill_info']['description']}")
        print(f"  来源: {result['skill_info'].get('metadata', {}).get('author', 'unknown')}")
    else:
        print(f"❌ 加载失败: {result['message']}")


# ==================== 示例 4: 卸载 Skills ====================

async def example_4_unloading():
    """示例 4: 卸载 Skills"""
    print("\n" + "="*60)
    print("示例 4: 卸载 Skills")
    print("="*60)
    
    # 1. 创建 Skill 注册表
    registry = SkillRegistry()
    
    # 2. 加载一些 Skills
    await registry.load_skill_from_local(
        skill_id="web-search",
        local_path="backend/app/agents/external_skills/web_search/SKILL.md"
    )
    await registry.load_skill_from_local(
        skill_id="code-analyzer",
        local_path="backend/app/agents/external_skills/code_analyzer/SKILL.md"
    )
    
    print(f"✅ 已加载 Skills: {registry.count_skills()} 个")
    
    # 3. 卸载单个 Skill
    result = await registry.unload_skill("web-search")
    print(f"\n✅ 卸载 web-search: {result['message']}")
    print(f"✅ 剩余 Skills: {registry.count_skills()} 个")
    
    # 4. 卸载所有 Skills
    result = await registry.unload_all_skills()
    print(f"\n✅ 卸载所有 Skills:")
    print(f"  卸载: {len(result['unloaded'])}")
    print(f"  剩余: {registry.count_skills()} 个")


# ==================== 示例 5: 使用增强管理器 ====================

async def example_5_enhanced_manager():
    """示例 5: 使用增强管理器"""
    print("\n" + "="*60)
    print("示例 5: 使用增强管理器")
    print("="*60)
    
    # 1. 创建增强管理器
    manager = EnhancedDeepAgentsManager()
    
    # 2. 加载 Skills
    result = await manager.load_skills_from_directory(
        directory="backend/app/agents/external_skills"
    )
    print(f"✅ 加载 Skills: {len(result['loaded'])} 个")
    
    # 3. 获取 Agent 信息
    agent_info = manager.get_agent_info()
    print(f"\n📊 Agent 信息:")
    print(f"  Skills 已启用: {agent_info['skills_enabled']}")
    print(f"  Skills 数量: {agent_info['skills_count']}")
    
    # 4. 列出 Skills
    print(f"\n📋 已加载 Skills:")
    for skill in manager.list_skills():
        print(f"  - {skill['skill_id']}: {skill['description']}")
    
    # 5. 卸载所有 Skills
    await manager.unload_all_skills()
    print(f"\n✅ 已卸载所有 Skills")


# ==================== 示例 6: 执行查询 ====================

async def example_6_execute_query():
    """示例 6: 使用 Skills 执行查询"""
    print("\n" + "="*60)
    print("示例 6: 使用 Skills 执行查询")
    print("="*60)
    
    # 1. 创建增强管理器
    manager = EnhancedDeepAgentsManager()
    
    # 2. 加载 Skills
    result = await manager.load_skills_from_directory(
        directory="backend/app/agents/external_skills"
    )
    print(f"✅ 已加载 Skills: {len(result['loaded'])} 个")
    
    # 3. 执行查询（使用 Skills）
    try:
        result = await manager.execute_with_skills(
            natural_language="搜索 LangGraph StateGraph 的最新文档",
            use_skills=True,
            thread_id="demo-session"
        )
        
        if result['success']:
            print(f"\n✅ 查询执行成功")
            print(f"  使用了 Skills: {result['used_skills']}")
            print(f"  Skills 数量: {result['skills_count']}")
        else:
            print(f"\n❌ 查询执行失败: {result.get('error')}")
    except Exception as e:
        print(f"\n⚠️  查询执行异常: {e}")
        print("  (这可能是因为 LLM 未配置或网络问题)")
    
    # 4. 卸载所有 Skills
    await manager.unload_all_skills()


# ==================== 示例 7: 动态管理 ====================

async def example_7_dynamic_management():
    """示例 7: 动态加载/卸载"""
    print("\n" + "="*60)
    print("示例 7: 动态加载/卸载")
    print("="*60)
    
    # 1. 创建注册表
    registry = SkillRegistry()
    
    # 2. 动态加载 Skill
    print("\n📥 加载 web-search Skill...")
    await registry.load_skill_from_local(
        skill_id="web-search",
        local_path="backend/app/agents/external_skills/web_search/SKILL.md"
    )
    print(f"✅ 当前 Skills: {registry.count_skills()} 个")
    
    # 3. 执行一些操作（这里只是模拟）
    print("\n⚙️  使用 Skills 执行任务...")
    # 实际使用中，这里会调用 Agent 执行查询
    
    # 4. 检查 Skill 是否存在
    exists = registry.skill_exists("web-search")
    print(f"\n🔍 web-search 存在: {exists}")
    
    # 5. 获取 Skill 信息
    if exists:
        info = registry.get_skill_info("web-search")
        print(f"\n📄 Skill 信息:")
        print(f"  名称: {info['name']}")
        print(f"  描述: {info['description']}")
        print(f"  来源: {info['source']}")
    
    # 6. 动态卸载
    print("\n📤 卸载 web-search Skill...")
    await registry.unload_skill("web-search")
    print(f"✅ 当前 Skills: {registry.count_skills()} 个")


# ==================== 示例 8: 错误处理 ====================

async def example_8_error_handling():
    """示例 8: 错误处理"""
    print("\n" + "="*60)
    print("示例 8: 错误处理")
    print("="*60)
    
    # 1. 创建注册表
    registry = SkillRegistry()
    
    # 2. 尝试加载不存在的文件
    print("\n📥 尝试加载不存在的文件...")
    result = await registry.load_skill_from_local(
        skill_id="non-existent",
        local_path="backend/app/agents/non-existent/SKILL.md"
    )
    print(f"❌ 加载失败: {result['message']}")
    
    # 3. 尝试卸载不存在的 Skill
    print("\n📤 尝试卸载不存在的 Skill...")
    result = await registry.unload_skill("non-existent")
    print(f"❌ 卸载失败: {result['message']}")
    
    # 4. 获取不存在的 Skill 信息
    print("\n🔍 尝试获取不存在的 Skill 信息...")
    info = registry.get_skill_info("non-existent")
    print(f"❌ 结果: {info}")


# ==================== 主函数 ====================

async def main():
    """运行所有示例"""
    print("\n" + "="*60)
    print("StoreBackend Skills 管理系统 - 完整示例")
    print("="*60)
    
    try:
        # 运行所有示例
        await example_1_basic_usage()
        await example_2_batch_loading()
        await example_3_url_loading()
        await example_4_unloading()
        await example_5_enhanced_manager()
        await example_6_execute_query()
        await example_7_dynamic_management()
        await example_8_error_handling()
        
        print("\n" + "="*60)
        print("✅ 所有示例执行完成!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 示例执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
