from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from pydantic import BaseModel
import httpx
import json
from pathlib import Path

from app.database import get_db
from app.models.model_config import ModelConfig
from app.models.settings import SystemSetting
from app.services.llm_client import test_llm_connection
from app.utils.encryption import encrypt_api_key, decrypt_api_key

router = APIRouter()

# ─── LLM 供应商配置加载 ───────────────────────────────────────────────────

_PROVIDERS_FILE = Path(__file__).resolve().parent.parent.parent / "config" / "llm_providers.json"
_providers_cache: Optional[dict] = None

# 需要从 LiteLLM model_cost 中自动发现的额外供应商
# key: 内部供应商标识, value: LiteLLM litellm_provider 名称
_LITELLM_DISCOVER_PROVIDERS = {
    "xai": {"litellmProvider": "xai", "label": "xAI (Grok)", "shortLabel": "xAI", "color": "#000000", "group": "international", "needApiKey": True, "showApiBase": False, "apiBase": "", "modelsEndpoint": None, "popularModels": []},
    "cohere": None,  # 已在 JSON 中定义
}


def _load_providers_config() -> dict:
    """加载并缓存供应商配置 JSON"""
    global _providers_cache
    if _providers_cache is None:
        with open(_PROVIDERS_FILE, "r", encoding="utf-8") as f:
            _providers_cache = json.load(f)
    return _providers_cache


def _invalidate_providers_cache():
    """使供应商配置缓存失效（修改 JSON 后调用）"""
    global _providers_cache
    _providers_cache = None


def _get_litellm_models_for_provider(litellm_provider: str) -> list[str]:
    """从 LiteLLM 内置 model_cost 注册表提取指定供应商的模型列表

    LiteLLM 维护了一个包含 2500+ 模型的注册表，无需网络调用即可获取。
    """
    try:
        import litellm
        models: list[str] = []
        seen: set[str] = set()
        for model_name, info in litellm.model_cost.items():
            if not isinstance(info, dict):
                continue
            if info.get("litellm_provider") != litellm_provider:
                continue
            # 去除供应商前缀 (如 "azure/gpt-4" → "gpt-4", "xai/grok-2" → "grok-2")
            clean = model_name
            if "/" in clean:
                clean = clean.split("/", 1)[1]
            # 去除版本后缀标记 (如 "@001", ":0")
            if "@" in clean or (":0" in clean and clean.count(":") == 1):
                continue
            # 过滤掉嵌入类模型和图像模型 (用户通常不需要)
            lower = clean.lower()
            if any(kw in lower for kw in ("embed", "tts", "speech", "dall-e", "flux", "image", "whisper", "stable-diffusion")):
                continue
            if clean and clean not in seen:
                seen.add(clean)
                models.append(clean)
        models.sort(key=str.lower)
        return models
    except Exception:
        return []


# Pydantic Schemas
class ModelConfigCreate(BaseModel):
    model_config = {"protected_namespaces": ()}
    name: str
    provider: str
    model_name: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    is_active: bool = True
    config_params: Optional[dict] = None


class ModelConfigUpdate(BaseModel):
    model_config = {"protected_namespaces": ()}
    name: Optional[str] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    is_active: Optional[bool] = None
    config_params: Optional[dict] = None


class ModelConfigResponse(BaseModel):
    model_config = {
        "protected_namespaces": (),
        "from_attributes": True
    }
    id: str
    name: str
    provider: str
    model_name: str
    api_base: Optional[str]
    is_active: bool
    is_default: bool
    config_params: Optional[dict]
    created_at: str
    updated_at: str


class ModelConfigStatusResponse(BaseModel):
    is_configured: bool
    default_model: Optional[ModelConfigResponse] = None


# --- System Settings Schemas ---
class SystemSettingResponse(BaseModel):
    id: str
    key: str
    value: Any
    category: str
    description: Optional[str] = None
    created_at: str
    updated_at: str

class SystemSettingUpdate(BaseModel):
    value: Any
    description: Optional[str] = None


@router.get("/model", response_model=List[ModelConfigResponse])
def get_model_configs(db: Session = Depends(get_db)):
    """获取所有模型配置"""
    configs = db.query(ModelConfig).all()
    return [ModelConfigResponse(**c.to_dict()) for c in configs]


@router.get("/model/status", response_model=ModelConfigStatusResponse)
def get_model_config_status(db: Session = Depends(get_db)):
    """获取模型配置状态"""
    default_config = db.query(ModelConfig).filter(
        ModelConfig.is_default == True,
        ModelConfig.is_active == True
    ).first()
    
    return ModelConfigStatusResponse(
        is_configured=default_config is not None,
        default_model=ModelConfigResponse(**default_config.to_dict()) if default_config else None
    )


@router.get("/model/{id}", response_model=ModelConfigResponse)
def get_model_config(id: str, db: Session = Depends(get_db)):
    """获取单个模型配置"""
    config = db.query(ModelConfig).filter(ModelConfig.id == id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Model config not found")
    return ModelConfigResponse(**config.to_dict())


@router.post("/model", response_model=ModelConfigResponse)
def create_model_config(data: ModelConfigCreate, db: Session = Depends(get_db)):
    """创建模型配置"""
    # Check if this is the first config, make it default
    existing_count = db.query(ModelConfig).count()
    
    config = ModelConfig(
        name=data.name,
        provider=data.provider,
        model_name=data.model_name,
        api_key=encrypt_api_key(data.api_key) if data.api_key else None,
        api_base=data.api_base,
        is_active=data.is_active,
        is_default=existing_count == 0,  # First config is default
        config_params=data.config_params
    )
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    return ModelConfigResponse(**config.to_dict())


@router.put("/model/{id}", response_model=ModelConfigResponse)
def update_model_config(id: str, data: ModelConfigUpdate, db: Session = Depends(get_db)):
    """更新模型配置"""
    config = db.query(ModelConfig).filter(ModelConfig.id == id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Model config not found")
    
    update_data = data.model_dump(exclude_unset=True)
    
    # Encrypt API key if provided
    if "api_key" in update_data and update_data["api_key"]:
        update_data["api_key"] = encrypt_api_key(update_data["api_key"])
    
    for key, value in update_data.items():
        setattr(config, key, value)
    
    db.commit()
    db.refresh(config)
    
    return ModelConfigResponse(**config.to_dict())


@router.delete("/model/{id}")
def delete_model_config(id: str, db: Session = Depends(get_db)):
    """删除模型配置"""
    config = db.query(ModelConfig).filter(ModelConfig.id == id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Model config not found")
    
    db.delete(config)
    db.commit()
    
    return {"message": "Deleted successfully"}


@router.post("/model/{id}/test")
async def test_model_connection_endpoint(id: str, db: Session = Depends(get_db)):
    """测试模型连接"""
    config = db.query(ModelConfig).filter(ModelConfig.id == id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Model config not found")
    
    # Decrypt API key for testing
    api_key = decrypt_api_key(config.api_key) if config.api_key else None
    
    success, message = await test_llm_connection(
        provider=config.provider,
        model_name=config.model_name,
        api_key=api_key,
        api_base=config.api_base
    )
    
    return {"success": success, "message": message}


@router.put("/model/{id}/activate", response_model=ModelConfigResponse)
def activate_model_config(id: str, db: Session = Depends(get_db)):
    """设为默认模型"""
    config = db.query(ModelConfig).filter(ModelConfig.id == id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Model config not found")
    
    # Remove default from all other configs
    db.query(ModelConfig).update({"is_default": False})
    
    # Set this config as default and active
    config.is_default = True
    config.is_active = True
    
    db.commit()
    db.refresh(config)
    
    return ModelConfigResponse(**config.to_dict())


# --- System Settings Routes ---
@router.get("/system", response_model=List[SystemSettingResponse])
def get_system_settings(category: Optional[str] = None, db: Session = Depends(get_db)):
    """获取系统设置"""
    query = db.query(SystemSetting)
    if category:
        query = query.filter(SystemSetting.category == category)
    settings = query.all()
    return [SystemSettingResponse(**s.to_dict()) for s in settings]


@router.get("/system/{key}", response_model=SystemSettingResponse)
def get_system_setting(key: str, db: Session = Depends(get_db)):
    """获取单个系统设置"""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        # Initial data for time formats if not exists
        if key == "time_formats":
            default_formats = [
                {"name": "YYYY-MM-DD", "label": "按日", "suffix": "day", "is_default": True},
                {"name": "YYYY-MM", "label": "按月", "suffix": "month", "is_default": False},
                {"name": "YYYY", "label": "按年", "suffix": "year", "is_default": False},
                {"name": "YYYY-WW", "label": "按周", "suffix": "week", "is_default": False}
            ]
            setting = SystemSetting(key="time_formats", value=default_formats, category="query", description="支持的时间格式化类型")
            db.add(setting)
            db.commit()
            db.refresh(setting)
        else:
            raise HTTPException(status_code=404, detail="Setting not found")
    return SystemSettingResponse(**setting.to_dict())


@router.put("/system/{key}", response_model=SystemSettingResponse)
def update_system_setting(key: str, data: SystemSettingUpdate, db: Session = Depends(get_db)):
    """更新系统设置"""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        setting = SystemSetting(key=key, value=data.value, category="general", description=data.description)
        db.add(setting)
    else:
        setting.value = data.value
        if data.description is not None:
            setting.description = data.description
    
    db.commit()
    db.refresh(setting)
    return SystemSettingResponse(**setting.to_dict())


# ─── LLM 供应商 & 模型动态查询 ─────────────────────────────────────────────


@router.get("/llm/providers")
def get_llm_providers():
    """获取 LLM 供应商列表

    数据来源：
    1. 本地 JSON 配置文件（UI 元数据：颜色、标签、分组）
    2. LiteLLM 内置注册表（自动发现未在 JSON 中定义的供应商）
    3. 每个供应商会附加 LiteLLM 注册表中的模型数量
    """
    config = _load_providers_config()
    providers = dict(config.get("providers", {}))

    # 为 JSON 中的供应商查询 LiteLLM 模型数量
    for key, cfg in providers.items():
        litellm_p = cfg.get("litellmProvider")
        if litellm_p:
            models = _get_litellm_models_for_provider(litellm_p)
            cfg["litellmModels"] = models
            cfg["litellmModelCount"] = len(models)

    # 从 LiteLLM 注册表发现 JSON 中未定义的供应商
    try:
        import litellm
        discovered_providers: set[str] = set()
        for info in litellm.model_cost.values():
            if isinstance(info, dict):
                lp = info.get("litellm_provider", "")
                if lp and lp not in ("text-completion-openai", "text-completion-azure"):
                    discovered_providers.add(lp)

        # 排除已在 JSON 中定义的（通过 litellmProvider 映射）
        mapped = {cfg.get("litellmProvider") for cfg in providers.values() if cfg.get("litellmProvider")}
        for lp in sorted(discovered_providers - mapped):
            if lp in ("openai", "anthropic", "azure", "deepseek", "mistral", "gemini", "cohere", "ollama", "bedrock", "vertex_ai"):
                # 主流供应商已在 JSON 中，跳过
                if any(cfg.get("litellmProvider") == lp for cfg in providers.values()):
                    continue
            # 为发现的供应商创建默认条目
            label = lp.replace("_", " ").replace("-", " ").title()
            models = _get_litellm_models_for_provider(lp)
            if models:  # 只添加有可用模型的供应商
                providers[f"litellm:{lp}"] = {
                    "group": "other",
                    "label": label,
                    "shortLabel": lp.split("/")[-1][:12],
                    "color": "#6b7280",
                    "litellmProvider": lp,
                    "needApiKey": True,
                    "showApiBase": True,
                    "apiBase": "",
                    "modelsEndpoint": None,
                    "popularModels": [],
                    "litellmModels": models,
                    "litellmModelCount": len(models),
                    "_discovered": True,
                }
    except Exception:
        pass

    return {
        "groups": config.get("groups", []),
        "providers": providers,
    }


class FetchModelsRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None


@router.post("/llm/models")
async def fetch_llm_models(req: FetchModelsRequest):
    """动态查询供应商的可用模型列表

    优先级：
    1. LiteLLM 内置注册表（瞬时返回，无需网络）
    2. 供应商 API 端点（需网络，获取最新）
    3. JSON 配置中的热门模型列表（兜底）
    """
    config = _load_providers_config()
    provider_key = req.provider

    # 处理 LiteLLM 自动发现的供应商（key 格式: "litellm:provider_name"）
    if provider_key.startswith("litellm:"):
        litellm_p = provider_key[len("litellm:"):]
        models = _get_litellm_models_for_provider(litellm_p)
        if models:
            return {"models": models, "source": "litellm_registry"}
        return {"models": [], "source": "empty"}

    provider_cfg = config.get("providers", {}).get(provider_key)
    if not provider_cfg:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {req.provider}")

    # 优先级 1: LiteLLM 内置注册表
    litellm_p = provider_cfg.get("litellmProvider")
    if litellm_p:
        litellm_models = _get_litellm_models_for_provider(litellm_p)
        if litellm_models:
            return {"models": litellm_models, "source": "litellm_registry"}

    # 优先级 2: 供应商 API 端点
    api_base = (req.api_base or provider_cfg.get("apiBase", "")).rstrip("/")
    models_endpoint = provider_cfg.get("modelsEndpoint")

    if api_base and models_endpoint:
        try:
            headers = {}
            if req.api_key:
                headers["Authorization"] = f"Bearer {req.api_key}"

            url = f"{api_base}{models_endpoint}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            models: list[str] = []

            if provider_key == "ollama":
                for m in data.get("models", []):
                    name = m.get("name", "")
                    models.append(name.split(":")[0] if ":" in name else name)
            else:
                for m in data.get("data", []):
                    model_id = m.get("id", "")
                    if model_id and not model_id.startswith("ft:"):
                        models.append(model_id)

            models.sort(key=str.lower)
            if models:
                return {"models": models, "source": "api"}

        except Exception as e:
            # API 失败，继续到兜底
            popular = provider_cfg.get("popularModels", [])
            if popular:
                return {"models": popular, "source": "fallback", "error": str(e)}

    # 优先级 3: JSON 配置中的热门模型
    return {"models": provider_cfg.get("popularModels", []), "source": "config"}
