from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, ConfigDict, Field


class BaseSwaggerModel(BaseModel):
    """Swagger模型基类"""

    model_config = ConfigDict(
        extra="ignore",  # 忽略额外字段
        str_strip_whitespace=True,  # 自动去除字符串首尾空白
        from_attributes=True,  # 支持从对象属性创建模型
    )


# Swagger v2 模型


class SwaggerV2Schema(BaseSwaggerModel):
    """OpenAPI v3 Schema"""

    type: Optional[str] = None
    ref: Optional[str] = None


class SwaggerV2Parameter(BaseSwaggerModel):
    """Swagger v2 参数信息"""

    name: str
    description: Optional[str] = None
    required: bool = False
    type: Optional[str] = None  # 参数类型
    in_location: Optional[str] = None  # 参数位置
    schema_def: Optional[SwaggerV2Schema] = None  # 用于body参数


class SwaggerV2Api(BaseSwaggerModel):
    """Swagger v2 API信息"""

    path: str  # API路径
    method: str  # HTTP方法
    summary: Optional[str] = None  # 摘要
    description: Optional[str] = None  # 描述
    parameters: Optional[List[SwaggerV2Parameter]] = None  # 参数列表
    tags: Optional[List[str]] = None  # 标签
    deprecated: bool = False  # 是否已废弃


class SwaggerV2Doc(BaseSwaggerModel):
    """Swagger v2 文档信息"""

    swagger: str  # Swagger版本
    paths: List[SwaggerV2Api] = Field(default_factory=list)  # API列表
    definitions: Dict[str, Any] = Field(default_factory=dict)  # 组件


# OpenAPI v3 模型


class SwaggerV3Schema(BaseSwaggerModel):
    """OpenAPI v3 Schema"""

    type: Optional[str] = None
    ref: Optional[str] = None


class SwaggerV3MediaType(BaseSwaggerModel):
    """OpenAPI v3 媒体类型"""

    schema_def: Optional[SwaggerV3Schema] = None


class SwaggerV3RequestBody(BaseSwaggerModel):
    """OpenAPI v3 请求体"""

    description: Optional[str] = None
    content: Dict[str, SwaggerV3MediaType] = Field(default_factory=dict)
    required: bool = False


class SwaggerV3Parameter(BaseSwaggerModel):
    """OpenAPI v3 参数信息"""

    name: str
    description: Optional[str] = None
    required: bool = False
    in_location: Optional[str] = None  # 参数位置
    schema_def: Optional[SwaggerV3Schema] = None


class SwaggerV3Api(BaseSwaggerModel):
    """OpenAPI v3 API信息"""

    path: str  # API路径
    method: str  # HTTP方法
    summary: Optional[str] = None  # 摘要
    description: Optional[str] = None  # 描述
    parameters: Optional[List[SwaggerV3Parameter]] = None  # 参数列表
    request_body: Optional[SwaggerV3RequestBody] = None  # 请求体
    tags: Optional[List[str]] = None  # 标签
    deprecated: bool = False  # 是否已废弃


class SwaggerV3Doc(BaseSwaggerModel):
    """OpenAPI v3 文档信息"""

    openapi: str  # OpenAPI版本
    paths: List[SwaggerV3Api] = Field(default_factory=list)  # API列表
    components: Dict[str, Any] = Field(default_factory=dict)  # 组件


# 统一API信息模型 - 用于内部处理和对外展示


class SwaggerParameterType(str, Enum):
    """参数类型枚举"""

    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class SwaggerParameter(BaseSwaggerModel):
    """API参数信息"""

    name: str
    description: Optional[str] = None
    required: bool = False
    type: SwaggerParameterType  # 参数类型


class SwaggerApi(BaseSwaggerModel):
    """API信息"""

    name: Optional[str] = None  # API名称，基于method和path生成的标识符
    path: str  # API路径
    method: str  # HTTP方法
    summary: Optional[str] = None  # 摘要
    description: Optional[str] = None  # 描述
    path_parameters: List[SwaggerParameter] = Field(
        default_factory=list
    )  # Path参数列表
    query_parameters: List[SwaggerParameter] = Field(
        default_factory=list
    )  # Query参数列表
    body_parameters: List[SwaggerParameter] = Field(
        default_factory=list
    )  # Body参数列表
    tags: List[str] = Field(default_factory=list)  # 标签
    deprecated: bool = False  # 是否已废弃


class SwaggerDoc(BaseSwaggerModel):
    """API文档"""

    version: str  # 版本
    apis: List[SwaggerApi] = Field(default_factory=list)  # API列表
