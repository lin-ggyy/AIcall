import json
import logging
from llm_api import client
from rag.vector_store import search
from logger_config import setup_logging, CustomAdapter
import urllib.request
import urllib.parse


logger = setup_logging("agent.log")
adapter = CustomAdapter(logger, {})

# 告诉 LLM 有哪些工具可以用
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "从本地知识库检索公司内部文档片段。当用户问到公司制度、规定、流程、报销、出差等需要查阅内部资料的问题时，必须使用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "检索关键词或问题"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询城市天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "要查询天气的城市名称"
                    }
                },
                "required": ["city"]
            }
        }
    }
]

def get_weather(city: str) -> str:
    """通过 wttr.in 免费 API 查询城市天气"""
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "Agent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        current = data["current_condition"][0]
        location = data["nearest_area"][0]

        weather_desc = current["weatherDesc"][0]["value"]
        temp_c = current["temp_C"]
        humidity = current["humidity"]
        wind_speed = current["windspeedKmph"]
        area = location["areaName"][0]["value"]
        country = location["country"][0]["value"]

        return (
            f"城市：{area}, {country}\n"
            f"天气：{weather_desc}\n"
            f"温度：{temp_c}°C\n"
            f"湿度：{humidity}%\n"
            f"风速：{wind_speed} km/h"
        )
    except Exception as e:
        return f"查询天气失败：{e}"



def execute_tool(name: str, arguments: dict) -> str:
    """执行工具调用，返回结果字符串"""
    if name == "search_knowledge_base":
        query = arguments.get("query", "")
        docs = search(query, top_k=3)
        if not docs:
            return "知识库中未找到相关内容。"
        return "\n\n---\n\n".join([f"【资料{i+1}】{doc}" for i, doc in enumerate(docs)])
    elif name == "get_weather":
        city = arguments.get("city", "")
        if not city:
            return "错误：缺少城市名"
        return get_weather(city)
    return f"未知工具: {name}"


def agent_chat(user_prompt: str) -> str:
    """
    Agent 核心循环：
    1. 把用户问题和工具列表发给 LLM
    2. 如果 LLM 要调工具 → 执行 → 结果追加到对话 → 再发给 LLM
    3. 如果 LLM 直接回复 → 返回结果
    """
    messages = [{"role": "user", "content": user_prompt}]

    # 最多循环 5 轮，防止无限调用
    for _ in range(5):
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=TOOLS
        )

        msg = response.choices[0].message

        # 情况 1：LLM 直接回复（不需要调工具）
        if msg.content and not msg.tool_calls:
            return msg.content

        # 情况 2：LLM 要调工具
        if msg.tool_calls:
            # 把 LLM 的工具调用请求加入对话
            messages.append(msg)

            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                result = execute_tool(name, args)
                adapter.info(f"Agent 调用工具: {name}({args})")

                # 把工具执行结果加入对话
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

    return "Agent 达到最大轮次，未能完成回答。"
