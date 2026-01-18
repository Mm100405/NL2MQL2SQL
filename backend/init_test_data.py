"""
初始化测试数据脚本
"""
import sys
sys.path.append('.')

from app.database import SessionLocal
from app.models.datasource import DataSource
from app.models.dataset import Dataset
from app.models.metric import Metric
from app.models.dimension import Dimension
import json

def init_test_data():
    db = SessionLocal()
    
    try:
        # 1. 创建数据源
        datasource = DataSource(
            name="测试数据库",
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="admin",
            password="password",
            description="测试用PostgreSQL数据源"
        )
        db.add(datasource)
        db.commit()
        db.refresh(datasource)
        print(f"✓ 创建数据源: {datasource.name} (ID: {datasource.id})")
        
        # 2. 创建数据集
        datasets_data = [
            {
                "name": "订单表",
                "physical_name": "orders",
                "schema_name": "public",
                "description": "订单主表",
                "columns": [
                    {"name": "id", "type": "INTEGER", "nullable": False, "comment": "订单ID"},
                    {"name": "user_id", "type": "INTEGER", "nullable": False, "comment": "用户ID"},
                    {"name": "amount", "type": "DECIMAL", "nullable": False, "comment": "订单金额"},
                    {"name": "status", "type": "VARCHAR", "nullable": False, "comment": "订单状态"},
                    {"name": "create_time", "type": "TIMESTAMP", "nullable": False, "comment": "创建时间"}
                ]
            },
            {
                "name": "用户表",
                "physical_name": "users",
                "schema_name": "public",
                "description": "用户信息表",
                "columns": [
                    {"name": "id", "type": "INTEGER", "nullable": False, "comment": "用户ID"},
                    {"name": "name", "type": "VARCHAR", "nullable": False, "comment": "用户名"},
                    {"name": "email", "type": "VARCHAR", "nullable": True, "comment": "邮箱"},
                    {"name": "phone", "type": "VARCHAR", "nullable": True, "comment": "手机号"},
                    {"name": "create_time", "type": "TIMESTAMP", "nullable": False, "comment": "注册时间"}
                ]
            },
            {
                "name": "商品表",
                "physical_name": "products",
                "schema_name": "public",
                "description": "商品信息表",
                "columns": [
                    {"name": "id", "type": "INTEGER", "nullable": False, "comment": "商品ID"},
                    {"name": "name", "type": "VARCHAR", "nullable": False, "comment": "商品名称"},
                    {"name": "price", "type": "DECIMAL", "nullable": False, "comment": "商品价格"},
                    {"name": "category", "type": "VARCHAR", "nullable": True, "comment": "商品分类"}
                ]
            }
        ]
        
        created_datasets = []
        for ds_data in datasets_data:
            dataset = Dataset(
                datasource_id=datasource.id,
                name=ds_data["name"],
                physical_name=ds_data["physical_name"],
                schema_name=ds_data["schema_name"],
                description=ds_data["description"],
                columns=ds_data["columns"]
            )
            db.add(dataset)
            db.commit()
            db.refresh(dataset)
            created_datasets.append(dataset)
            print(f"✓ 创建数据集: {dataset.name} (ID: {dataset.id})")
        
        # 3. 创建指标
        metrics_data = [
            {
                "name": "gmv",
                "display_name": "销售额",
                "metric_type": "basic",
                "dataset_id": created_datasets[0].id,
                "aggregation": "SUM",
                "measure_column": "amount",
                "description": "总销售金额",
                "unit": "元"
            },
            {
                "name": "order_count",
                "display_name": "订单量",
                "metric_type": "basic",
                "dataset_id": created_datasets[0].id,
                "aggregation": "COUNT",
                "measure_column": "id",
                "description": "订单总数",
                "unit": "单"
            },
            {
                "name": "avg_order_value",
                "display_name": "客单价",
                "metric_type": "derived",
                "calculation_formula": "gmv / order_count",
                "description": "平均订单金额",
                "unit": "元"
            }
        ]
        
        for metric_data in metrics_data:
            metric = Metric(**metric_data)
            db.add(metric)
            db.commit()
            db.refresh(metric)
            print(f"✓ 创建指标: {metric.display_name} (ID: {metric.id})")
        
        # 4. 创建维度
        dimensions_data = [
            {
                "name": "date",
                "display_name": "日期",
                "dataset_id": created_datasets[0].id,
                "column_name": "create_time",
                "dimension_type": "time",
                "description": "订单日期维度"
            },
            {
                "name": "user_id",
                "display_name": "用户",
                "dataset_id": created_datasets[0].id,
                "column_name": "user_id",
                "dimension_type": "categorical",
                "description": "用户维度"
            }
        ]
        
        for dim_data in dimensions_data:
            dimension = Dimension(**dim_data)
            db.add(dimension)
            db.commit()
            db.refresh(dimension)
            print(f"✓ 创建维度: {dimension.display_name} (ID: {dimension.id})")
        
        print("\n✅ 测试数据初始化成功！")
        print(f"   - 数据源: 1 个")
        print(f"   - 数据集: {len(created_datasets)} 个")
        print(f"   - 指标: {len(metrics_data)} 个")
        print(f"   - 维度: {len(dimensions_data)} 个")
        
    except Exception as e:
        print(f"❌ 初始化失败: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_test_data()
