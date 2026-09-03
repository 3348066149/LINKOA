"""自定义业务异常 + 全局异常处理器，统一返回 {code, msg, data:null}"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("linkoa")


class BusinessException(Exception):
    """业务异常：code + msg，由全局处理器统一包装返回"""

    def __init__(self, code: int = 400, msg: str = ""):
        self.code = code
        self.msg = msg
        super().__init__(msg)


def ok(data=None):
    """统一成功响应体"""
    return {"code": 200, "msg": "", "data": data}


def fail(code: int, msg: str):
    """统一失败响应体"""
    return {"code": code, "msg": msg, "data": None}


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器：业务异常 / 参数校验异常 / 未捕获异常"""

    @app.exception_handler(BusinessException)
    async def business_exception_handler(request: Request, exc: BusinessException):
        # HTTP 状态码固定 200，业务码放在 body.code 中，与统一返回格式约定一致
        return JSONResponse(status_code=200, content=fail(exc.code, exc.msg))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # 入参校验失败按 400 处理，不暴露内部字段细节
        return JSONResponse(status_code=200, content=fail(400, "请求参数错误"))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # 未捕获异常返回 500，记录日志但不向客户端暴露堆栈
        logger.exception("Unhandled exception: %s %s", request.method, request.url.path)
        return JSONResponse(status_code=200, content=fail(500, "服务器内部错误"))
