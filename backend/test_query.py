"""
完整查询测试脚本
测试从自然语言到SQL的完整流程
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))


async def test_query():
    """测试完整查询流程"""
    print("="*60)
    print("  🔍 完整查询流程测试")
    print("="*60 + "\n")
    
    # 导入必要的模块
    from app.agents.mql_agent import MQLAgent
    from app.agents.state.query_state import QueryState
    
    # 创建Agent
    print("1️⃣ 创建Agent...")
    try:
        agent = MQLAgent()
        print("✅ Agent创建成功\n")
    except Exception as e:
        print(f"❌ Agent创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 测试查询
    test_queries = [
        "查询最近7天的销售额",
        "按产品类别统计上个月的销售数据",
        "查看本季度的订单数量趋势"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"  测试查询 {i}: {query}")
        print(f"{'='*60}\n")
        
        try:
            # 执行查询
            print("执行查询...")
            result = await agent.query(
                query=query,
                user_id="test_user"
            )
            
            # 打印结果
            print("\n查询结果:")
            print(f"  成功: {result.get('success', False)}")
            print(f"  消息: {result.get('message', 'N/A')}")
            
            if result.get('sql'):
                print(f"  生成的SQL: {result.get('sql', 'N/A')}")
            
            if result.get('data'):
                print(f"  数据行数: {len(result.get('data', []))}")
            
            if result.get('explanation'):
                print(f"  解释: {result.get('explanation', 'N/A')[:100]}...")
            
        except Exception as e:
            print(f"❌ 查询执行失败: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print("\n" + "="*60)
    print("  ✅ 查询测试完成")
    print("="*60)
    
    return True


def main():
    """主函数"""
    try:
        success = asyncio.run(test_query())
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
