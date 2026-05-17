import os


def load_documents(directory: str) -> list[dict]:
    """
    加载目录下所有 .txt 和 .md 文件
    返回: [{"title": "文件名", "content": "文件内容"}, ...]
    """
    docs = []
    for filename in os.listdir(directory):
        if filename.endswith((".txt", ".md")):
            filepath = os.path.join(directory, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            docs.append({"title": filename, "content": content})
    return docs


def split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    把长文本切成固定大小的块，相邻块之间有 overlap 字重叠
    例如 chunk_size=500, overlap=50:
      块1: 0~500字
      块2: 450~950字   ← 和块1重叠50字
      块3: 900~1400字  ← 和块2重叠50字
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def load_and_split(directory: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """
    加载 + 切分，一步完成
    返回: [{"title": "文件名", "chunk_index": 0, "content": "片段内容"}, ...]
    """
    documents = load_documents(directory)
    result = []
    for doc in documents:
        chunks = split_text(doc["content"], chunk_size, overlap)
        for i, chunk in enumerate(chunks):
            result.append({
                "title": doc["title"],
                "chunk_index": i,
                "content": chunk
            })
    return result
