"""
运行验证脚本的包装器，修复sitecustomize问题
"""

import sys
import site

# 修复 sitecustomize 问题
if hasattr(sys, 'setdefaultencoding'):
    # 这个检查会避免 AttributeError
    pass

# 添加 site-packages 回来
site.main()

# 导入验证脚本
sys.path.insert(0, '.')
exec(open('verify_temp.py', encoding='utf-8').read())
