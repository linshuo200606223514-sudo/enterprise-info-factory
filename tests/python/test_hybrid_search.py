"""混合搜索模块测试"""
import sys
import os
from datetime import datetime

# 添加 src/python 到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src", "python"))

from storage.document import Document, CorpusStats
from indexer.bm25_indexer import BM25Indexer
from scoring.content_scorer import ContentScorer


class TestDocument:
    """Document 模型测试"""

    def test_create_document(self):
        doc = Document(
            url="https://example.com/test",
            title="测试标题",
            content="测试内容",
            domain="example.com",
        )
        assert doc.url == "https://example.com/test"
        assert doc.title == "测试标题"
        assert doc.domain == "example.com"
        assert doc.is_valid == True
        assert doc.is_garbled == False

    def test_is_garbled_text(self):
        # 正常文本
        assert Document.is_garbled_text("正常文本内容") == False
        # 乱码检测
        assert Document.is_garbled_text("\x00\x01\x02") == True
        # 短文本
        assert Document.is_garbled_text("") == False

    def test_is_navigation_content(self):
        # 导航内容检测
        assert Document.is_navigation_content("这是一个普通段落内容") == False
        assert Document.is_navigation_content("[](https://example.com)") == True
        # nav_patterns = ['](/', 'tag-', 'article/', 'category/']
        # 需要超过3次才判定为导航
        assert Document.is_navigation_content("/tag-python /tag-js /tag-ts /article/test /category/test") == True

    def test_to_dict_from_dict(self):
        doc = Document(
            url="https://example.com/test",
            title="测试",
            content="内容",
            domain="example.com",
            fetched_at=datetime(2026, 5, 10),
        )
        d = doc.to_dict()
        assert d["url"] == "https://example.com/test"

        doc2 = Document.from_dict(d)
        assert doc2.url == doc.url
        assert doc2.title == doc.title


class TestCorpusStats:
    """CorpusStats 测试"""

    def test_update_from_documents(self):
        docs = [
            Document(url="http://a.com/1", title="A", content="内容1", domain="a.com"),
            Document(url="http://b.com/1", title="B", content="内容2", domain="b.com"),
            Document(url="http://b.com/2", title="C", content="内容3", domain="b.com"),
        ]
        stats = CorpusStats()
        stats.update_from_documents(docs)

        assert stats.total_count == 3
        assert stats.domain_counts == {"a.com": 1, "b.com": 2}
        assert stats.avg_content_length > 0

    def test_domain_diversity_score(self):
        docs = [
            Document(url="http://a.com/1", title="A", content="内容1", domain="a.com"),
            Document(url="http://a.com/2", title="B", content="内容2", domain="a.com"),
            Document(url="http://a.com/3", title="C", content="内容3", domain="a.com"),
            Document(url="http://a.com/4", title="D", content="内容4", domain="a.com"),
            Document(url="http://a.com/5", title="E", content="内容5", domain="a.com"),
            Document(url="http://a.com/6", title="F", content="内容6", domain="a.com"),
        ]
        stats = CorpusStats()
        stats.update_from_documents(docs)

        # 6个文档来自同一域名，多样性应为0
        assert stats.domain_diversity_score("a.com") == 0
        assert stats.domain_diversity_score("b.com") == 1  # 新域名满分


class TestBM25Indexer:
    """BM25 索引测试"""

    def test_build_index(self):
        docs = [
            Document(url="http://a.com/1", title="餐饮 ERP 系统", content="餐饮行业解决方案"),
            Document(url="http://a.com/2", title="零售 POS", content="零售收银系统"),
        ]
        indexer = BM25Indexer()
        indexer.build_index(docs)

        assert len(indexer.doc_ids) == 2
        assert len(indexer.doc_tokens) == 2

    def test_search(self):
        docs = [
            Document(url="http://a.com/1", title="餐饮 ERP 系统", content="餐饮行业解决方案"),
            Document(url="http://a.com/2", title="零售 POS", content="零售收银系统"),
            Document(url="http://b.com/1", title="电商 SaaS", content="电商平台服务"),
        ]
        indexer = BM25Indexer()
        indexer.build_index(docs)

        results = indexer.search("餐饮 ERP", top_k=5)
        assert len(results) > 0
        assert results[0][0] == "http://a.com/1"  # 第一个结果应该是餐饮相关的

    def test_normalize_scores(self):
        scores = {"a": 10.0, "b": 5.0, "c": 1.0}
        normalized = BM25Indexer.normalize_scores(scores)

        assert normalized["a"] == 1.0
        assert 0.4 < normalized["b"] < 0.6  # 约0.44，允许误差
        assert normalized["c"] == 0.0


class TestContentScorer:
    """内容评分器测试"""

    def test_calc_valid_score(self):
        doc = Document(url="http://test.com", title="Test", content="Content", domain="test.com")
        scorer = ContentScorer()

        assert scorer.calc_valid_score(doc) == 1.0

        doc_invalid = Document(url="http://test.com", title="Test", content="Content", domain="test.com", is_valid=False)
        assert scorer.calc_valid_score(doc_invalid) == 0.0

    def test_calc_quality_score(self):
        scorer = ContentScorer()

        # 短内容
        doc_short = Document(url="http://test.com", title="Test", content="短", domain="test.com")
        assert scorer.calc_quality_score(doc_short) == 0.0

        # 长内容 (3000字 > 2000)
        doc_long = Document(url="http://test.com", title="Test", content="A" * 3000, domain="test.com")
        assert scorer.calc_quality_score(doc_long) == 1.0

    def test_score_batch(self):
        docs = [
            Document(url="http://a.com/1", title="A", content="A" * 3000, domain="a.com"),
            Document(url="http://b.com/1", title="B", content="短", domain="b.com"),
        ]
        scorer = ContentScorer()
        scores = scorer.score_batch(docs)

        assert scores["http://a.com/1"] > scores["http://b.com/1"]

    def test_get_score_breakdown(self):
        doc = Document(url="http://test.com", title="Test", content="A" * 2000, domain="test.com")
        scorer = ContentScorer()
        breakdown = scorer.get_score_breakdown(doc)

        assert "total" in breakdown
        assert "valid" in breakdown
        assert "quality" in breakdown
        assert "diversity" in breakdown
        assert "freshness" in breakdown


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])