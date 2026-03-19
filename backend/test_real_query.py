"""
测试实际查询
使用前端配置的模型进行查询测试
"""

import sys
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

print("="*60)
print("  测试实际查询")
print("="*60 + "\n")

# 导入必要的模块
try:
    from app.database import get_db
    from app.models.model_config import ModelConfig
    from app.agents.mql_agent import MQLAgent
    from app.utils.encryption import decrypt_api_key
    print("[OK] 必要模块导入成功\n")
except Exception as e:
    print(f"[FAIL] 模块导入失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 获取数据库session
db = next(get_db())

# 检查是否有模型配置
print("1. 检查模型配置...")
default_config = db.query(ModelConfig).filter(
    ModelConfig.is_default == True,
    ModelConfig.is_active == True
).first()

if not default_config:
    print("[WARN] 没有找到默认的模型配置")
    print("\n请按以下步骤配置:")
    print("  1. 启动前端: cd frontend && npm run dev")
    print("  2. 访问: http://localhost:5173")
    print("  3. 进入: 设置 -> 模型配置")
    print("  4. 新增配置:")
    print("     - 提供商: openai 或 ollama")
    print("     - 模型名称: gpt-3.5-turbo 或 llama3")
    print("     - API Key: (OpenAI需要，Ollama不需要)")
    print("     - API地址: (可选，默认值即可)")
    print("  5. 点击'测试连接'验证配置")
    print("  6. 启用配置")
    db.close()
    sys.exit(0)

print(f"[OK] 找到默认配置: {default_config.name}")
print(f"     提供商: {default_config.provider}")
print(f"     模型: {default_config.model_name}")
print(f"     API地址: {default_config.api_base or '默认'}")

# 检查是否有API Key
if default_config.provider != 'ollama' and not default_config.api_key:
    print("\n[WARN] 配置的模型需要API Key，但当前配置中没有")
    print("请在前端编辑配置，添加API Key")
    db.close()
    sys.exit(0)

# 解密API Key
api_key = None
if default_config.api_key:
    try:
        api_key = decrypt_api_key(default_config.api_key)
        print(f"     API Key: {api_key[:10]}...{api_key[-4:] if api_key else 'None'}")
    except Exception as e:
        print(f"[WARN] API Key解密失败: {e}")
        db.close()
        sys.exit(0)
else:
    print("     API Key: 无（Ollama本地模型）")

print()

# 创建Agent实例
print("2. 创建Agent...")
try:
    # 创建临时配置对象（用于Skills初始化）
    # 注意：当前Agent需要先配置LLM环境变量
    # 我们将设置临时环境变量
    import os
    if api_key:
        os.environ['OPENAI_API_KEY'] = api_key
    if default_config.api_base:
        os.environ['OPENAI_API_BASE'] = default_config.api_base

    # 使用db session创建Agent
    agent = MQLAgent(db_session=db)

    # 添加query方法作为execute_query的别名
    agent.query = agent.execute_query

    print("[OK] Agent创建成功")
    print(f"     Provider: {default_config.provider}")
    print(f"     Model: {default_config.model_name}")
    print()
except Exception as e:
    print(f"[FAIL] Agent创建失败: {e}\n")
    import traceback
    traceback.print_exc()
    db.close()
    sys.exit(1)

# 测试查询
test_queries = [
    "查询最近7天的销售额",
    "按产品类别统计上个月的销售数据",
]

async def run_tests():
    """运行测试查询"""
    for i, query in enumerate(test_queries, 1):
        print("="*60)
        print(f"  测试查询 {i}: {query}")
        print("="*60 + "\n")

        try:
            print("执行中...")
            result = await agent.execute_query(
                natural_language=query,
                context={}
            )

            # 打印结果
            print("\n查询结果:")
            print(f"  原始查询: {result.get('natural_language', 'N/A')}")

            if result.get('mql'):
                print(f"  生成的MQL: {result.get('mql', 'N/A')}")

            if result.get('sql'):
                sql = result.get('sql', 'N/A')
                if sql and len(sql) > 200:
                    sql = sql[:200] + "..."
                print(f"  生成的SQL: {sql}")

            query_result = result.get('result')
            if query_result:
                if isinstance(query_result, list):
                    print(f"  数据行数: {len(query_result)}")
                    if len(query_result) > 0:
                        print(f"  示例数据: {query_result[0]}")
                else:
                    print(f"  查询结果: {query_result}")

            if result.get('interpretation'):
                interpretation = result.get('interpretation', '')
                print(f"  解释: {interpretation[:200]}..." if len(interpretation) > 200 else f"  解释: {interpretation}")

            if result.get('steps'):
                print(f"  执行步骤: {len(result.get('steps', []))}")

            if result.get('insights'):
                insights = result.get('insights', [])
                print(f"  洞察数量: {len(insights)}")
                for idx, insight in enumerate(insights[:3], 1):
                    print(f"    {idx}. {insight}")

            print("\n[OK] 查询执行成功")

        except Exception as e:
            print(f"\n[FAIL] 查询执行失败: {e}")
            import traceback
            traceback.print_exc()

        print("\n")

# 运行测试
try:
    print("3. 开始测试查询...")
    asyncio.run(run_tests())

    print("="*60)
    print("  测试完成！")
    print("="*60)
    print("\n说明:")
    print("  - 如果查询成功，说明架构工作正常")
    print("  - 如果查询失败，请检查:")
    print("    1. 模型配置是否正确")
    print("    2. API Key是否有效")
    print("    3. 网络连接是否正常")
    print("    4. 数据库是否有相关数据")
    print("\n下一步:")
    print("  - 在前端进行实际查询测试")
    print("  - 根据需要定制Skills")
    print("  - 优化查询性能")

except KeyboardInterrupt:
    print("\n\n[INFO] 测试被用户中断")
finally:
    db.close()
