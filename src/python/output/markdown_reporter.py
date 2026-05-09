"""Markdown报告生成模块 - 支持行业背景融合"""
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
        company_name = data.get("company_name", "未知企业")
        llm_analysis = data.get("llm_analysis", data.get("structured", {}))
        industry_context = data.get("industry_context", {})
        markdown = self._build_markdown(company_name, llm_analysis, industry_context)

        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in company_name)
        filename = f"{safe_name}_企业画像_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)
        return filepath

    def _build_markdown(self, company_name: str, llm_data: Dict, industry_context: Dict = None) -> str:
        lines = [
            f"# 企业画像：{company_name}",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**数据可信度**: {llm_data.get('confidence_score', 'N/A')}",
            "",
            "---",
            "",
            "## 📋 已确认信息",
        ]

        confirmed = llm_data.get("confirmed_info", {})
        if confirmed:
            lines.append(f"- **业务范围**: {', '.join(confirmed.get('business_scope', ['待确认']))}")
            lines.append(f"- **地理位置**: {confirmed.get('location', '未确认')}")
            lines.append(f"- **成立年份**: {confirmed.get('established_year', '未确认')}")
            lines.append(f"- **预估规模**: {confirmed.get('estimated_scale', '未确认')}")
        else:
            lines.append("- 暂无确认信息")

        lines.extend(["", "## 📊 业务特征"])
        biz_chars = llm_data.get("business_characteristics", "")
        lines.append(biz_chars if biz_chars else "信息不足，无法分析")

        lines.extend(["", "## 🏭 行业定位"])
        lines.append(llm_data.get("industry_position", "未确认"))

        # 竞争优势（新增）
        advantages = llm_data.get("competitive_advantages", [])
        if advantages:
            lines.extend(["", "## 💪 竞争优势"])
            for adv in advantages:
                lines.append(f"- {adv}")

        lines.extend(["", "## ⚠️ 潜在痛点"])
        pain_points = llm_data.get("potential_pain_points", [])
        if pain_points:
            severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            for pp in pain_points:
                emoji = severity_emoji.get(pp.get("severity", "medium"), "⚪")
                lines.append(f"{emoji} **{pp.get('issue', '未知问题')}**")
                lines.append(f"   - 依据: {pp.get('basis', '无')}")
        else:
            lines.append("未识别到明显痛点")

        lines.extend(["", "## 💻 数字化成熟度"])
        digital = llm_data.get("digital_maturity", {})
        if digital:
            lines.append(f"**评级**: {digital.get('level', '未知')}")
            lines.append(f"**描述**: {digital.get('description', '')}")
            indicators = digital.get("indicators", [])
            if indicators:
                lines.append("**判断依据**:")
                for ind in indicators:
                    lines.append(f"- {ind}")
        else:
            lines.append("信息不足，无法评估")

        lines.extend(["", "## 📰 市场口碑"])
        reputation = llm_data.get("market_reputation", {})
        if reputation:
            sentiment = reputation.get("sentiment", "unknown")
            sentiment_map = {"positive": "✅ 正面", "negative": "❌ 负面", "neutral": "➖ 中性", "unknown": "❓ 未知"}
            lines.append(f"**情感倾向**: {sentiment_map.get(sentiment, '未知')}")
            evidence = reputation.get("evidence", [])
            if evidence:
                lines.append("**评价证据**:")
                for e in evidence:
                    lines.append(f"- {e}")
            concerns = reputation.get("concerns", [])
            if concerns:
                lines.append("**投诉/问题**:")
                for c in concerns:
                    lines.append(f"- {c}")
        else:
            lines.append("暂无公开评价信息")

        # 行业背景（新增）
        if industry_context:
            lines.extend(["", "## 🏢 行业背景"])
            players = industry_context.get("top_players", [])
            if players:
                lines.append("**行业头部玩家**:")
                for p in players[:3]:
                    lines.append(f"- {p.get('title', '未知')}")
            news = industry_context.get("news", [])
            if news:
                lines.append("**近期动态**:")
                for n in news[:3]:
                    lines.append(f"- {n.get('title', '未知')[:60]}")

        # 数字化建议（新增）
        recommendations = llm_data.get("recommendations", [])
        if recommendations:
            lines.extend(["", "## 📋 数字化建议"])
            for rec in recommendations:
                lines.append(f"- {rec}")

        lines.extend(["", "## 📝 数据缺口"])
        data_gaps = llm_data.get("data_gaps", [])
        if data_gaps:
            lines.append("以下关键信息暂未获取到：")
            for gap in data_gaps:
                lines.append(f"- {gap}")
        else:
            lines.append("数据收集较完整")

        lines.extend(["", "---", "", f"*本报告由企业信息收集系统自动生成*"])

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