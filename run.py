import os
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
from contextlib import asynccontextmanager

from rag.document import load_and_split
from rag.vector_store import store_documents, search, reset_collection
from agent import agent_chat


# ==================== 日志初始化 ====================
setup_logging("api.log")
root_logger = logging.getLogger()
adapter = CustomAdapter(root_logger, {})

# 压低 slowapi 自己的日志，不让它往外冒
logging.getLogger("slowapi").propagate = False

# ==================== 启动时自动加载文档 ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务启动时，把 documents 目录下的文件全部导入向量数据库"""
    import os
    docs_dir = os.path.join(os.path.dirname(__file__), "documents")
    if os.path.isdir(docs_dir):
        chunks = load_and_split(docs_dir)
        if chunks:
            reset_collection()
            store_documents(chunks)
            adapter.info(f"文档加载完成，共 {len(chunks)} 个片段")
        else:
            adapter.warning("documents 目录为空，没有加载任何文档")
    else:
        adapter.warning("documents 目录不存在")
    yield
    # yield 后面可以写关闭服务时的清理逻辑，目前不需要

# ==================== FastAPI 应用 ====================
app = FastAPI(lifespan=lifespan)


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

# ==================== RAG 接口 ====================
@app.post("/rag_call")
@limiter.limit("5/minute")
async def rag_call_endpoint(payload: AIRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"

    if not payload.prompt:
        adapter.warning("缺少提示词参数", extra={"ip": client_ip})
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "缺少提示词参数"}
        )

    try:
        # 1. 从知识库检索相关文档
        retrieved_docs = search(payload.prompt, top_k=3)

        # 2. 拼接增强版 prompt
        context = "\n\n".join([
            f"【参考资料{i+1}】{doc}"
            for i, doc in enumerate(retrieved_docs)
        ])
        enhanced_prompt = f"请根据以下参考资料回答问题。\n\n{context}\n\n用户问题：{payload.prompt}\n\n如果参考资料无法回答问题，请如实告知。\n"

        # 3. 发给 LLM
        result = await run_in_threadpool(call_ai, enhanced_prompt)

        adapter.info(f"prompt: {payload.prompt} | 检索到 {len(retrieved_docs)} 条资料 | response: {result}", extra={"ip": client_ip})
        return {"code": 200, "message": result, "sources": [doc[:50] + "..." for doc in retrieved_docs]}

    except Exception as e:
        adapter.error(str(e), extra={"ip": client_ip})
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": str(e)}
        )
    
@app.post("/reload")
async def reload_documents():
    """重新加载文档，不需要重启服务"""
    try:
        docs_dir = os.path.join(os.path.dirname(__file__), "documents")
        if not os.path.isdir(docs_dir):
            return {"code": 500, "message": "documents 目录不存在"}
        chunks = load_and_split(docs_dir)
        if not chunks:
            return {"code": 500, "message": "未找到任何文档"}
        reset_collection()
        store_documents(chunks)
        adapter.info(f"文档热重载完成，共 {len(chunks)} 个片段")
        return {"code": 200, "message": f"重载完成，共 {len(chunks)} 个片段"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"code": 500, "message": str(e)})

# ==================== Agent 接口 ====================
@app.post("/agent_call")
@limiter.limit("5/minute")
async def agent_call_endpoint(payload: AIRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"

    if not payload.prompt:
        adapter.warning("缺少提示词参数", extra={"ip": client_ip})
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "缺少提示词参数"}
        )

    try:
        result = await run_in_threadpool(agent_chat, payload.prompt)
        adapter.info(f"Agent prompt: {payload.prompt} | response: {result}", extra={"ip": client_ip})
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
