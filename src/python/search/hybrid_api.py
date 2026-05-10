"""
混合搜索 API - 提供搜索接口

用法:
1. 先采集文档并构建索引:
   from search.hybrid_api import HybridSearchAPI
   api = HybridSearchAPI()
   api.crawl_and_index(urls)  # 爬取 URL
   api.save_index("my_index")  # 保存索引

2. 加载已有索引并搜索:
   api = HybridSearchAPI()
   api.load_index("my_index")
   results = api.search("餐饮 ERP 头部玩家")

3. 或者使用 pipeline 批量处理:
   from search.hybrid_api import HybridSearchPipeline
   pipeline = HybridSearchPipeline()
   pipeline.process_industry("餐饮行业")
"""
import json
import os
from typing import List, Dict, Optional, Tuple

from storage.document import Document, DocumentStore, CorpusStats
from crawler.hybrid_crawler import HybridCrawler
from indexer.bm25_indexer import BM25Indexer
from indexer.vector_indexer import VectorIndexer
from search.hybrid.hybrid_search import HybridSearcher, SearchResult
from scoring.content_scorer import ContentScorer


class HybridSearchAPI:
    """混合搜索 API"""

    def __init__(self, storage_dir: str = None):
        self.crawler = HybridCrawler(max_workers=10, timeout=30)
        self.bm25_indexer = BM25Indexer()
        self.vector_indexer = VectorIndexer()
        self.searcher: Optional[HybridSearcher] = None
        self.corpus_stats: Optional[CorpusStats] = None
        self.document_store = DocumentStore(storage_dir)
        self.documents: Dict[str, Document] = {}

    def crawl_and_index(self, urls: List[str], titles: List[str] = None) -> int:
        """
        爬取 URL 并构建索引

        Args:
            urls: URL 列表
            titles: 标题列表（可选）

        Returns:
            成功爬取的文档数量
        """
        print(f"Crawling {len(urls)} URLs...")
        documents = self.crawler.crawl(urls)

        # 如果提供了标题，覆盖
        if titles:
            for doc, title in zip(documents, titles):
                if title and not doc.is_garbled:
                    doc.title = title

        # 保存文档
        self.documents = {doc.url: doc for doc in documents}
        for doc in documents:
            self.document_store.add_document(doc)

        # 构建索引
        self._build_indexes()

        return len(documents)

    def _build_indexes(self):
        """构建 BM25 和向量索引"""
        if not self.documents:
            return

        documents = list(self.documents.values())

        print("Building BM25 index...")
        self.bm25_indexer.build_index(documents)

        print("Building vector index...")
        self.vector_indexer.build_index(documents)

        # 构建搜索器
        self.searcher = HybridSearcher()
        self.searcher.documents = self.documents
        self.searcher.bm25_indexer = self.bm25_indexer
        self.searcher.vector_indexer = self.vector_indexer
        self.searcher.corpus_stats = CorpusStats()
        self.searcher.corpus_stats.update_from_documents(documents)

    def search(self, query: str, top_k: int = 20) -> List[SearchResult]:
        """
        搜索

        Args:
            query: 查询词
            top_k: 返回数量

        Returns:
            List[SearchResult]
        """
        if not self.searcher:
            self.searcher = HybridSearcher()
            self.searcher.documents = self.documents
            self.searcher.bm25_indexer = self.bm25_indexer
            self.searcher.vector_indexer = self.vector_indexer
            self._build_indexes()

        return self.searcher.search(query, top_k)

    def save_index(self, namespace: str = "default") -> None:
        """保存索引到文件"""
        self.document_store.save_documents(list(self.documents.values()), namespace)

    def load_index(self, namespace: str = "default") -> int:
        """从文件加载索引"""
        documents = self.document_store.load_documents(namespace)
        self.documents = {doc.url: doc for doc in documents}
        self._build_indexes()
        return len(documents)


class HybridSearchPipeline:
    """混合搜索流水线 - 多关键词并行搜索"""

    def __init__(self):
        self.api = HybridSearchAPI()
        self.max_workers = 10

    def process_search_results(
        self,
        raw_results: List[dict],
        query: str,
        top_k: int = 20,
    ) -> List[SearchResult]:
        """
        处理原始搜索结果（如 Tavily 结果）并重新评分

        Args:
            raw_results: 原始搜索结果
            query: 查询词
            top_k: 返回数量

        Returns:
            List[SearchResult]: 重新评分后的结果
        """
        # 转换为 Document
        documents = []
        for r in raw_results:
            doc = Document(
                url=r.get("url", ""),
                title=r.get("title", ""),
                content=r.get("content", r.get("raw_content", "")),
                domain=r.get("domain", ""),
                is_valid=True,
                is_garbled=False,
                is_navigation=False,
            )
            documents.append(doc)

        # 构建索引
        self.api.documents = {doc.url: doc for doc in documents}
        self.api._build_indexes()

        # 搜索
        return self.api.search(query, top_k)

    def process_industry(
        self,
        industry_keyword: str,
        search_dimensions: Dict[str, List[str]],
        raw_results: Dict[str, List[dict]],
    ) -> Dict[str, List[SearchResult]]:
        """
        处理行业搜索（合并原始搜索结果 + 重新评分）

        Args:
            industry_keyword: 行业关键词
            search_dimensions: 搜索维度配置
            raw_results: 各维度的原始搜索结果 {
                "main": [...],
                "news": [...],
            }

        Returns:
            Dict[str, List[SearchResult]]: 各维度重评分后的结果
        """
        from collections import OrderedDict
        import concurrent.futures

        def process_dimension(dim_name: str, results: List[dict]) -> Tuple[str, List[SearchResult]]:
            # 构建查询关键词
            keywords = search_dimensions.get(dim_name, [])
            if keywords:
                query = keywords[0].format(keyword=industry_keyword)
            else:
                query = industry_keyword

            # 重新评分
            processed = self.process_search_results(results, query, top_k=20)

            # URL 去重
            merged = OrderedDict()
            for r in processed:
                if r.url in merged:
                    if r.fused_score > merged[r.url].fused_score:
                        merged[r.url] = r
                else:
                    merged[r.url] = r

            return dim_name, list(merged.values())

        # 并行处理各维度
        dim_results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(process_dimension, dim_name, results): dim_name
                for dim_name, results in raw_results.items()
            }
            for future in concurrent.futures.as_completed(futures):
                dim_name, results = future.result()
                dim_results[dim_name] = results

        return dim_results


def main():
    """测试用"""
    # 测试搜索
    api = HybridSearchAPI()

    # 如果已有索引，加载
    doc_count = api.load_index("test")
    print(f"Loaded {doc_count} documents")

    if doc_count == 0:
        # 测试爬取
        test_urls = [
            "https://www.example.com",
            "https://www.python.org",
        ]
        api.crawl_and_index(test_urls)
        api.save_index("test")

    # 测试搜索
    results = api.search("Python programming", top_k=5)
    print(f"\nSearch results for 'Python programming':")
    for r in results:
        print(f"  - {r.title} (score: {r.fused_score:.3f})")


if __name__ == "__main__":
    main()