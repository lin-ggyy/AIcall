import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from ai_request import AIRequest
from logger_config import setup_logging, CustomAdapter
from llm_api import call_ai


# ==================== 日志初始化 ====================
setup_logging("api.log")
root_logger = logging.getLogger()
adapter = CustomAdapter(root_logger, {})

# 压低 slowapi 自己的日志，不让它往外冒
logging.getLogger("slowapi").propagate = False


# ==================== FastAPI 应用 ====================
app = FastAPI()


# ==================== 速率限制 ====================
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


# ==================== 异常处理 ====================
@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    client_ip = request.client.host if request.client else "unknown"
    adapter.warning(f"触发速率限制", extra={"ip": client_ip})
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "请求太频繁了，请稍后再试"}
    )


# ==================== 业务接口 ====================
@app.post("/ai_call")
@limiter.limit("5/minute")
async def ai_call_endpoint(payload: AIRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"

    # 1. 校验 prompt 是否存在
    if not payload.prompt:
        adapter.warning("缺少提示词参数", extra={"ip": client_ip})
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "缺少提示词参数"}
        )

    # 2. 调用大模型
    try:
        result = await run_in_threadpool(call_ai, payload.prompt)
        adapter.info(f"prompt: {payload.prompt} | response: {result}", extra={"ip": client_ip})
        return {"code": 200, "message": result}
    except Exception as e:
        adapter.error(str(e), extra={"ip": client_ip})
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": str(e)}
        )


# ==================== 启动入口 ====================
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
