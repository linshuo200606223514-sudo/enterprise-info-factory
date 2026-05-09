import pytest
import json
import os
import shutil
from src.python.output.json_exporter import JSONExporter

def test_export_creates_file():
    """测试导出创建文件"""
    test_dir = "./test_output_json"
    os.makedirs(test_dir, exist_ok=True)
    exporter = JSONExporter(output_dir=test_dir)
    data = {"company": "测试公司", "collected_at": "2026-05-09"}
    path = exporter.export(data, "test_company")
    assert os.path.exists(path)
    shutil.rmtree(test_dir)

def test_export_contains_required_fields():
    """测试导出数据包含必要字段"""
    test_dir = "./test_output_json"
    os.makedirs(test_dir, exist_ok=True)
    exporter = JSONExporter(output_dir=test_dir)
    data = {
        "company_name": "测试公司",
        "sources": ["baidu", "tianyancha"],
        "structured": {"basic_info": {}}
    }
    path = exporter.export(data, "test_company")
    with open(path, encoding="utf-8") as f:
        saved = json.load(f)
    assert "company_name" in saved
    assert "collected_at" in saved
    shutil.rmtree(test_dir)