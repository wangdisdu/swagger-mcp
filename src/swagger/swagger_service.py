import logging
import random
from typing import Dict, List, Optional, Any, Union

import httpx

from src.swagger.swagger_exceptions import SwaggerServiceError
from src.swagger.swagger_models import (
    SwaggerV2Parameter,
    SwaggerV2Api,
    SwaggerV3Parameter,
    SwaggerV3Api,
    SwaggerV3RequestBody,
    SwaggerV3MediaType,
    SwaggerV3Schema,
    SwaggerDoc,
    SwaggerApi,
    SwaggerParameter,
    SwaggerParameterType,
    SwaggerV3Doc,
    SwaggerV2Doc,
)

logger = logging.getLogger(__name__)


class SwaggerService:
    """
    Swagger服务工具类

    用于获取Swagger API信息和调用API
    """

    def __init__(
        self,
        swagger_urls: Union[str, List[str]],
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
        api_servers: Optional[Union[str, List[str]]] = None,
    ):
        """
        初始化Swagger服务

        Args:
            swagger_urls: Swagger文档URL地址，多个地址用逗号分隔，或者直接传入列表
            headers: 请求头
            timeout: 超时时间（秒）
            api_servers: API调用地址，多个地址用逗号分隔，或者直接传入列表，当为None时使用swagger_urls
        """
        # 处理swagger_urls参数
        if isinstance(swagger_urls, str):
            self.swagger_urls = []
            for url in swagger_urls.split(","):
                url = url.strip().rstrip("/")
                if not url.startswith(("http://", "https://")):
                    url = f"http://{url}"
                self.swagger_urls.append(url)
        else:
            self.swagger_urls = [
                url.strip().rstrip("/")
                if not url.strip().startswith(("http://", "https://"))
                else url.strip().rstrip("/")
                for url in swagger_urls
            ]

        # 处理api_servers参数
        self.api_servers = []
        if api_servers:
            if isinstance(api_servers, str):
                for url in api_servers.split(","):
                    url = url.strip().rstrip("/")
                    if not url.startswith(("http://", "https://")):
                        url = f"http://{url}"
                    self.api_servers.append(url)
            else:
                self.api_servers = [
                    url.strip().rstrip("/")
                    if not url.strip().startswith(("http://", "https://"))
                    else url.strip().rstrip("/")
                    for url in api_servers
                ]

        self.headers = headers or {}
        self.timeout = timeout

        logger.info(
            f"Initialized SwaggerService with URLs: {', '.join(self.swagger_urls)}"
        )
        if self.api_servers:
            logger.info(f"Using API servers: {', '.join(self.api_servers)}")

    async def _make_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        发送HTTP请求，支持失败重试其他地址

        Args:
            method: HTTP方法 (GET, POST等)
            url: 完整URL
            **kwargs: 传递给httpx的其他参数

        Returns:
            httpx.Response

        Raises:
            SwaggerServiceError: 当请求失败时抛出
        """
        # 确保headers存在并合并默认headers
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        kwargs["headers"].update(self.headers)

        try:
            # 记录请求信息
            request_log = {
                "method": method,
                "url": url,
                "headers": kwargs.get("headers", {}),
            }
            if "json" in kwargs:
                request_log["body"] = kwargs["json"]
            elif "data" in kwargs:
                request_log["body"] = kwargs["data"]
            logger.info(f"Swagger Request: {request_log}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
        except Exception as e:
            error_msg = f"Request to {url} failed: {str(e)}"
            logger.warning(error_msg)
            raise SwaggerServiceError(error_msg, e)

    async def _fetch_swagger_doc(self, url: str) -> Dict[str, Any]:
        """
        获取Swagger文档

        Args:
            url: Swagger文档完整URL

        Returns:
            Dict: Swagger文档

        Raises:
            SwaggerServiceError: 当获取文档失败时抛出
        """
        try:
            response = await self._make_request("GET", url)
            return response.json()
        except Exception as e:
            # 如果请求失败，抛出异常
            raise SwaggerServiceError(f"Failed to fetch Swagger document from {url}", e)

    async def _get_swagger_doc(self) -> Dict[str, Any]:
        """
        获取Swagger文档，支持多个URL自动切换

        Returns:
            Dict: Swagger文档

        Raises:
            SwaggerServiceError: 当所有URL都获取失败时抛出
        """
        # 复制URL列表并随机打乱顺序
        urls = self.swagger_urls.copy()
        random.shuffle(urls)

        last_error = None
        failed_urls = []

        for url in urls:
            try:
                doc = await self._fetch_swagger_doc(url)
                return doc
            except Exception as e:
                last_error = e
                failed_urls.append(url)

        # 如果所有URL都失败，抛出异常
        error_msg = f"All Swagger servers failed ({', '.join(failed_urls)})"
        raise SwaggerServiceError(error_msg, last_error)

    def _parse_parameter_v2(self, param: Dict[str, Any]) -> SwaggerV2Parameter:
        """解析OpenAPI v2参数"""

        # 创建 schema
        schema = None
        if "schema" in param:
            schema_data = param["schema"]
            schema = SwaggerV3Schema(
                type=schema_data.get("type"),
                ref=schema_data.get("$ref"),
            )

        return SwaggerV2Parameter(
            name=param.get("name", ""),
            description=param.get("description"),
            required=param.get("required", False),
            type=param.get("type"),
            in_location=param["in"],
            schema_def=schema,
        )

    def _parse_api_info_v2(
        self, path: str, method: str, operation: Dict[str, Any]
    ) -> SwaggerV2Api:
        """解析Swagger v2 API信息"""
        parameters = []

        # 处理参数
        if "parameters" in operation:
            for param in operation["parameters"]:
                parameters.append(self._parse_parameter_v2(param))

        return SwaggerV2Api(
            path=path,
            method=method.upper(),
            summary=operation.get("summary"),
            description=operation.get("description"),
            parameters=parameters,
            tags=operation.get("tags"),
            deprecated=operation.get("deprecated", False),
        )

    def _parse_doc_v2(self, doc: Dict[str, Any]) -> SwaggerV2Doc:
        """解析Swagger v2文档"""
        paths = []
        for path, path_data in doc.get("paths", {}).items():
            for method, operation in path_data.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE"]:
                    paths.append(self._parse_api_info_v2(path, method, operation))
        return SwaggerV2Doc(
            swagger=doc.get("swagger"),
            paths=paths,
            definitions=doc.get("definitions", {}),
        )

    def _parse_parameter_v3(self, param: Dict[str, Any]) -> SwaggerV3Parameter:
        """解析OpenAPI v3参数"""

        # 创建 schema
        schema = None
        if "schema" in param:
            schema_data = param["schema"]
            schema = SwaggerV3Schema(
                type=schema_data.get("type"),
                ref=schema_data.get("$ref"),
            )

        return SwaggerV3Parameter(
            name=param.get("name", ""),
            description=param.get("description"),
            required=param.get("required", False),
            in_location=param["in"],
            schema_def=schema,
        )

    def _parse_request_body_v3(
        self, request_body: Dict[str, Any]
    ) -> SwaggerV3RequestBody:
        """解析OpenAPI v3请求体"""

        content = {}
        if "content" in request_body:
            for content_type, content_data in request_body["content"].items():
                media_type = None
                if "schema" in content_data:
                    media_type = SwaggerV3MediaType(
                        schema_def=SwaggerV3Schema(
                            type=content_data["schema"].get("type"),
                            ref=content_data["schema"].get("$ref"),
                        )
                    )
                content[content_type] = media_type

        return SwaggerV3RequestBody(
            description=request_body.get("description"),
            content=content,
            required=request_body.get("required", False),
        )

    def _parse_api_info_v3(
        self, path: str, method: str, operation: Dict[str, Any]
    ) -> SwaggerV3Api:
        """解析OpenAPI v3 API信息"""
        parameters = []

        # 处理参数
        if "parameters" in operation:
            for param in operation["parameters"]:
                parameters.append(self._parse_parameter_v3(param))

        # 处理请求体
        request_body = None
        if "requestBody" in operation:
            request_body = self._parse_request_body_v3(operation["requestBody"])

        return SwaggerV3Api(
            path=path,
            method=method.upper(),
            summary=operation.get("summary"),
            description=operation.get("description"),
            parameters=parameters,
            request_body=request_body,
            tags=operation.get("tags", []),
            deprecated=operation.get("deprecated", False),
        )

    def _parse_doc_v3(self, doc: Dict[str, Any]) -> SwaggerV3Doc:
        """解析OpenAPI v3文档"""
        paths = []
        for path, path_data in doc.get("paths", {}).items():
            for method, operation in path_data.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE"]:
                    paths.append(self._parse_api_info_v3(path, method, operation))
        return SwaggerV3Doc(
            openapi=doc.get("openapi"),
            paths=paths,
            components=doc.get("components", {}),
        )

    def _convert_v2_to_unified(self, v2_doc: SwaggerV2Doc) -> SwaggerDoc:
        """将Swagger v2文档转换为统一格式"""
        apis = []

        for api in v2_doc.paths:
            # 创建统一格式的API信息
            path_params = []
            query_params = []
            body_params = []

            # 处理参数
            if api.parameters:
                for param in api.parameters:
                    # 创建统一格式的参数
                    param_type = SwaggerParameterType.STRING

                    # 如果是body参数，默认为OBJECT类型
                    if param.in_location == "body":
                        param_type = SwaggerParameterType.OBJECT
                    elif param.type:  # 其他类型的参数使用type字段
                        try:
                            param_type = SwaggerParameterType(param.type)
                        except ValueError:
                            # 如果类型不能识别，跳过此参数
                            continue

                    swagger_param = SwaggerParameter(
                        name=param.name,
                        description=param.description,
                        required=param.required,
                        type=param_type,
                    )

                    # 根据参数位置分类
                    if param.in_location == "path":
                        path_params.append(swagger_param)
                    elif param.in_location == "query":
                        query_params.append(swagger_param)
                    elif param.in_location == "body":
                        # 处理body参数
                        if param.schema_def and param.schema_def.ref:
                            # 处理schema引用
                            ref_name = self._extract_ref_name(param.schema_def.ref)
                            if ref_name and ref_name in v2_doc.definitions:
                                # 获取引用的定义
                                definition = v2_doc.definitions[ref_name]
                                # 解析定义中的属性作为body参数
                                self._parse_definition_properties(
                                    definition, body_params
                                )

            # 创建统一API
            unified_api = SwaggerApi(
                path=api.path,
                method=api.method,
                name=self._generate_api_name(api.path, api.method),
                summary=api.summary,
                description=api.description,
                path_parameters=path_params,
                query_parameters=query_params,
                body_parameters=body_params,
                tags=api.tags or [],
                deprecated=api.deprecated,
            )

            apis.append(unified_api)

        # 创建统一文档
        return SwaggerDoc(version=v2_doc.swagger, apis=apis)

    def _convert_v3_to_unified(self, v3_doc: SwaggerV3Doc) -> SwaggerDoc:
        """将OpenAPI v3文档转换为统一格式"""
        apis = []

        for api in v3_doc.paths:
            # 创建统一格式的API信息
            path_params = []
            query_params = []
            body_params = []

            # 处理参数
            if api.parameters:
                for param in api.parameters:
                    # 获取参数类型
                    param_type = SwaggerParameterType.STRING
                    if param.schema_def and param.schema_def.type:
                        try:
                            param_type = SwaggerParameterType(param.schema_def.type)
                        except ValueError:
                            # 如果类型不能识别，跳过此参数
                            continue

                    swagger_param = SwaggerParameter(
                        name=param.name,
                        description=param.description,
                        required=param.required,
                        type=param_type,
                    )

                    # 根据参数位置分类
                    if param.in_location == "path":
                        path_params.append(swagger_param)
                    elif param.in_location == "query":
                        query_params.append(swagger_param)

            # 处理请求体
            if api.request_body:
                for content_type, media_type in api.request_body.content.items():
                    if media_type and media_type.schema_def:
                        # 处理schema引用
                        if media_type.schema_def.ref:
                            ref_name = self._extract_ref_name(media_type.schema_def.ref)
                            if ref_name and ref_name in v3_doc.components.get(
                                "schemas", {}
                            ):
                                # 获取引用的定义
                                definition = v3_doc.components["schemas"][ref_name]
                                # 解析定义中的属性作为body参数
                                self._parse_definition_properties(
                                    definition, body_params
                                )

            # 创建统一API
            unified_api = SwaggerApi(
                path=api.path,
                method=api.method,
                name=self._generate_api_name(api.path, api.method),
                summary=api.summary,
                description=api.description,
                path_parameters=path_params,
                query_parameters=query_params,
                body_parameters=body_params,
                tags=api.tags or [],
                deprecated=api.deprecated,
            )

            apis.append(unified_api)

        # 创建统一文档
        return SwaggerDoc(version=v3_doc.openapi, apis=apis)

    def _extract_base_url(self, url: str) -> str:
        """
        从 Swagger 文档URL中提取基础URL（去除文档路径部分）

        Args:
            url: Swagger 文档完整URL，例如 https://petstore.swagger.io/v2/swagger.json

        Returns:
            基础URL，例如 https://petstore.swagger.io
        """
        # 解析URL
        from urllib.parse import urlparse

        parsed_url = urlparse(url)
        # 返回 scheme + netloc，例如 https://petstore.swagger.io
        return f"{parsed_url.scheme}://{parsed_url.netloc}"

    def _extract_ref_name(self, ref: str) -> Optional[str]:
        """从引用字符串中提取定义名称

        例如：从 "#/definitions/Pet" 提取 "Pet"
        """
        if not ref:
            return None

        # 处理常见的引用格式
        if ref.startswith("#/definitions/"):
            return ref.replace("#/definitions/", "")
        elif ref.startswith("#/components/schemas/"):
            return ref.replace("#/components/schemas/", "")

        # 如果是其他格式，返回最后一个部分
        parts = ref.split("/")
        if parts:
            return parts[-1]
        return None

    def _parse_definition_properties(
        self, definition: Dict[str, Any], body_params: List[SwaggerParameter]
    ) -> None:
        """解析定义中的属性，并添加到body参数列表中"""
        if not isinstance(definition, dict):
            return

        # 获取属性列表
        properties = definition.get("properties", {})
        required_props = definition.get("required", [])

        # 遍历属性并添加到body参数列表
        for prop_name, prop_def in properties.items():
            # 确定参数类型
            param_type = SwaggerParameterType.STRING
            if "type" in prop_def:
                try:
                    param_type = SwaggerParameterType(prop_def["type"])
                except ValueError:
                    # 如果类型不能识别，跳过此参数
                    continue

            # 创建参数
            swagger_param = SwaggerParameter(
                name=prop_name,
                description=prop_def.get("description"),
                required=prop_name in required_props,
                type=param_type,
            )

            body_params.append(swagger_param)

    def _generate_api_name(self, path: str, method: str) -> str:
        """根据API方法和路径生成名称，将非字母数字字符转换为下划线

        Args:
            path: API路径
            method: HTTP方法

        Returns:
            生成的API名称
        """
        # 先处理方法名，转为小写
        method_part = method.lower()

        # 处理路径
        path_part = ""
        for char in path:
            if char.isalnum():  # 如果是字母或数字
                path_part += char
            else:  # 非字母数字字符替换为下划线
                path_part += "_"

        # 合并方法和路径
        return f"{method_part}_{path_part}"

    async def get_doc(self) -> SwaggerDoc:
        """
        获取所有API列表

        Returns:
            SwaggerDoc: API信息

        Raises:
            SwaggerServiceError: 当获取API列表失败时抛出
        """
        try:
            # 获取原始Swagger文档
            raw_doc = await self._get_swagger_doc()

            # 判断是v2还是v3版本
            if "swagger" in raw_doc and raw_doc["swagger"].startswith("2"):
                # 解析v2文档
                v2_doc = self._parse_doc_v2(raw_doc)
                # 转换为统一格式
                return self._convert_v2_to_unified(v2_doc)
            elif "openapi" in raw_doc and raw_doc["openapi"].startswith("3"):
                # 解析v3文档
                v3_doc = self._parse_doc_v3(raw_doc)
                # 转换为统一格式
                return self._convert_v3_to_unified(v3_doc)
            else:
                # 无法识别的版本
                raise SwaggerServiceError(
                    f"Unsupported Swagger/OpenAPI version: {raw_doc.get('swagger') or raw_doc.get('openapi')}"
                )
        except Exception as e:
            if isinstance(e, SwaggerServiceError):
                raise e
            else:
                raise SwaggerServiceError("Failed to get Swagger document", e)

    async def call_api(self, name: str, params: Dict[str, Any] = None) -> str:
        """
        调用API

        Args:
            name: API名称，由_generate_api_name生成的标识符
            params: 参数，包含path、query和body参数

        Returns:
            ApiCallResult: API调用结果

        Raises:
            SwaggerServiceError: 当API调用失败时抛出
        """
        try:
            # 获取API文档，用于验证参数
            doc = await self.get_doc()

            # 查找匹配的API
            api = None
            for a in doc.apis:
                if a.name == name:
                    api = a
                    break

            if not api:
                raise SwaggerServiceError(f"API not found: {name}")

            # 获取路径和方法
            path = api.path
            method = api.method

            # 准备请求参数
            params = params or {}
            url_path = path
            query_params = {}
            body_data = {}

            # 处理路径参数
            for param in api.path_parameters:
                if param.name in params:
                    # 替换路径中的参数
                    url_path = url_path.replace(
                        f"{{{param.name}}}", str(params[param.name])
                    )
                elif param.required:
                    raise SwaggerServiceError(
                        f"Missing required path parameter: {param.name}"
                    )

            # 处理查询参数
            for param in api.query_parameters:
                if param.name in params:
                    query_params[param.name] = params[param.name]
                elif param.required:
                    raise SwaggerServiceError(
                        f"Missing required query parameter: {param.name}"
                    )

            # 处理请求体参数
            for param in api.body_parameters:
                if param.name in params:
                    body_data[param.name] = params[param.name]
                elif param.required:
                    raise SwaggerServiceError(
                        f"Missing required body parameter: {param.name}"
                    )

            # 构建完整URL
            # 如果path已经是完整URL，则直接使用
            if url_path.startswith(("http://", "https://")):
                full_url = url_path
            else:
                # 使用API调用地址，如果没有配置，则使用Swagger文档URL的基础部分
                if self.api_servers:
                    base_url = self.api_servers[0]  # 使用第一个API调用地址
                else:
                    # 从 Swagger 文档URL中提取基础URL（去除文档路径部分）
                    swagger_url = self.swagger_urls[0]
                    base_url = self._extract_base_url(swagger_url)

                # 确保base_url不以/结尾，path以/开头
                base_url = base_url.rstrip("/")
                url_path = url_path if url_path.startswith("/") else f"/{url_path}"
                full_url = f"{base_url}{url_path}"

            # 发送请求
            kwargs = {}
            if query_params:
                kwargs["params"] = query_params
            if body_data:
                kwargs["json"] = body_data

            response = await self._make_request(method.upper(), full_url, **kwargs)

            return response.text
        except Exception as e:
            if isinstance(e, SwaggerServiceError):
                raise e
            else:
                raise SwaggerServiceError(
                    f"Failed to call API: {method.upper()} {path}", e
                )
