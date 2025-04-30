class SwaggerServiceError(Exception):
    """Swagger服务异常"""

    def __init__(self, message: str, cause: Exception = None):
        self.message = message
        self.cause = cause
        super().__init__(f"{message}: {str(cause) if cause else ''}")
