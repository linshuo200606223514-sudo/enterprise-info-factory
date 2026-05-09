"""Markdown报告生成模块"""
import sys
import json
import os
from datetime import datetime
from typing import Dict

class MarkdownReporter:
    """企业画像Markdown报告生成器"""

    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, data: Dict) -> str:
        """
        生成Markdown格式的企业画像报告

        Args:
            data: 包含企业信息的数据字典

        Returns:
            str - 报告文件路径
        """
        company_name = data.get("company_name", "未知企业")
        structured = data.get("structured", {})

        markdown = self._build_markdown(company_name, structured)

        filename = f"{company_name}_企业画像_{datetime.now().strftime('%Y%m%d')}.md"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)

        return filepath

    def _build_markdown(self, company_name: str, structured: Dict) -> str:
        """构建Markdown内容"""
        lines = [
            f"# 企业画像：{company_name}",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            "",
            "## 基础信息",
        ]

        basic_info = structured.get("basic_info", {})
        if basic_info:
            for key, value in basic_info.items():
                lines.append(f"- **{key}**: {value}")
        else:
            lines.append("- 暂无信息")

        lines.extend(["", "## 业务范围"])
        scope = structured.get("business_scope", [])
        if scope:
            for item in scope:
                lines.append(f"- {item}")
        else:
            lines.append("- 暂无信息")

        lines.extend(["", "## 行业特征"])
        features = structured.get("industry_features", [])
        if features:
            for item in features:
                lines.append(f"- {item}")
        else:
            lines.append("- 暂无信息")

        lines.extend(["", "## 可能的痛点（AI推断）"])
        pain_points = structured.get("potential_pain_points", [])
        if pain_points:
            for i, point in enumerate(pain_points, 1):
                lines.append(f"{i}. {point}")
        else:
            lines.append("- 暂无信息")

        lines.extend(["", "---", f"*本报告由企业信息收集系统自动生成*"])

        return "\n".join(lines)

if __name__ == "__main__":
    data_json = None
    for arg in sys.argv[1:]:
        if arg.startswith("data="):
            data_json = arg.split("=", 1)[1]

    if not data_json:
        print("Error: data is required")
        sys.exit(1)

    data = json.loads(data_json)
    reporter = MarkdownReporter()
    filepath = reporter.generate(data)
    print(filepath)