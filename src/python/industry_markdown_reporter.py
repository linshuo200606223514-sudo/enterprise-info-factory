"""行业研究报告Markdown生成器"""
import os
import sys
import json
from datetime import datetime
from typing import Dict

class IndustryMarkdownReporter:
    """行业报告Markdown生成器"""

    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, report_data: Dict) -> str:
        """生成Markdown格式的行业报告"""
        lines = [
            f"# {report_data.get('industry', '未知行业')} 行业研究报告",
            "",
            f"**生成时间**: {report_data.get('generated_at', datetime.now().strftime('%Y-%m-%d %H:%M'))}",
            "",
            "---",
            "",
            "## 📊 行业概览",
        ]

        insights = report_data.get('key_insights', {})
        lines.append(f"- **主要玩家数**: {insights.get('player_count', 0)} 个")
        lines.append(f"- **近期动态**: {insights.get('news_count', 0)} 条")
        lines.append(f"- **市场活跃度**: {insights.get('market_activity', 'unknown')}")
        lines.append(f"- **市场概述**: {insights.get('summary', '暂无数据')}")

        # 头部玩家
        players = report_data.get('top_players', [])
        if players:
            lines.extend(["", "## 🏢 头部玩家"])
            lines.append("| 名称 | 官网 | 来源 |")
            lines.append("|------|------|------|")
            for p in players:
                name = p.get('name', '未知')[:40]
                url = p.get('url', '')
                domain = p.get('domain', '')
                lines.append(f"| {name} | [{domain}]({url}) | {domain} |")

        # 最新动态
        news = report_data.get('latest_news', [])
        if news:
            lines.extend(["", "## 📰 最新动态"])
            for n in news:
                title = n.get('title', '未知')
                url = n.get('url', '')
                source = n.get('source', '')
                lines.append(f"- **{title}** — [{source}]({url})")

        # 竞品分析
        competitors = report_data.get('competitors', [])
        if competitors:
            lines.extend(["", "## ⚔️ 竞品分析"])
            for c in competitors:
                name = c.get('name', '未知')
                url = c.get('url', '')
                lines.append(f"- [{name}]({url})")

        # 趋势
        trends = report_data.get('trends', [])
        if trends:
            lines.extend(["", "## 📈 行业趋势"])
            for t in trends:
                lines.append(f"- {t}")

        lines.extend(["", "---", f"*本报告由企业信息收集系统自动生成*"])

        return "\n".join(lines)

    def save(self, report_data: Dict, filename: str = None) -> str:
        """保存Markdown报告"""
        if filename is None:
            safe_keyword = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in report_data['industry'])
            filename = f"{safe_keyword[:20]}_行业报告_{datetime.now().strftime('%Y%m%d_%H%M')}.md"

        filepath = os.path.join(self.output_dir, filename)
        content = self.generate(report_data)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath


if __name__ == "__main__":
    data_json = None
    for arg in sys.argv[1:]:
        if arg.startswith("data="):
            data_json = arg.split("=", 1)[1]

    if not data_json:
        print("Error: data is required")
        sys.exit(1)

    data = json.loads(data_json)
    reporter = IndustryMarkdownReporter()
    filepath = reporter.save(data)
    print(filepath)