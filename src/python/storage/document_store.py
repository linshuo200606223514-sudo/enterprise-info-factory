"""文档存储模块 - 负责文档的持久化和加载"""
import json
import os
from typing import List, Optional
from datetime import datetime

from .document import Document, CorpusStats


class DocumentStore:
    """文档存储 - 支持 JSON 文件持久化"""

    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            storage_dir = os.path.join(root, "data", "search_cache")
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def save_documents(self, documents: List[Document], namespace: str = "default") -> None:
        """保存文档列表到 JSON 文件"""
        filepath = self._get_filepath(namespace)
        data = {
            "saved_at": datetime.now().isoformat(),
            "count": len(documents),
            "documents": [doc.to_dict() for doc in documents]
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_documents(self, namespace: str = "default") -> List[Document]:
        """从 JSON 文件加载文档列表"""
        filepath = self._get_filepath(namespace)
        if not os.path.exists(filepath):
            return []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return [Document.from_dict(d) for d in data.get("documents", [])]
        except Exception as e:
            print(f"Failed to load documents from {filepath}: {e}")
            return []

    def add_document(self, document: Document, namespace: str = "default") -> None:
        """添加单个文档到存储（追加模式）"""
        documents = self.load_documents(namespace)
        existing_urls = {doc.url for doc in documents}
        if document.url not in existing_urls:
            documents.append(document)
            self.save_documents(documents, namespace)

    def get_document(self, url: str, namespace: str = "default") -> Optional[Document]:
        """根据 URL 获取文档"""
        documents = self.load_documents(namespace)
        for doc in documents:
            if doc.url == url:
                return doc
        return None

    def clear(self, namespace: str = "default") -> None:
        """清空指定 namespace 的所有文档"""
        filepath = self._get_filepath(namespace)
        if os.path.exists(filepath):
            os.remove(filepath)

    def _get_filepath(self, namespace: str) -> str:
        """获取存储文件路径"""
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        safe_name = "".join(c for c in namespace if c in allowed)
        return os.path.join(self.storage_dir, f"docs_{safe_name}.json")

    def load_corpus_stats(self, namespace: str = "default") -> CorpusStats:
        """加载语料统计信息"""
        documents = self.load_documents(namespace)
        stats = CorpusStats()
        stats.update_from_documents(documents)
        return stats


class InMemoryDocumentStore:
    """内存文档存储 - 用于小规模测试或缓存"""

    def __init__(self):
        self.documents: List[Document] = []

    def save_documents(self, documents: List[Document], namespace: str = "default") -> None:
        """保存到内存（不持久化）"""
        self.documents = documents

    def load_documents(self, namespace: str = "default") -> List[Document]:
        """从内存加载"""
        return self.documents

    def add_document(self, document: Document, namespace: str = "default") -> None:
        """添加文档"""
        existing_urls = {doc.url for doc in self.documents}
        if document.url not in existing_urls:
            self.documents.append(document)

    def get_document(self, url: str, namespace: str = "default") -> Optional[Document]:
        """根据 URL 获取文档"""
        for doc in self.documents:
            if doc.url == url:
                return doc
        return None

    def clear(self, namespace: str = "default") -> None:
        """清空"""
        self.documents = []

    def load_corpus_stats(self, namespace: str = "default") -> CorpusStats:
        """获取语料统计"""
        stats = CorpusStats()
        stats.update_from_documents(self.documents)
        return stats
