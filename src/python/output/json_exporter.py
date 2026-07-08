"""JSON导出模块"""
import sys
import json
import os
import re
from datetime import datetime
from typing import Dict

class JSONExporter:
    """企业信息的JSON格式导出器"""

    def __init__(self, output_dir: str = "./data"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export(self, data: Dict, company_name: str) -> str:
        """
        导出数据到JSON文件

        Args:
            data: 要导出的数据结构
            company_name: 公司名称（用于文件名）

        Returns:
            str - 导出文件的路径
        """
        # 添加收集时间戳
        if "collected_at" not in data:
            data["collected_at"] = datetime.now().isoformat()

        # 生成安全文件名
        safe_name = self._safe_filename(company_name)
        filename = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filepath

    def _safe_filename(self, name: str) -> str:
        """生成安全的文件名"""
        safe = re.sub(r'[^一-龥a-zA-Z0-9]', '_', name)
        return safe[:50]

if __name__ == "__main__":
    data_json = None
    company_name = None
    for arg in sys.argv[1:]:
        if arg.startswith("data="):
            data_json = arg.split("=", 1)[1]
        elif arg.startswith("company_name="):
            company_name = arg.split("=", 1)[1]

    if not data_json or not company_name:
        print("Error: data and company_name are required")
        sys.exit(1)

    data = json.loads(data_json)
    exporter = JSONExporter()
    filepath = exporter.export(data, company_name)
    print(filepath)