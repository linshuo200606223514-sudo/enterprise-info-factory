import pytest
from src.python.ai.entity_extractor import EntityExtractor

def test_extract_with_mock_data():
    """测试实体提取器对Mock数据的处理"""
    extractor = EntityExtractor(provider="mock")

    raw_data = {
        "search_results": [
            {"title": "东社造纸厂 - 专业纸箱制造商", "abstract": "成立于2010年，注册资本1000万元"}
        ],
        "tianyancha_data": {
            "data": {
                "items": [{
                    "name": "东社造纸厂",
                    "capital": "1000万元",
                    "成立时间": "2010-01-01",
                    "地址": "浙江省温州市",
                    "经营范围": "纸箱制造、销售"
                }]
            }
        }
    }

    result = extractor.extract(raw_data)

    assert "company_name" in result
    assert "confirmed_info" in result
    assert "potential_pain_points" in result
    assert "confidence_score" in result

def test_extract_by_rules_fallback():
    """测试规则提取降级方案"""
    extractor = EntityExtractor(provider="mock")

    raw_data = {
        "search_results": [],
        "tianyancha_data": {"data": {"items": []}}
    }

    result = extractor.extract(raw_data)

    assert result.get("confidence_score") == 0.2
    assert "company_name" in result
    assert "potential_pain_points" in result

def test_confirmed_info_structure():
    """测试confirmed_info结构"""
    extractor = EntityExtractor(provider="mock")

    raw_data = {
        "search_results": [
            {"title": "测试公司", "abstract": "纸箱制造商"}
        ],
        "tianyancha_data": {"data": {"items": []}}
    }

    result = extractor.extract(raw_data)
    confirmed = result.get("confirmed_info", {})

    assert "business_scope" in confirmed
    assert "location" in confirmed
    assert "established_year" in confirmed
    assert "estimated_scale" in confirmed