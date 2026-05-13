"""
WorldQuant Brain API 异常类

定义统一的异常层次结构，便于错误处理和区分
"""


class WQAPIError(Exception):
    """WorldQuant API 错误基类"""

    def __init__(self, message: str, status_code: int = None, response_text: str = None):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(self.message)

    def __str__(self):
        if self.status_code:
            return f"[HTTP {self.status_code}] {self.message}"
        return self.message


class WQAuthError(WQAPIError):
    """认证错误

    触发场景：
    - 用户名/密码错误
    - 会话过期
    - 认证失败
    """
    pass


class WQRateLimitError(WQAPIError):
    """限流错误

    触发场景：
    - HTTP 429 Too Many Requests
    - 模拟次数超限
    """

    def __init__(self, message: str, retry_after: int = 60, **kwargs):
        self.retry_after = retry_after
        super().__init__(message, **kwargs)

    def __str__(self):
        return f"[限流] {self.message} - 请等待 {self.retry_after} 秒后重试"


class WQNotFoundError(WQAPIError):
    """资源不存在错误

    触发场景：
    - HTTP 404
    - Alpha ID 不存在
    """
    pass


class WQServerError(WQAPIError):
    """服务器错误

    触发场景：
    - HTTP 500 Internal Server Error
    - HTTP 503 Service Unavailable
    """
    pass


class WQValidationError(WQAPIError):
    """验证错误

    触发场景：
    - HTTP 400 Bad Request
    - Alpha 表达式语法错误
    - 参数验证失败
    """
    pass


class WQSimulationError(WQAPIError):
    """模拟错误

    触发场景：
    - 模拟失败
    - 模拟超时
    - 检查失败
    """

    def __init__(self, message: str, alpha_id: str = None, check_results: list = None, **kwargs):
        self.alpha_id = alpha_id
        self.check_results = check_results or []
        super().__init__(message, **kwargs)