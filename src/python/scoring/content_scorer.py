"""四因子评分模块 - 可用率/内容质量/域名多样性/新鲜度"""
from datetime import datetime
from typing import Dict, Optional

from storage.document import Document, CorpusStats


class ContentScorer:
    """内容可用性评分器"""

    # 权重配置
    WEIGHTS = {
        "valid": 0.40,       # 可用率
        "quality": 0.30,     # 内容质量
        "diversity": 0.15,   # 域名多样性
        "freshness": 0.15,   # 新鲜度
    }

    def __init__(self, weights: Dict[str, float] = None):
        """初始化评分器"""
        if weights:
            self.weights = {**self.WEIGHTS, **weights}
        else:
            self.weights = self.WEIGHTS

    def score(self, document: Document, corpus_stats: Optional[CorpusStats] = None) -> float:
        """
        计算综合评分

        Args:
            document: 文档
            corpus_stats: 语料统计信息

        Returns:
            float: 综合评分 [0, 1]
        """
        valid_score = self.calc_valid_score(document)
        quality_score = self.calc_quality_score(document)
        diversity_score = self.calc_diversity_score(document, corpus_stats)
        freshness_score = self.calc_freshness_score(document)

        total_score = (
            valid_score * self.weights["valid"] +
            quality_score * self.weights["quality"] +
            diversity_score * self.weights["diversity"] +
            freshness_score * self.weights["freshness"]
        )
        return total_score

    def calc_valid_score(self, document: Document) -> float:
        """可用率：非乱码、非导航内容"""
        return 1.0 if document.is_valid else 0.0

    def calc_quality_score(self, document: Document) -> float:
        """内容质量：页面充实度、正文长度"""
        if document.content_length < 100:
            return 0.0
        # 归一化到 [0, 1]，正文>2000字为满分
        return min(document.content_length / 2000, 1.0)

    def calc_diversity_score(self, document: Document, corpus_stats: Optional[CorpusStats] = None) -> float:
        """域名多样性：同域名文档越少越好"""
        if not corpus_stats:
            return 0.5  # 无统计信息时返回中性分数
        return corpus_stats.domain_diversity_score(document.domain)

    def calc_freshness_score(self, document: Document, max_age_days: int = 365) -> float:
        """新鲜度：越新越好"""
        days_old = (datetime.now() - document.fetched_at).days
        return max(0, 1 - days_old / max_age_days)

    def score_batch(
        self,
        documents: list,
        corpus_stats: Optional[CorpusStats] = None,
    ) -> Dict[str, float]:
        """
        批量评分

        Args:
            documents: 文档列表
            corpus_stats: 语料统计信息

        Returns:
            Dict[str, float]: url -> score
        """
        if not corpus_stats:
            corpus_stats = CorpusStats()
            corpus_stats.update_from_documents(documents)

        return {
            doc.url: self.score(doc, corpus_stats)
            for doc in documents
        }

    def get_score_breakdown(
        self,
        document: Document,
        corpus_stats: Optional[CorpusStats] = None,
    ) -> Dict[str, float]:
        """
        获取评分明细

        Returns:
            Dict with 'total' and each factor
        """
        return {
            "total": self.score(document, corpus_stats),
            "valid": self.calc_valid_score(document),
            "quality": self.calc_quality_score(document),
            "diversity": self.calc_diversity_score(document, corpus_stats),
            "freshness": self.calc_freshness_score(document),
        }


class QualityFilter:
    """质量过滤器 - 基于评分过滤低质量结果"""

    def __init__(
        self,
        min_valid_ratio: float = 0.6,
        min_quality_score: float = 0.4,
    ):
        """
        Args:
            min_valid_ratio: 最小有效结果比例
            min_quality_score: 最小质量分数
        """
        self.min_valid_ratio = min_valid_ratio
        self.min_quality_score = min_quality_score

    def filter(self, documents: list, scores: Dict[str, float]) -> list:
        """
        过滤低质量文档

        Args:
            documents: 文档列表
            scores: url -> quality score

        Returns:
            过滤后的文档列表
        """
        # 按分数排序
        sorted_docs = sorted(
            [(doc, scores.get(doc.url, 0)) for doc in documents],
            key=lambda x: x[1],
            reverse=True
        )

        # 取最高分的结果
        if not sorted_docs:
            return []

        top_score = sorted_docs[0][1]
        threshold = top_score * self.min_valid_ratio

        filtered = [
            doc for doc, score in sorted_docs
            if score >= threshold and score >= self.min_quality_score
        ]

        return filtered