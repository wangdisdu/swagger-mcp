import json
import logging
from typing import Dict, Any, Optional

from src.config import config
from src.swagger.swagger_exceptions import SwaggerServiceError
from src.swagger.swagger_models import SwaggerDoc
from src.swagger.swagger_service import SwaggerService

logger = logging.getLogger(__name__)


class SwaggerTool:
    """Swagger服务工具类，用于管理SwaggerService实例的创建和API调用"""

    @staticmethod
    async def get() -> SwaggerService:
        """获取Swagger服务实例

        Returns:
            SwaggerService: Swagger服务实例

        Raises:
            SwaggerServiceError: 当创建Swagger服务实例失败时抛出
        """
        try:
            # 获取配置
            swagger_urls = config.swagger_urls
            if not swagger_urls:
                raise SwaggerServiceError("SWAGGER_URLS_NOT_CONFIGURED")

            # 解析headers
            headers = {}
            if config.swagger_headers:
                try:
                    headers = json.loads(config.swagger_headers)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse swagger_headers: {e}")

            # 获取API调用地址
            api_servers = config.swagger_api_servers

            # 创建SwaggerService实例
            return SwaggerService(
                swagger_urls=swagger_urls,
                headers=headers,
                timeout=config.swagger_timeout,
                api_servers=api_servers,
            )
        except Exception as e:
            logger.error("Failed to create SwaggerService", exc_info=True)
            if isinstance(e, SwaggerServiceError):
                raise e
            else:
                raise SwaggerServiceError("GET_SWAGGER_SERVICE_ERROR", e)

    @staticmethod
    async def get_doc() -> SwaggerDoc:
        """
        获取API文档

        Returns:
            SwaggerDoc: API文档信息

        Raises:
            SwaggerServiceError: 当获取API文档失败时抛出
        """
        try:
            swagger_service = await SwaggerTool.get()
            return await swagger_service.get_doc()
        except Exception as e:
            logger.error("get swagger doc exception", exc_info=True)
            if isinstance(e, SwaggerServiceError):
                raise e
            else:
                raise SwaggerServiceError("GET_SWAGGER_DOC_ERROR", e)

    @staticmethod
    async def call_api(name: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        调用API

        Args:
            name: API名称，由_generate_api_name生成的标识符
            params: 参数，包含path、query和body参数

        Returns:
            Any: API调用结果

        Raises:
            SwaggerServiceError: 当API调用失败时抛出
        """
        try:
            swagger_service = await SwaggerTool.get()
            return await swagger_service.call_api(name, params)
        except Exception as e:
            logger.error(f"call_api exception: {name}", exc_info=True)
            if isinstance(e, SwaggerServiceError):
                raise e
            else:
                raise SwaggerServiceError(f"CALL_API_ERROR: {name}", e)
