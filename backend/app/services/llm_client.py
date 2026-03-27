"""LLM Client - 基于 LiteLLM 的统一多供应商接口

支持 100+ LLM 供应商，无需为每个供应商编写适配代码：
- 国际：OpenAI, Anthropic (Claude), Google Gemini, Azure OpenAI, Mistral AI, Cohere ...
- 国内：DeepSeek, 通义千问, 智谱 (GLM), 月之暗面 (Moonshot), 百川 ...
- 本地：Ollama, vLLM, LM Studio 等所有 OpenAI 兼容端点
- 扩展：任何新供应商只需在前端下拉框添加选项，无需改后端代码

架构说明：
  NATIVE_PROVIDERS 中的供应商使用 LiteLLM 原生协议调用（最优）
  其他供应商通过 OpenAI 兼容协议 + api_base 调用（通用方案）
"""
import litellm
from typing import Optional, Tuple

# 抑制 LiteLLM 调试信息输出
litellm.suppress_debug_info = True

# ─── 供应商路由 ───────────────────────────────────────────────────────────
# 具有原生 LiteLLM 支持的供应商（使用各自的 API 协议，功能最完整）
NATIVE_PROVIDERS = frozenset({
    "openai", "anthropic", "azure", "ollama",
    "deepseek", "mistral", "gemini", "cohere",
    "bedrock", "vertex_ai", "huggingface",
})


def _get_litellm_model(provider: str, model_name: str) -> str:
    """将内部供应商标识转换为 LiteLLM model 标识

    Examples:
        "openai",  "gpt-4"            → "openai/gpt-4"
        "deepseek","deepseek-chat"    → "deepseek/deepseek-chat"
        "qwen",   "qwen-max"          → "openai/qwen-max"    (OpenAI 兼容)
        "custom", "my-model"          → "openai/my-model"    (OpenAI 兼容)
    """
    if provider == "custom":
        return f"openai/{model_name}"
    if provider in NATIVE_PROVIDERS:
        return f"{provider}/{model_name}"
    # 其他供应商（通义千问、智谱、月之暗面等）→ OpenAI 兼容协议
    return f"openai/{model_name}"


def _build_kwargs(
    provider: str,
    model_name: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    **extra: object,
) -> dict:
    """构造 LiteLLM 调用参数"""
    kwargs: dict = {"model": _get_litellm_model(provider, model_name), **extra}
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base
    return kwargs


# ─── 公共接口（保持签名不变，调用方零改动） ────────────────────────────────


async def test_llm_connection(
    provider: str,
    model_name: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
) -> Tuple[bool, str]:
    """测试 LLM 供应商连接"""
    try:
        kwargs = _build_kwargs(
            provider, model_name, api_key, api_base,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5,
            timeout=10.0,
        )
        await litellm.acompletion(**kwargs)
        return True, "连接成功"
    except litellm.AuthenticationError:
        return False, "API Key 无效"
    except litellm.NotFoundError:
        return False, f"模型 {model_name} 不存在"
    except litellm.Timeout:
        return False, "连接超时"
    except litellm.APIConnectionError:
        return False, "无法连接到服务器"
    except litellm.RateLimitError:
        return False, "请求频率超限，请稍后重试"
    except Exception as e:
        return False, str(e)


async def call_llm(
    prompt: str,
    provider: str,
    model_name: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config_params: Optional[dict] = None,
    timeout: Optional[float] = None,
) -> str:
    """调用 LLM 并返回文本响应"""
    config = config_params or {}
    temperature = config.get("temperature", 0.7)
    max_tokens = config.get("max_tokens", 4096)
    timeout = timeout or config.get("timeout", 120.0)

    kwargs = _build_kwargs(
        provider, model_name, api_key, api_base,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )

    response = await litellm.acompletion(**kwargs)
    return response.choices[0].message.content
