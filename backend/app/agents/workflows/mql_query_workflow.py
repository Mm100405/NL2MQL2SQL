# backend/app/agents/workflows/mql_query_workflow.py

from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from sqlalchemy.orm import Session

from app.agents.state.query_state import QueryState
from app.agents.nodes.preparation_node import PreparationNode
from app.agents.nodes.generation_node import GenerationNode
from app.agents.nodes.execution_node import ExecutionNode
from app.agents.nodes.interpretation_node import InterpretationNode


class MQLQueryWorkflow:
    """
    MQL查询工作流 - 4节点企业级架构
    """
    
    def __init__(self, db_session: Session, step_callback=None):
        self.db_session = db_session
        self.graph = None
        self.compiled_graph = None
        self.step_callback = step_callback
    
    def build(self):
        """构建工作流图"""
        # 初始化4个节点（传递step_callback）
        preparation_node = PreparationNode(self.db_session, step_callback=self.step_callback)
        generation_node = GenerationNode(self.db_session, step_callback=self.step_callback)
        execution_node = ExecutionNode(self.db_session, step_callback=self.step_callback)
        interpretation_node = InterpretationNode(self.db_session, step_callback=self.step_callback)
        
        # 创建状态图
        self.graph = StateGraph(QueryState)
        
        # 添加节点
        self.graph.add_node("preparation", preparation_node)
        self.graph.add_node("generation", generation_node)
        self.graph.add_node("execution", execution_node)
        self.graph.add_node("interpretation", interpretation_node)
        
        # 设置入口点
        self.graph.set_entry_point("preparation")
        
        # 定义流程
        self.graph.add_edge("preparation", "generation")
        self.graph.add_edge("generation", "execution")
        self.graph.add_edge("execution", "interpretation")
        self.graph.add_edge("interpretation", END)
        
        # 编译工作流
        self.compiled_graph = self.graph.compile()
        
        return self.compiled_graph
    
    def get_graph(self):
        """获取编译后的工作流图"""
        if self.compiled_graph is None:
            return self.build()
        return self.compiled_graph
    
    def get_graph_info(self):
        """获取工作流图信息（节点和边）"""
        if self.graph is None:
            self.build()
        
        # 获取节点和边信息
        nodes = list(self.graph.nodes.keys()) if hasattr(self.graph, 'nodes') else []
        edges = []
        if hasattr(self.graph, 'edges'):
            for edge in self.graph.edges:
                if isinstance(edge, tuple) and len(edge) >= 2:
                    edges.append((edge[0], edge[1]))
        
        return {
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges)
        }
    
    async def run(self, initial_state: QueryState, config: RunnableConfig = None):
        """
        运行工作流
        
        Args:
            initial_state: 初始状态
            config: 运行配置
        
        Returns:
            最终状态
        """
        graph = self.get_graph()
        result = await graph.ainvoke(initial_state, config)
        return result


def create_mql_query_workflow(db_session: Session):
    """创建4节点MQL查询工作流（兼容函数）"""
    workflow = MQLQueryWorkflow(db_session)
    return workflow.build()
