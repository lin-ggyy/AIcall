import re
import logging
from openai import OpenAI
from logger_config import setup_logging, CustomAdapter

# 初始化日志
logger = setup_logging("llm_test.log")
adapter = CustomAdapter(logger, {})

# 创建 OpenAI 客户端，指向 deepseek 的接口
client = OpenAI(
    api_key="sk-82d487a06efd4346a836cc91cf60d0d3",   # ← 去 https://platform.deepseek.com 注册获取
    base_url="https://api.deepseek.com"
)

# 预编译正则，用于去除 Markdown 格式
TITLE_PATTERN = re.compile(r'^#{1,6}\s+', re.MULTILINE)
ORDERED_LIST_PATTERN = re.compile(r'^\d+\.\s+', re.MULTILINE)
UNORDERED_LIST_PATTERN = re.compile(r'^[-*+]\s+', re.MULTILINE)


def markdown_to_plain_text(md_text: str) -> str:
    """把 Markdown 转成纯文本"""
    text = TITLE_PATTERN.sub('', md_text)
    text = ORDERED_LIST_PATTERN.sub('', text)
    text = UNORDERED_LIST_PATTERN.sub('', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    return text


def call_ai(prompt: str) -> str:
    """调用大模型，返回回复内容"""
    try:
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        adapter.error(f"调用大模型api出错: {e}")
        return f"调用大模型api出错: {e}"
