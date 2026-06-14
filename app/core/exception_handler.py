from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.core.logger import logger


class AppBaseException(Exception):
    def __init__(self, message: str, code: int = 400, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}


class NotFoundException(AppBaseException):
    def __init__(self, message: str = "资源不存在", details: dict = None):
        super().__init__(message, status.HTTP_404_NOT_FOUND, details)


class BadRequestException(AppBaseException):
    def __init__(self, message: str = "请求参数错误", details: dict = None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, details)


class UnauthorizedException(AppBaseException):
    def __init__(self, message: str = "未授权访问", details: dict = None):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, details)


class ForbiddenException(AppBaseException):
    def __init__(self, message: str = "无权限访问", details: dict = None):
        super().__init__(message, status.HTTP_403_FORBIDDEN, details)


class ConflictException(AppBaseException):
    def __init__(self, message: str = "资源冲突", details: dict = None):
        super().__init__(message, status.HTTP_409_CONFLICT, details)


class BusinessException(AppBaseException):
    def __init__(self, message: str = "业务处理失败", code: int = 400, details: dict = None):
        super().__init__(message, code, details)


def register_exception_handlers(app):
    @app.exception_handler(AppBaseException)
    async def app_exception_handler(request: Request, exc: AppBaseException):
        logger.error(f"AppException: {exc.message}", extra={"details": exc.details})
        return JSONResponse(
            status_code=exc.code,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": getattr(request.state, "request_id", None)
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append(f"{field}: {error['msg']}")

        logger.warning(f"Validation error: {errors}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "message": "参数验证失败",
                "details": {"errors": errors},
                "request_id": getattr(request.state, "request_id", None)
            }
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.error(f"Database integrity error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "code": status.HTTP_409_CONFLICT,
                "message": "数据完整性冲突",
                "details": {},
                "request_id": getattr(request.state, "request_id", None)
            }
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
        logger.error(f"Database error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "数据库操作失败",
                "details": {},
                "request_id": getattr(request.state, "request_id", None)
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "服务器内部错误",
                "details": {},
                "request_id": getattr(request.state, "request_id", None)
            }
        )
