"""BM25 索引模块 - 使用 rank-bm25 + jieba 分词"""
import jieba
import numpy as np
from typing import List, Dict, Tuple, Set

from storage.document import Document

# 默认行业术语（可以在实例化后添加更多）
DEFAULT_TERMS: Set[str] = {
    "ERP", "CRM", "OMS", "POS", "SaaS", "电商", "餐饮", "零售",
    "供应链", "财务管理", "人力资源", "客户管理", "订单管理",
    "数字化转型", "智能化", "自动化",
}


class BM25Indexer:
    """BM25 索引构建器"""

    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        avg_doc_length: int = None,
        custom_terms: Set[str] = None,
    ):
        """
        Args:
            k1: BM25 参数，控制词频饱和度
            b: BM25 参数，控制文档长度归一化
            avg_doc_length: 平均文档长度（自动计算）
            custom_terms: 自定义行业术语集合
        """
        self.k1 = k1
        self.b = b
        self.avg_doc_length = avg_doc_length or 500

        # 合并默认术语和自定义术语
        self.custom_terms = (DEFAULT_TERMS | (custom_terms or set()))
        self._setup_jieba()

        # 分词器配置
        self.stopwords = self._load_chinese_stopwords()

        # 索引数据
        self.doc_ids: List[str] = []
        self.doc_tokens: List[List[str]] = []
        self.doc_lengths: List[int] = []

    def _setup_jieba(self) -> None:
        """配置 jieba 分词器"""
        # 添加自定义术语到 jieba
        for term in self.custom_terms:
            jieba.add_word(term, freq=1000, tag='nz')

    def add_terms(self, terms: Set[str]) -> None:
        """动态添加行业术语"""
        for term in terms:
            jieba.add_word(term, freq=1000, tag='nz')
            self.custom_terms.add(term)

    def build_index(self, documents: List[Document]) -> None:
        """从文档列表构建 BM25 索引"""
        self.doc_ids = []
        self.doc_tokens = []
        self.doc_lengths = []

        for doc in documents:
            if not doc.content:
                continue
            self.doc_ids.append(doc.url)
            tokens = self._tokenize(doc.title + " " + doc.content)
            self.doc_tokens.append(tokens)
            self.doc_lengths.append(len(tokens))

        # 计算平均文档长度
        if self.doc_lengths:
            self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths)

    def _tokenize(self, text: str) -> List[str]:
        """中文分词 + 去停用词"""
        if not text:
            return []
        # jieba 分词
        tokens = jieba.cut(text)
        # 去停用词 + 过滤短词
        return [
            t.strip()
            for t in tokens
            if t.strip()
            and len(t) > 1
            and t.lower() not in self.stopwords
            and not t.isdigit()
        ]

    def _load_chinese_stopwords(self) -> set:
        """加载中文停用词"""
        # 常用中文停用词（简化版）
        return {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
            '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
            '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '他',
            '它', '她', '们', '吗', '呢', '吧', '啊', '哦', '嗯', '呀',
            '的', '地', '得', '之', '于', '从', '中', '为', '以', '及',
            '与', '或', '但', '却', '而', '所以', '因为', '如果', '虽然',
        }

    def search(self, query: str, top_k: int = 20, use_synonym: bool = True) -> List[Tuple[str, float]]:
        """
        BM25 搜索

        Args:
            query: 查询词
            top_k: 返回前 k 个结果

        Returns:
            List[(url, score)]: 按分数降序排列
        """
        if not self.doc_ids:
            return []

        # 同义词扩展
        if use_synonym:
            from search.synonym_expander import expand_query
            expanded_queries = expand_query(query)
            # 用扩展后的词列表搜索
            all_scores = {}
            for eq in expanded_queries:
                eq_tokens = self._tokenize(eq)
                if not eq_tokens:
                    continue
                # 计算 IDF
                doc_count = len(self.doc_tokens)
                doc_freq = {}
                for tokens in self.doc_tokens:
                    for t in set(tokens):
                        doc_freq[t] = doc_freq.get(t, 0) + 1
                # 计算分数
                for idx, tokens in enumerate(self.doc_tokens):
                    url = self.doc_ids[idx]
                    doc_len = self.doc_lengths[idx]
                    score = 0.0
                    for qt in eq_tokens:
                        if qt not in doc_freq:
                            continue
                        idf = np.log((doc_count - doc_freq[qt] + 0.5) / (doc_freq[qt] + 0.5) + 1)
                        tf = tokens.count(qt)
                        tf_norm = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length))
                        score += idf * tf_norm
                    if score > 0:
                        all_scores[url] = all_scores.get(url, 0) + score

            sorted_scores = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
            return sorted_scores[:top_k]
        else:
            # 原版逻辑
            query_tokens = self._tokenize(query)
            if not query_tokens:
                return []

            doc_count = len(self.doc_tokens)
            doc_freq = {}
            for tokens in self.doc_tokens:
                for t in set(tokens):
                    doc_freq[t] = doc_freq.get(t, 0) + 1

            scores: Dict[str, float] = {}
            for idx, tokens in enumerate(self.doc_tokens):
                url = self.doc_ids[idx]
                doc_len = self.doc_lengths[idx]
                score = 0.0

                for qt in query_tokens:
                    if qt not in doc_freq:
                        continue

                    idf = np.log((doc_count - doc_freq[qt] + 0.5) / (doc_freq[qt] + 0.5) + 1)
                    tf = tokens.count(qt)
                    tf_norm = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length))
                    score += idf * tf_norm

                if score > 0:
                    scores[url] = score

            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            return sorted_scores[:top_k]

    def get_scores(self, query: str) -> Dict[str, float]:
        """获取查询对所有文档的 BM25 分数"""
        if not self.doc_ids:
            return {}

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return {}

        doc_count = len(self.doc_tokens)
        doc_freq = {}
        for tokens in self.doc_tokens:
            for t in set(tokens):
                doc_freq[t] = doc_freq.get(t, 0) + 1

        all_scores: Dict[str, float] = {}
        for idx, tokens in enumerate(self.doc_tokens):
            url = self.doc_ids[idx]
            doc_len = self.doc_lengths[idx]
            score = 0.0

            for qt in query_tokens:
                if qt not in doc_freq:
                    continue
                idf = np.log((doc_count - doc_freq[qt] + 0.5) / (doc_freq[qt] + 0.5) + 1)
                tf = tokens.count(qt)
                tf_norm = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length))
                score += idf * tf_norm

            if score > 0:
                all_scores[url] = score

        return all_scores

    @staticmethod
    def normalize_scores(scores: Dict[str, float]) -> Dict[str, float]:
        """将分数归一化到 [0, 1]"""
        if not scores:
            return {}
        max_score = max(scores.values())
        min_score = min(scores.values())
        if max_score == min_score:
            return {k: 1.0 for k in scores}
        return {k: (v - min_score) / (max_score - min_score) for k, v in scores.items()}