import pymysql

# 连接数据库
conn = pymysql.connect(
    host='localhost', 
    port=3306, 
    user='root', 
    password='123456', 
    database='nlqdb'
)
cursor = conn.cursor()

try:
    # 检查并添加外键约束
    
    # 1. 检查 metrics 表的外键
    cursor.execute("SHOW CREATE TABLE metrics")
    result = cursor.fetchone()
    if 'fk_metrics_view_id' not in result[1]:
        print("Adding foreign key to metrics.view_id...")
        cursor.execute("ALTER TABLE metrics ADD CONSTRAINT fk_metrics_view_id FOREIGN KEY (view_id) REFERENCES views(id)")
        print("Success!")
    else:
        print("metrics.view_id foreign key already exists")
    
    # 2. 检查 dimensions 表的外键
    cursor.execute("SHOW CREATE TABLE dimensions")
    result = cursor.fetchone()
    if 'fk_dimensions_view_id' not in result[1]:
        print("Adding foreign key to dimensions.view_id...")
        cursor.execute("ALTER TABLE dimensions ADD CONSTRAINT fk_dimensions_view_id FOREIGN KEY (view_id) REFERENCES views(id)")
        print("Success!")
    else:
        print("dimensions.view_id foreign key already exists")
        
    # 3. 检查 views 表的外键
    cursor.execute("SHOW CREATE TABLE views")
    result = cursor.fetchone()
    if 'fk_views_datasource_id' not in result[1]:
        print("Adding foreign key to views.datasource_id...")
        cursor.execute("ALTER TABLE views ADD CONSTRAINT fk_views_datasource_id FOREIGN KEY (datasource_id) REFERENCES datasources(id)")
        print("Success!")
    else:
        print("views.datasource_id foreign key already exists")
        
    if 'fk_views_base_table_id' not in result[1]:
        print("Adding foreign key to views.base_table_id...")
        cursor.execute("ALTER TABLE views ADD CONSTRAINT fk_views_base_table_id FOREIGN KEY (base_table_id) REFERENCES datasets(id)")
        print("Success!")
    else:
        print("views.base_table_id foreign key already exists")
        
    # 4. 检查 field_dictionaries 表的外键
    cursor.execute("SHOW CREATE TABLE field_dictionaries")
    result = cursor.fetchone()
    constraints = [
        ("fk_field_dicts_ref_view_id", "ref_view_id", "views(id)"),
        ("fk_field_dicts_auto_source_dataset_id", "auto_source_dataset_id", "datasets(id)")
    ]
    
    for constraint_name, column, ref in constraints:
        if constraint_name not in result[1]:
            print(f"Adding foreign key to field_dictionaries.{column}...")
            cursor.execute(f"ALTER TABLE field_dictionaries ADD CONSTRAINT {constraint_name} FOREIGN KEY ({column}) REFERENCES {ref}")
            print("Success!")
        else:
            print(f"field_dictionaries.{column} foreign key already exists")
    
    conn.commit()
    print("\nAll foreign key constraints added successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()