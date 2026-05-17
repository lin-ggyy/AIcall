import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("SILICONFLOW_API_KEY"),#去 https://www.siliconflow.cn/ 注册获取，硅基流动有免费的嵌入模型
    base_url="https://api.siliconflow.cn/v1/"
)

# Embedding 模型：把文本转成向量
EMBEDDING_MODEL = "BAAI/bge-large-zh-v1.5"


def get_embedding(text: str) -> list[float]:
    """把一段文本转成向量（list of float）"""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """批量转换，一次处理多段文本"""
    embeddings = []
    for text in texts:
        embeddings.append(get_embedding(text))
    return embeddings
