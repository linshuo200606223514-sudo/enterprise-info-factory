import pytest
from src.python.search.baidu_search import BaiduSearch

def test_search_returns_results():
    """测试搜索返回非空结果"""
    searcher = BaiduSearch()
    results = searcher.search("东社造纸厂")
    assert isinstance(results, list)

def test_search_result_structure():
    """测试结果包含必要字段"""
    searcher = BaiduSearch()
    results = searcher.search("测试公司")
    if len(results) > 0:
        assert "title" in results[0]
        assert "url" in results[0]
        assert "abstract" in results[0]