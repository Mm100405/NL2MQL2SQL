"""
使用 FilesystemBackend 加载外部 Skill 示例

此文件演示如何在当前项目中加载和使用外部标准 Skill
"""

from app.agents.deep_agents.manager import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver
from app.models.datasource import Datasource
from app.db.database import get_db


async def create_agent_with_external_skills():
    """创建带外部 Skill 的 Agent"""
    
    # 1. 创建检查点器
    checkpointer = MemorySaver()
    
    # 2. 设置文件系统后端
    backend = FilesystemBackend(
        root_dir="c:/Files/qoderProj/NL2MQL2SQL"
    )
    
    # 3. 配置外部 Skill 路径
    # 注意：路径必须使用正斜杠，相对于 backend.root_dir
    external_skills_paths = [
        "./backend/app/agents/external_skills/web_search/",
        "./backend/app/agents/external_skills/code_analyzer/",
    ]
    
    # 4. 创建 Agent（加载外部 Skills）
    agent = create_deep_agent(
        backend=backend,
        skills=external_skills_paths,
        checkpointer=checkpointer,
    )
    
    print(f"✅ Agent 创建成功，已加载 {len(external_skills_paths)} 个外部 Skills")
    print(f"   - web_search")
    print(f"   - code_analyzer")
    
    return agent


async def demo_external_skill_usage():
    """演示外部 Skill 的使用"""
    
    # 1. 创建 Agent
    agent = await create_agent_with_external_skills()
    
    # 2. 模拟使用 web_search Skill
    print("\n=== 演示 1: 使用 web_search Skill ===")
    
    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "搜索关于 LangGraph StateGraph 的最新文档"
                }
            ],
            "natural_language": "搜索关于 LangGraph StateGraph 的最新文档"
        },
        config={
            "configurable": {
                "thread_id": "demo-001"
            }
        }
    )
    
    print(f"结果: {result['messages'][-1]['content'][:200]}...")
    
    # 3. 模拟使用 code_analyzer Skill
    print("\n=== 演示 2: 使用 code_analyzer Skill ===")
    
    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "分析 backend/app/agents/deep_agents/tools.py 的代码质量"
                }
            ],
            "natural_language": "分析 tools.py 的代码质量"
        },
        config={
            "configurable": {
                "thread_id": "demo-002"
            }
        }
    )
    
    print(f"结果: {result['messages'][-1]['content'][:200]}...")


async def create_agent_with_mixed_skills():
    """创建混合使用内部工具和外部 Skill 的 Agent"""
    
    # 注意：当前架构使用自定义的工具系统（get_all_tools()）
    # 外部 Skill 需要通过不同的方式集成
    
    checkpointer = MemorySaver()
    
    backend = FilesystemBackend(
        root_dir="c:/Files/qoderProj/NL2MQL2SQL"
    )
    
    agent = create_deep_agent(
        backend=backend,
        skills=[
            "./backend/app/agents/external_skills/web_search/",
        ],
        checkpointer=checkpointer,
    )
    
    print(f"✅ 创建混合 Agent，结合内部工具和外部 Skill")
    
    return agent


# ==================== 使用场景示例 ====================

class ExternalSkillManager:
    """外部 Skill 管理器"""
    
    def __init__(self, root_dir: str = "c:/Files/qoderProj/NL2MQL2SQL"):
        self.root_dir = root_dir
        self.skill_paths = []
        self.backend = FilesystemBackend(root_dir=root_dir)
    
    def add_skill(self, skill_path: str):
        """添加 Skill 路径"""
        # 确保使用正斜杠
        skill_path = skill_path.replace("\\", "/")
        if not skill_path.startswith("./"):
            skill_path = f"./{skill_path}"
        self.skill_paths.append(skill_path)
        print(f"✅ 添加 Skill: {skill_path}")
    
    def add_all_local_skills(self, skills_dir: str = "./backend/app/agents/external_skills/"):
        """添加所有本地 Skills"""
        import os
        
        skills_dir = skills_dir.replace("\\", "/")
        full_path = os.path.join(self.root_dir, skills_dir.replace("./", ""))
        
        if not os.path.exists(full_path):
            print(f"⚠️  Skills 目录不存在: {full_path}")
            return
        
        for skill_name in os.listdir(full_path):
            skill_path = os.path.join(skills_dir, skill_name).replace("\\", "/")
            self.add_skill(skill_path)
    
    def create_agent(self, checkpointer=None):
        """创建带外部 Skills 的 Agent"""
        if checkpointer is None:
            checkpointer = MemorySaver()
        
        agent = create_deep_agent(
            backend=self.backend,
            skills=self.skill_paths,
            checkpointer=checkpointer,
        )
        
        print(f"✅ Agent 创建成功，已加载 {len(self.skill_paths)} 个 Skills")
        return agent


# ==================== 推荐使用方式 ====================

async def recommended_usage():
    """推荐的使用方式"""
    
    # 1. 初始化 Skill 管理器
    skill_manager = ExternalSkillManager()
    
    # 2. 添加外部 Skills
    skill_manager.add_all_local_skills()
    
    # 3. 创建 Agent
    agent = skill_manager.create_agent()
    
    # 4. 使用 Agent
    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "搜索 LangGraph 最新文档"
                }
            ]
        },
        config={"configurable": {"thread_id": "recommended-001"}}
    )
    
    return result


if __name__ == "__main__":
    import asyncio
    
    # 运行演示
    asyncio.run(demo_external_skill_usage())
