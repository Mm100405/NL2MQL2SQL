"""
转换脚本沙箱验证服务
"""
import re
import json
import logging
import subprocess
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SandboxValidator:
    """转换脚本沙箱验证器"""

    # 允许使用的JavaScript函数
    ALLOWED_FUNCTIONS = [
        'Array.isArray', 'Object.keys', 'Object.values',
        'Object.entries', 'JSON.stringify', 'JSON.parse',
        'Number', 'String', 'Boolean', 'Date',
        'Math.floor', 'Math.ceil', 'Math.round', 'Math.abs',
        'Array.prototype.map', 'Array.prototype.filter',
        'Array.prototype.reduce', 'Array.prototype.find',
        'Array.prototype.forEach', 'Array.prototype.findIndex',
        'Array.prototype.slice', 'Array.prototype.push',
        'Array.prototype.join', 'Array.prototype.includes',
        'String.prototype.trim', 'String.prototype.split',
        'String.prototype.replace', 'String.prototype.toString',
        'parseInt', 'parseFloat', 'isNaN', 'isFinite'
    ]

    # 禁止的模式
    FORBIDDEN_PATTERNS = [
        (r'eval\s*\(', "禁止使用 eval()"),
        (r'Function\s*\(', "禁止使用 Function()"),
        (r'import\s+', "禁止使用 import"),
        (r'require\s*\(', "禁止使用 require()"),
        (r'fetch\s*\(', "禁止使用 fetch()"),
        (r'window\.', "禁止访问 window 对象"),
        (r'document\.', "禁止访问 document 对象"),
        (r'XMLHttpRequest', "禁止使用 XMLHttpRequest"),
        (r'__proto__', "禁止访问 __proto__"),
        (r'constructor\s*\[', "禁止访问 constructor 属性"),
        (r'child_process', "禁止使用子进程"),
        (r'fs\.', "禁止使用文件系统"),
        (r'process\.', "禁止使用进程对象"),
        (r'exec\s*\(', "禁止执行命令"),
        (r'spawn\s*\(', "禁止生成进程"),
    ]

    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def validate_script(self, script: str, test_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        验证脚本的安全性、语法和功能

        Args:
            script: JavaScript转换脚本
            test_data: 可选的测试数据

        Returns:
            验证结果字典
        """
        logger.info(f"[SandboxValidator] 开始验证脚本，test_data: {test_data is not None}")

        # 1. 安全检查
        security_check = self._security_check(script)
        if not security_check["passed"]:
            return {
                "valid": False,
                "error": f"安全检查失败: {security_check['reason']}",
                "phase": "security"
            }

        # 2. 语法检查
        syntax_check = self._syntax_check(script)
        if not syntax_check["valid"]:
            return {
                "valid": False,
                "error": f"语法错误: {syntax_check['error']}",
                "line": syntax_check.get("line"),
                "phase": "syntax"
            }

        # 3. 功能验证（如果提供了测试数据）
        if test_data is not None:
            logger.info(f"[SandboxValidator] 执行功能验证，test_data keys: {list(test_data.keys())}")
            execution_result = self._execute_mock(script, test_data)
            if not execution_result["success"]:
                return {
                    "valid": False,
                    "error": f"执行错误: {execution_result['error']}",
                    "suggestion": execution_result.get("suggestion"),
                    "phase": "execution"
                }

            # 4. 验证输出格式
            if execution_result.get("result") is not None:
                logger.info(f"[SandboxValidator] 检查输出格式，result type: {type(execution_result['result'])}")
                format_check = self._check_output_format(execution_result["result"])
                if not format_check["valid"]:
                    return {
                        "valid": False,
                        "error": f"输出格式错误: {format_check['error']}",
                        "phase": "format"
                    }

            return {
                "valid": True,
                "result": execution_result.get("result"),
                "executionTime": execution_result.get("executionTime", 0)
            }

        logger.info("[SandboxValidator] 仅语法检查通过")
        return {
            "valid": True,
            "phase": "syntax_only"
        }

    def _security_check(self, script: str) -> Dict[str, Any]:
        """
        安全性检查
        """
        for pattern, reason in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, script, re.IGNORECASE):
                return {
                    "passed": False,
                    "reason": reason
                }

        return {"passed": True}

    def _syntax_check(self, script: str) -> Dict[str, Any]:
        """
        JavaScript语法检查（基础检查）
        """
        # 检查括号匹配
        if script.count('(') != script.count(')'):
            return {
                "valid": False,
                "error": "括号不匹配"
            }

        if script.count('{') != script.count('}'):
            return {
                "valid": False,
                "error": "花括号不匹配"
            }

        if script.count('[') != script.count(']'):
            return {
                "valid": False,
                "error": "方括号不匹配"
            }

        # 检查是否有函数定义
        if 'function' not in script and '=>' not in script:
            return {
                "valid": False,
                "error": "缺少函数定义"
            }

        # 检查return语句
        if 'return' not in script:
            return {
                "valid": False,
                "error": "缺少 return 语句"
            }

        return {"valid": True}

    def _execute_mock(self, script: str, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 Node.js 真实执行 JavaScript 脚本
        """
        import time
        start_time = time.time()

        try:
            # 检查测试数据格式
            if not isinstance(test_data, dict):
                return {
                    "success": False,
                    "error": "测试数据格式错误"
                }

            # 检查是否包含 transformData 函数
            if 'transformData' not in script:
                return {
                    "success": False,
                    "error": "脚本中缺少 transformData 函数"
                }

            # 构建完整的 JavaScript 代码
            js_code = f"""
{script}

// 执行转换
const sourceData = {json.dumps(test_data, ensure_ascii=False)};
const result = transformData(sourceData);

// 输出结果为 JSON
console.log(JSON.stringify(result));
"""

            # 使用 Node.js 执行
            result = subprocess.run(
                ['node', '-e', js_code],
                capture_output=True,
                text=True,
                encoding='utf-8',  # 指定 UTF-8 编码
                timeout=self.timeout
            )

            execution_time = time.time() - start_time

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                logger.error(f"Node.js 执行失败: {error_msg}")

                # 尝试提供修复建议
                suggestion = self._suggest_fix(error_msg)

                return {
                    "success": False,
                    "error": f"JavaScript 执行失败: {error_msg}",
                    "suggestion": suggestion
                }

            # 解析输出
            output = result.stdout.strip()
            if not output:
                return {
                    "success": False,
                    "error": "JavaScript 没有输出结果"
                }

            try:
                parsed_result = json.loads(output)
                logger.info(f"JavaScript 执行成功，结果类型: {type(parsed_result)}")
                return {
                    "success": True,
                    "result": parsed_result,
                    "executionTime": execution_time
                }
            except json.JSONDecodeError as e:
                logger.error(f"JavaScript 输出不是有效的 JSON: {output}")
                return {
                    "success": False,
                    "error": f"JavaScript 输出不是有效的 JSON: {str(e)}"
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "脚本执行超时"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "未找到 Node.js，请确保已安装"
            }
        except Exception as e:
            logger.error(f"执行异常: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _suggest_fix(self, error_msg: str) -> Optional[str]:
        """
        根据错误信息提供修复建议
        """
        error_lower = error_msg.lower()

        if "sourceddata is not defined" in error_lower or "sourceddata" in error_lower:
            return "错误: 变量名拼写错误。应该是 'sourceData' (注意大小写和拼写)"

        if "sourcedata is not defined" in error_lower:
            return "错误: 未定义变量 'sourceData'。请确保函数参数名为 'sourceData'"

        if "columns is not defined" in error_lower:
            return "错误: 未定义变量 'columns'。请使用 sourceData.columns 访问列名"

        if "data is not defined" in error_lower:
            return "错误: 未定义变量 'data'。请使用 sourceData.data 访问数据"

        if "transformdata is not defined" in error_lower or "'transformdata' is not a function" in error_lower:
            return "错误: 函数名应为 'transformData' (注意大小写)"

        return None

    def _check_output_format(self, result: Any) -> Dict[str, Any]:
        """
        检查输出格式
        """
        # 检查是否为数组
        if not isinstance(result, list):
            return {
                "valid": False,
                "error": f"输出必须是数组，实际为: {type(result).__name__}"
            }

        # 空数组直接通过
        if len(result) == 0:
            return {"valid": True}

        # 检查数组元素
        first_item = result[0]
        if not isinstance(first_item, dict):
            return {
                "valid": False,
                "error": f"数组元素必须是对象，实际为: {type(first_item).__name__}"
            }

        return {"valid": True}


def validate_transform_script(
    script: str,
    test_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    便捷函数：验证转换脚本

    Args:
        script: JavaScript转换脚本
        test_data: 可选的测试数据

    Returns:
        验证结果
    """
    validator = SandboxValidator()
    return validator.validate_script(script, test_data)
