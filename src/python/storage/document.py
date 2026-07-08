"""文档数据模型"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse


@dataclass
class Document:
    """搜索文档数据模型"""
    url: str
    title: str
    content: str
    domain: str = ""
    fetched_at: datetime = field(default_factory=datetime.now)
    content_length: int = 0
    is_valid: bool = True  # 非乱码、非导航
    is_garbled: bool = False
    is_navigation: bool = False
    embedding: Optional[list] = None  # 向量

    def __post_init__(self):
        if not self.domain:
            self.domain = self._extract_domain(self.url)
        if self.content_length == 0:
            self.content_length = len(self.content)

    @staticmethod
    def _extract_domain(url: str) -> str:
        """从URL提取域名"""
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ""

    @staticmethod
    def is_garbled_text(text: str) -> bool:
        """检测乱码 - 统计 `` 和 `?` 字符比例"""
        if not text or len(text) == 0:
            return False
        # 控制字符检测
        control_count = sum(1 for c in text if ord(c) < 32 and c not in '\t\n\r')
        # 问号异常检测（非中英文的 ? 可能是乱码）
        question_marks = text.count('?')
        if len(text) > 0 and (control_count / len(text) > 0.05 or question_marks / len(text) > 0.05):
            return True
        return False

    @staticmethod
    def is_navigation_content(content: str) -> bool:
        """检测导航内容 - 基于URL链接模式和常见导航路径"""
        if not content:
            return False
        # URL链接模式 = 导航
        if '](https://' in content:
            return True
        nav_patterns = ['](/', 'tag-', 'article/', 'category/']
        nav_count = sum(content.count(p) for p in nav_patterns)
        if nav_count > 3:
            return True
        if len(content) > 0 and nav_count / len(content) > 0.05:
            return True
        return False

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "domain": self.domain,
            "fetched_at": self.fetched_at.isoformat(),
            "content_length": self.content_length,
            "is_valid": self.is_valid,
            "is_garbled": self.is_garbled,
            "is_navigation": self.is_navigation,
            "embedding": self.embedding,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Document":
        """从字典反序列化"""
        fetched_at = d.get("fetched_at")
        if isinstance(fetched_at, str):
            fetched_at = datetime.fromisoformat(fetched_at)
        return cls(
            url=d["url"],
            title=d["title"],
            content=d["content"],
            domain=d.get("domain", ""),
            fetched_at=fetched_at or datetime.now(),
            content_length=d.get("content_length", 0),
            is_valid=d.get("is_valid", True),
            is_garbled=d.get("is_garbled", False),
            is_navigation=d.get("is_navigation", False),
            embedding=d.get("embedding"),
        )


@dataclass
class CorpusStats:
    """语料统计信息 - 用于评分计算"""
    total_count: int = 0
    domain_counts: dict = field(default_factory=dict)  # domain -> count
    avg_content_length: float = 0.0
    avg_fetched_days_ago: float = 0.0

    def update_from_documents(self, documents: list):
        """从文档列表更新统计信息"""
        self.total_count = len(documents)
        self.domain_counts = {}
        total_length = 0
        total_days = 0

        now = datetime.now()
        for doc in documents:
            domain = doc.domain or "unknown"
            self.domain_counts[domain] = self.domain_counts.get(domain, 0) + 1
            total_length += doc.content_length
            total_days += (now - doc.fetched_at).days

        self.avg_content_length = total_length / self.total_count if self.total_count > 0 else 0
        self.avg_fetched_days_ago = total_days / self.total_count if self.total_count > 0 else 0

    def domain_diversity_score(self, domain: str) -> float:
        """计算域名多样性得分 - 同域名文档越少越好"""
        count = self.domain_counts.get(domain, 1)
        # 超过5个同域名文档，多样性降为0
        return max(0, 1 - (count - 1) / 5)