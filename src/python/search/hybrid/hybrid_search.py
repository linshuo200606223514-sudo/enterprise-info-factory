"""混合搜索模块 - BM25 + 向量双路检索 + Score 融合"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from storage.document import Document, CorpusStats
from indexer.bm25_indexer import BM25Indexer
from indexer.vector_indexer import VectorIndexer


@dataclass
class SearchResult:
    """搜索结果"""
    url: str
    title: str
    content: str
    domain: str
    bm25_score: float = 0.0
    vector_score: float = 0.0
    fused_score: float = 0.0
    quality_score: float = 0.0
    is_valid: bool = True


class HybridSearcher:
    """混合搜索器 - BM25 * 0.5 + Cosine * 0.5"""

    def __init__(
        self,
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5,
        quality_weight_valid: float = 0.40,
        quality_weight_quality: float = 0.30,
        quality_weight_diversity: float = 0.15,
        quality_weight_freshness: float = 0.15,
    ):
        """
        Args:
            bm25_weight: BM25 分数权重
            vector_weight: 向量分数权重
            quality_weight_*: 四因子评分权重
        """
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
        self.quality_weights = {
            "valid": quality_weight_valid,
            "quality": quality_weight_quality,
            "diversity": quality_weight_diversity,
            "freshness": quality_weight_freshness,
        }

        self.bm25_indexer = BM25Indexer()
        self.vector_indexer = VectorIndexer()
        self.documents: Dict[str, Document] = {}
        self.corpus_stats: Optional[CorpusStats] = None

    def build_index(self, documents: List[Document]) -> None:
        """构建双索引"""
        # 保存文档
        self.documents = {doc.url: doc for doc in documents}

        # 构建 BM25 索引
        self.bm25_indexer.build_index(documents)

        # 构建向量索引
        self.vector_indexer.build_index(documents)

        # 更新语料统计
        self.corpus_stats = CorpusStats()
        self.corpus_stats.update_from_documents(documents)

    def add_documents(self, documents: List[Document]) -> None:
        """增量添加文档"""
        for doc in documents:
            if doc.url not in self.documents:
                self.documents[doc.url] = doc

        # 增量构建索引（简单重新构建）
        self.build_index(list(self.documents.values()))

    def search(
        self,
        query: str,
        top_k: int = 20,
        include_content: bool = True,
    ) -> List[SearchResult]:
        """
        混合检索主入口

        Args:
            query: 搜索 query
            top_k: 返回 top k 结果
            include_content: 是否包含正文内容

        Returns:
            List[SearchResult]: 融合后的结果
        """
        # 双路检索
        bm25_scores = self.bm25_indexer.get_scores(query)
        vector_scores = self.vector_indexer.get_scores(query) if self.vector_indexer else {}

        # 归一化
        bm25_norm = BM25Indexer.normalize_scores(bm25_scores)
        vector_norm = VectorIndexer.normalize_scores(vector_scores) if vector_scores else {}

        # 获取所有 URL
        all_urls = set(bm25_norm.keys()) | set(vector_norm.keys())

        # Score 融合
        fused_scores: Dict[str, float] = {}
        for url in all_urls:
            bm25_s = bm25_norm.get(url, 0.0)
            vec_s = vector_norm.get(url, 0.0)
            fused_scores[url] = self.bm25_weight * bm25_s + self.vector_weight * vec_s

        # 排序
        sorted_urls = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # 构建结果
        results = []
        for url, fused_score in sorted_urls:
            doc = self.documents.get(url)
            if not doc:
                continue

            # 计算质量分
            quality_score = self._calc_quality_score(doc)

            result = SearchResult(
                url=doc.url,
                title=doc.title,
                content=doc.content[:500] if include_content else "",
                domain=doc.domain,
                bm25_score=bm25_norm.get(url, 0.0),
                vector_score=vector_norm.get(url, 0.0),
                fused_score=fused_score,
                quality_score=quality_score,
                is_valid=doc.is_valid,
            )
            results.append(result)

        return results

    def _calc_quality_score(self, doc: Document) -> float:
        """计算内容质量分数（四因子）"""
        if not self.corpus_stats:
            return 0.5

        # 可用率 (40%)
        valid_score = 1.0 if doc.is_valid else 0.0

        # 内容质量 (30%) - 正文长度归一化到 2000 字满分
        if doc.content_length < 100:
            quality_score = 0.0
        else:
            quality_score = min(doc.content_length / 2000, 1.0)

        # 域名多样性 (15%)
        diversity_score = self.corpus_stats.domain_diversity_score(doc.domain)

        # 新鲜度 (15%) - 365 天内新鲜
        days_old = (self.corpus_stats.avg_fetched_days_ago or 0)
        freshness_score = max(0, 1 - days_old / 365)

        # 综合评分
        total_score = (
            valid_score * self.quality_weights["valid"] +
            quality_score * self.quality_weights["quality"] +
            diversity_score * self.quality_weights["diversity"] +
            freshness_score * self.quality_weights["freshness"]
        )
        return total_score

    def search_with_raw_results(
        self,
        query: str,
        raw_results: List[dict],
        top_k: int = 20,
    ) -> List[SearchResult]:
        """
        合并原始搜索结果（如 Tavily 结果）+ 自建索引的混合搜索

        Args:
            query: 搜索 query
            raw_results: 原始搜索结果 [(url, title, score, content), ...]
            top_k: 返回 top k 结果

        Returns:
            List[SearchResult]: 融合后的结果
        """
        # 转换原始结果为 Document
        documents = []
        for r in raw_results:
            doc = Document(
                url=r.get("url", ""),
                title=r.get("title", ""),
                content=r.get("content", ""),
                domain=r.get("domain", ""),
                is_valid=True,
            )
            documents.append(doc)

        # 构建索引
        self.build_index(documents)

        # 执行搜索
        return self.search(query, top_k)


class HybridSearchPipeline:
    """混合搜索流水线 - 支持多关键词并行搜索"""

    def __init__(
        self,
        hybrid_searcher: HybridSearcher,
        max_workers: int = 10,
    ):
        self.hybrid_searcher = hybrid_searcher
        self.max_workers = max_workers

    def parallel_search(
        self,
        keyword: str,
        search_dimensions: Dict[str, List[str]],
    ) -> Dict[str, List[SearchResult]]:
        """
        多关键词并行搜索

        Args:
            keyword: 行业关键词
            search_dimensions: 搜索维度配置 {
                "main": ["关键词1", "关键词2", ...],
                "news": [...],
            }

        Returns:
            Dict[str, List[SearchResult]]: 维度 -> 结果列表
        """
        import concurrent.futures

        def search_dimension(dim_name: str, keywords: List[str]) -> Tuple[str, List[SearchResult]]:
            all_results = []
            for kw in keywords:
                full_kw = kw.format(keyword=keyword)
                results = self.hybrid_searcher.search(full_kw, top_k=20)
                all_results.extend(results)

            # URL 去重，保留最高分
            url_scores: Dict[str, SearchResult] = {}
            for r in all_results:
                if r.url in url_scores:
                    if r.fused_score > url_scores[r.url].fused_score:
                        url_scores[r.url] = r
                else:
                    url_scores[r.url] = r

            return dim_name, list(url_scores.values())

        # 并行执行
        dim_results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(search_dimension, dim_name, kws): dim_name
                for dim_name, kws in search_dimensions.items()
            }
            for future in concurrent.futures.as_completed(futures):
                dim_name, results = future.result()
                dim_results[dim_name] = results

        return dim_results