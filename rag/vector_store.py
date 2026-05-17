import os
import chromadb
from chromadb import EmbeddingFunction
from rag.embedding import get_embedding


class DeepSeekEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: list[str]) -> list[list[float]]:
        return [get_embedding(text) for text in input]


DB_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db")

chroma_client = chromadb.PersistentClient(path=DB_PATH)


def get_or_create_collection(name: str = "knowledge_base"):
    """获取已有的集合，没有则创建"""
    ef = DeepSeekEmbeddingFunction()
    try:
        return chroma_client.get_collection(name)
    except Exception:
        return chroma_client.create_collection(name, embedding_function=ef)


def store_documents(chunks: list[dict], collection_name: str = "knowledge_base"):
    """
    把文档片段存进向量数据库（先删再建，保证数据最新）
    chunks 就是 document.py 的 load_and_split() 返回的列表
    """
    ef = DeepSeekEmbeddingFunction()
    try:
        chroma_client.delete_collection(collection_name)
    except Exception:
        pass
    collection = chroma_client.create_collection(collection_name, embedding_function=ef)

    ids = []
    documents = []
    metadatas = []

    for chunk in chunks:
        chunk_id = f"{chunk['title']}_chunk{chunk['chunk_index']}"
        ids.append(chunk_id)
        documents.append(chunk["content"])
        metadatas.append({
            "title": chunk["title"],
            "chunk_index": chunk["chunk_index"]
        })

    if ids:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)


def search(query: str, top_k: int = 3, collection_name: str = "knowledge_base") -> list[str]:
    """
    根据用户问题检索最相关的 top_k 个文档片段
    返回: ["片段1内容", "片段2内容", "片段3内容"]
    """
    collection = get_or_create_collection(collection_name)
    query_embedding = get_embedding(query)
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
    return results["documents"][0]


def reset_collection(collection_name: str = "knowledge_base"):
    """清空集合，重新导入文档前调用"""
    try:
        chroma_client.delete_collection(collection_name)
    except Exception:
        pass
