import pytest
import os
import shutil
from src.python.output.markdown_reporter import MarkdownReporter

def test_generate_report():
    """测试报告生成"""
    test_dir = "./test_output_md"
    os.makedirs(test_dir, exist_ok=True)
    reporter = MarkdownReporter(output_dir=test_dir)
    data = {
        "company_name": "东社造纸厂",
        "structured": {
            "basic_info": {"name": "东社造纸厂", "capital": "1000万元"},
            "business_scope": ["纸箱", "包装"],
            "potential_pain_points": ["订单管理混乱"]
        }
    }
    path = reporter.generate(data)
    assert os.path.exists(path)
    shutil.rmtree(test_dir)

def test_report_content():
    """测试报告内容"""
    test_dir = "./test_output_md"
    os.makedirs(test_dir, exist_ok=True)
    reporter = MarkdownReporter(output_dir=test_dir)
    data = {
        "company_name": "测试公司",
        "structured": {
            "basic_info": {},
            "business_scope": [],
            "industry_features": [],
            "potential_pain_points": []
        }
    }
    path = reporter.generate(data)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "企业画像" in content
    assert "测试公司" in content
    shutil.rmtree(test_dir)