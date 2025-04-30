class ToolException(Exception):
    """MCP Tool 异常基类"""

    def __init__(self, message: str, code: str = "TOOL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)
