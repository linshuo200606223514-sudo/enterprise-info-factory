import pytest
from unittest.mock import patch, MagicMock
from src.python.search.tianyancha_api import TianyanchaAPI

def test_search_company_returns_data():
    """测试企业搜索返回数据结构"""
    api = TianyanchaAPI(api_key="test_key")
    with patch('requests.get') as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": {"items": []}}
        )
        result = api.search_company("东社造纸厂")
        assert isinstance(result, dict)
        assert "items" in result or "data" in result

def test_mock_data_when_no_api_key():
    """测试无API key时返回mock数据"""
    api = TianyanchaAPI(api_key=None)
    result = api.search_company("测试公司")
    assert isinstance(result, dict)
    assert "data" in result