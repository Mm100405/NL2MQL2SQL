from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.model_config import ModelConfig
from app.services.llm_client import test_llm_connection
from app.utils.encryption import encrypt_api_key, decrypt_api_key

router = APIRouter()


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
