import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.concurrency import iterate_in_threadpool
from app.core.logger import logger


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        with logger.contextualize(request_id=request_id):
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = getattr(request.state, "request_id", "N/A")

        logger.info(
            f"Request started: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        response = await call_next(request)

        process_time = (time.time() - start_time) * 1000
        formatted_process_time = f"{process_time:.2f}"

        response_body = [section async for section in response.body_iterator]
        response.body_iterator = iterate_in_threadpool(iter(response_body))
        response_body_str = b"".join(response_body).decode("utf-8", errors="replace")

        if process_time > 1000:
            logger.warning(
                f"Slow request: {request.method} {request.url.path} "
                f"status={response.status_code} duration={formatted_process_time}ms"
            )
        else:
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"status={response.status_code} duration={formatted_process_time}ms"
            )

        if response.status_code >= 400:
            logger.error(
                f"Request error: {request.method} {request.url.path} "
                f"status={response.status_code} body={response_body_str[:500]}"
            )

        response.headers["X-Process-Time"] = formatted_process_time
        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.request_counts = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        current_minute = int(time.time() // 60)
        key = f"{client_ip}:{current_minute}"

        count = self.request_counts.get(key, 0)
        if count >= 100:
            return Response(
                content='{"detail": "Too many requests"}',
                status_code=429,
                media_type="application/json"
            )

        self.request_counts[key] = count + 1

        for old_key in list(self.request_counts.keys()):
            old_minute = int(old_key.split(":")[-1])
            if current_minute - old_minute > 1:
                del self.request_counts[old_key]

        return await call_next(request)
