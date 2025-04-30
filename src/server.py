import logging
from typing import Any

from mcp.server.lowlevel import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, Request, TextContent
from starlette.applications import Starlette
from starlette.routing import Mount, Route

from src.config import config
from src.exceptions import ToolException
from src.swagger.swagger_tool import SwaggerTool

SWAGGER_TOOL_PREFIX: str = config.swagger_tool_prefix

SSE_PATH: str = "/sse"
MESSAGE_PATH: str = "/messages/"

mcp = Server("Swagger MCP Server")

sse = SseServerTransport(MESSAGE_PATH)

logger = logging.getLogger(__name__)


async def handle_sse(request: Request) -> None:
    async with sse.connect_sse(
        request.scope,
        request.receive,
        request._send,
    ) as streams:
        await mcp.run(
            streams[0],
            streams[1],
            mcp.create_initialization_options(),
        )


# Initialize Starlette App
app = Starlette(
    debug=True,
    routes=[
        Route(SSE_PATH, endpoint=handle_sse),
        Mount(MESSAGE_PATH, app=sse.handle_post_message),
    ],
)


@mcp.list_tools()
async def list_swagger_tools() -> list[Tool]:
    try:
        # 获取API文档
        swagger_doc = await SwaggerTool.get_doc()

        # 将SwaggerDoc转换为Tool列表
        tools = []
        for api in swagger_doc.apis:
            # 构建输入schema
            properties = {}
            required = []

            # 添加路径参数
            for param in api.path_parameters:
                properties[param.name] = {
                    "type": param.type.value,
                    "description": param.description or f"Path parameter: {param.name}",
                }
                if param.required:
                    required.append(param.name)

            # 添加查询参数
            for param in api.query_parameters:
                properties[param.name] = {
                    "type": param.type.value,
                    "description": param.description
                    or f"Query parameter: {param.name}",
                }
                if param.required:
                    required.append(param.name)

            # 添加请求体参数
            for param in api.body_parameters:
                properties[param.name] = {
                    "type": param.type.value,
                    "description": param.description or f"Body parameter: {param.name}",
                }
                if param.required:
                    required.append(param.name)

            # 构建工具描述
            description = f"{api.summary or 'API'}"
            if api.description:
                description += f"\n\n{api.description}"

            # 添加标签信息
            if api.tags:
                description += f"\n\nTags: {', '.join(api.tags)}"

            # 如果API已废弃，添加警告
            if api.deprecated:
                description += "\n\n This API is deprecated."

            name = f"{SWAGGER_TOOL_PREFIX}{api.name}"
            # 创建Tool对象
            tool = Tool(
                name=name,
                description=description,
                inputSchema={
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            )
            tools.append(tool)

        return tools
    except Exception as e:
        logger.error(f"list_swagger_tools error: {str(e)}", exc_info=True)
        # 发生错误时返回空列表
        return []


@mcp.call_tool()
async def call_swagger_api(name: str, arguments: dict) -> Any:
    try:
        # 从工具名称中提取API名称
        # 工具名称格式为: swagger_<api_name>
        if not name.startswith(SWAGGER_TOOL_PREFIX):
            raise ToolException("unknown tool", code="UNKNOWN_TOOL")

        api_name = name[len(SWAGGER_TOOL_PREFIX) :]

        # 获取API文档
        swagger_doc = await SwaggerTool.get_doc()

        # 查找匹配的API
        api = None
        for a in swagger_doc.apis:
            if a.name == api_name:
                api = a
                break

        if not api:
            raise ToolException(f"API not found: {api_name}", code="API_NOT_FOUND")

        # 调用API
        result = await SwaggerTool.call_api(api_name, arguments)

        return [TextContent(type="text", text=result)]
    except Exception as e:
        logger.error(f"call_swagger_api error: {str(e)}", exc_info=True)
        if isinstance(e, ToolException):
            raise e
        else:
            raise ToolException(str(e), code="CALL_SWAGGER_API_ERROR")
