import asyncio
import os
import sys



# 把项目根目录加到 sys.path，确保能 import rag 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from rag.vector_store import search
from rag.document import load_and_split
from rag.vector_store import store_documents, reset_collection
from agent import agent_chat
from llm_api import call_ai

# 服务启动时加载文档
docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")
if os.path.isdir(docs_dir):
    chunks = load_and_split(docs_dir)
    if chunks:
        reset_collection()
        store_documents(chunks)

# 创建 MCP Server
server = Server("ai_call_mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """告诉客户端有哪些工具可用"""
    return [
        Tool(
            name="search_knowledge_base",
            description="从本地知识库检索相关文档片段。当用户询问需要查阅公司内部资料、制度、规定等问题时使用。",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "要检索的问题或关键词"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="ask_ai",
            description="直接向 DeepSeek 大模型提问，用于知识库无法覆盖的通用问题。",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "要问的问题"
                    }
                },
                "required": ["prompt"]
            }
        ),
        Tool(
            name="reload_knowledge_base",
            description="重新加载知识库文档，不需要重启服务。",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """处理客户端的工具调用请求"""
    if name == "search_knowledge_base":
        query = arguments.get("query", "")
        if not query:
            return [TextContent(type="text", text="错误：缺少查询参数")]
        docs = search(query, top_k=3)
        result = "\n\n---\n\n".join([f"【资料{i+1}】{doc}" for i, doc in enumerate(docs)])
        return [TextContent(type="text", text=result)]

    elif name == "ask_ai":
        prompt = arguments.get("prompt", "")
        if not prompt:
            return [TextContent(type="text", text="错误：缺少问题参数")]
        result = call_ai(prompt)
        return [TextContent(type="text", text=result)]

    elif name == "reload_knowledge_base":
        chunks = load_and_split(docs_dir)
        if not chunks:
            return [TextContent(type="text", text="未找到任何文档")]
        reset_collection()
        store_documents(chunks)
        return [TextContent(type="text", text=f"重载完成，共 {len(chunks)} 个片段")]

    return [TextContent(type="text", text=f"未知工具: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
