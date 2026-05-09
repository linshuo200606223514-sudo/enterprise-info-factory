import pytest
from src.python.ai.entity_extractor import EntityExtractor

def test_extract_basic_info():
    """测试基本信息的提取"""
    extractor = EntityExtractor(provider="mock")
    text = "东社造纸厂成立于2010年，注册资本1000万元，位于浙江省"
    result = extractor.extract_basic_info(text)
    assert "name" in result or len(result) > 0

def test_extract_business_scope():
    """测试业务范围提取"""
    extractor = EntityExtractor(provider="mock")
    text = "主要生产纸箱、包装材料、纸板等产品"
    result = extractor.extract_business_scope(text)
    assert isinstance(result, list)

def test_extract_pain_points():
    """测试痛点推断"""
    extractor = EntityExtractor(provider="mock")
    text = "制造业工厂需要管理订单和生产"
    result = extractor.extract_pain_points(text)
    assert isinstance(result, list)
    assert len(result) > 0