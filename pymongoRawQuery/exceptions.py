class ParameterErrorFailed(Exception):
    """验证器错误类"""

    def __init__(self, detail):
        self.detail = detail


class LogicErrorFailed(Exception):
    """logic错误类"""

    def __init__(self, detail):
        self.detail = detail
