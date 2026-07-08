import pytest
import os
import shutil
from src.python.search.baidu_search import BaiduSearch
from src.python.search.tianyancha_api import TianyanchaAPI
from src.python.ai.entity_extractor import EntityExtractor
from src.python.output.json_exporter import JSONExporter
from src.python.output.markdown_reporter import MarkdownReporter

def test_full_collect_workflow():
    """测试完整收集流程"""
    # 1. 搜索（使用mock数据避免网络依赖）
    searcher = BaiduSearch()
    search_results = [
        {"title": "东社造纸厂", "url": "http://example.com", "abstract": "东社造纸厂是一家专业纸箱制造企业"}
    ]

    # 2. 工商查询
    api = TianyanchaAPI()
    tianyancha_data = api.search_company("东社造纸厂")

    # 3. AI提取
    extractor = EntityExtractor(provider="mock")
    raw_data = {"search_results": search_results, "tianyancha_data": tianyancha_data}
    structured = extractor.extract(raw_data)

    # 4. 输出
    test_data_dir = "./test_integration_data"
    test_report_dir = "./test_integration_reports"
    os.makedirs(test_data_dir, exist_ok=True)
    os.makedirs(test_report_dir, exist_ok=True)

    exporter = JSONExporter(output_dir=test_data_dir)
    data = {
        "company_name": "东社造纸厂",
        "sources": ["baidu", "tianyancha"],
        "raw_data": raw_data,
        "structured": structured
    }
    json_path = exporter.export(data, "东社造纸厂")

    reporter = MarkdownReporter(output_dir=test_report_dir)
    md_path = reporter.generate(data)

    # 验证
    assert os.path.exists(json_path)
    assert os.path.exists(md_path)
    assert len(structured["basic_info"]) >= 0
    assert len(structured["potential_pain_points"]) > 0

    # 清理
    shutil.rmtree(test_data_dir)
    shutil.rmtree(test_report_dir)