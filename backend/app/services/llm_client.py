"""LLM Client for multiple providers"""
import httpx
from typing import Optional, Tuple
import openai


async def test_llm_connection(
    provider: str,
    model_name: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None
) -> Tuple[bool, str]:
    """Test connection to LLM provider"""
    try:
        if provider == "openai":
            return await _test_openai(api_key, api_base, model_name)
        elif provider == "ollama":
            return await _test_ollama(api_base or "http://localhost:11434", model_name)
        elif provider == "azure":
            return await _test_azure(api_key, api_base, model_name)
        elif provider == "custom":
            return await _test_custom(api_key, api_base, model_name)
        else:
            return False, f"Unknown provider: {provider}"
    except Exception as e:
        return False, str(e)


async def _test_openai(api_key: str, api_base: Optional[str], model_name: str) -> Tuple[bool, str]:
    """Test OpenAI connection"""
    if not api_key:
        return False, "API key is required for OpenAI"
    
    client = openai.AsyncOpenAI(
        api_key=api_key,
        base_url=api_base if api_base else None
    )
    
    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        return True, "Connection successful"
    except openai.AuthenticationError:
        return False, "Invalid API key"
    except openai.NotFoundError:
        return False, f"Model {model_name} not found"
    except Exception as e:
        return False, str(e)


async def _test_ollama(api_base: str, model_name: str) -> Tuple[bool, str]:
    """Test Ollama connection"""
    async with httpx.AsyncClient() as client:
        try:
            # Check if Ollama is running
            response = await client.get(f"{api_base}/api/tags", timeout=5.0)
            if response.status_code != 200:
                return False, "Cannot connect to Ollama server"
            
            # Check if model exists
            models = response.json().get("models", [])
            model_names = [m.get("name", "").split(":")[0] for m in models]
            
            if model_name not in model_names and f"{model_name}:latest" not in [m.get("name") for m in models]:
                return False, f"Model {model_name} not found. Available: {', '.join(model_names)}"
            
            return True, "Connection successful"
        except httpx.ConnectError:
            return False, "Cannot connect to Ollama server. Is it running?"
        except Exception as e:
            return False, str(e)


async def _test_azure(api_key: str, api_base: str, model_name: str) -> Tuple[bool, str]:
    """Test Azure OpenAI connection"""
    if not api_key or not api_base:
        return False, "API key and endpoint are required for Azure OpenAI"
    
    # Azure OpenAI uses different endpoint format
    client = openai.AsyncAzureOpenAI(
        api_key=api_key,
        azure_endpoint=api_base,
        api_version="2024-02-15-preview"
    )
    
    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        return True, "Connection successful"
    except Exception as e:
        return False, str(e)


async def _test_custom(api_key: Optional[str], api_base: str, model_name: str) -> Tuple[bool, str]:
    """Test custom API endpoint"""
    if not api_base:
        return False, "API base URL is required for custom provider"
    
    async with httpx.AsyncClient() as client:
        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            response = await client.get(f"{api_base}/models", headers=headers, timeout=5.0)
            if response.status_code == 200:
                return True, "Connection successful"
            else:
                return False, f"Server returned status {response.status_code}"
        except Exception as e:
            return False, str(e)


async def call_llm(
    prompt: str,
    provider: str,
    model_name: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config_params: Optional[dict] = None
) -> str:
    """Call LLM and return response"""
    config = config_params or {}
    temperature = config.get("temperature", 0.7)
    max_tokens = config.get("max_tokens", 4096)
    
    if provider == "openai":
        return await _call_openai(prompt, api_key, api_base, model_name, temperature, max_tokens)
    elif provider == "ollama":
        return await _call_ollama(prompt, api_base or "http://localhost:11434", model_name, temperature, max_tokens)
    elif provider == "azure":
        return await _call_azure(prompt, api_key, api_base, model_name, temperature, max_tokens)
    elif provider == "custom":
        return await _call_custom(prompt, api_key, api_base, model_name, temperature, max_tokens)
    else:
        raise ValueError(f"Unknown provider: {provider}")


async def _call_openai(prompt: str, api_key: str, api_base: Optional[str], model_name: str, temperature: float, max_tokens: int) -> str:
    client = openai.AsyncOpenAI(
        api_key=api_key,
        base_url=api_base if api_base else None
    )
    
    response = await client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    return response.choices[0].message.content


async def _call_ollama(prompt: str, api_base: str, model_name: str, temperature: float, max_tokens: int) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{api_base}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            },
            timeout=60.0
        )
        return response.json().get("response", "")


async def _call_azure(prompt: str, api_key: str, api_base: str, model_name: str, temperature: float, max_tokens: int) -> str:
    client = openai.AsyncAzureOpenAI(
        api_key=api_key,
        azure_endpoint=api_base,
        api_version="2024-02-15-preview"
    )
    
    response = await client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    return response.choices[0].message.content


async def _call_custom(prompt: str, api_key: Optional[str], api_base: str, model_name: str, temperature: float, max_tokens: int) -> str:
    async with httpx.AsyncClient() as client:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        try:
            response = await client.post(
                f"{api_base}/chat/completions",
                headers=headers,
                json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except httpx.TimeoutException:
            raise Exception("LLM request timed out after 30 seconds")
        except Exception as e:
            raise Exception(f"LLM request failed: {str(e)}")
