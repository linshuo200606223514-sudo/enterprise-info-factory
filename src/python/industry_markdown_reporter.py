"""行业研究报告Markdown生成器"""
import os
import sys
import json
from datetime import datetime
from typing import Dict, List

class IndustryMarkdownReporter:
    """行业报告Markdown生成器"""

    def __init__(self, output_dir: str = None):
        if output_dir is None:
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(root, "reports")
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

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
        lines.append(f"- **竞品数量**: {insights.get('competitor_count', 0)} 个")
        lines.append(f"- **市场活跃度**: {insights.get('market_activity', 'unknown')}")
        lines.append(f"- **市场概述**: {insights.get('summary', '暂无数据')}")

        # 搜索耗时分析
        timings = report_data.get('search_timings', {})
        if timings:
            lines.extend(["", "### ⏱️ 信息收集效率"])
            for name, info in timings.items():
                label = {"main": "头部玩家", "news": "新闻动态", "compare": "竞品对比", "trend": "趋势分析", "community": "社区评价"}.get(name, name)
                status = "[OK]" if info.get("success") else "[FAIL]"
                elapsed = info.get("elapsed", 0)
                lines.append(f"- {label}: {elapsed:.1f}s {status}")

        # 搜索质量分析
        quality = report_data.get('search_quality', {})
        if quality:
            lines.extend(["", "### 📊 搜索质量分析（基于内容可用性）"])
            lines.append("| 搜索维度 | 结果数 | 可用 | 域名多样 | Tavily均分 | 质量分 | 状态 |")
            lines.append("|----------|--------|------|----------|-----------|--------|------|")
            for name, info in quality.items():
                label = {"main": "头部玩家", "news": "新闻动态", "compare": "竞品对比", "trend": "趋势分析", "community": "社区评价"}.get(name, name)
                count = info.get('count', 0)
                valid = info.get('valid_count', count)
                div = info.get('domain_diversity', 0)
                avg = info.get('avg_score', 0)
                qs = info.get('quality_score', 0)
                status = info.get('status', 'unknown')
                status_icon = "[OK]" if status == "good" else "[WARN]" if status == "warning" else "[FAIL]"
                lines.append(f"| {label} | {count} | {valid} | {div} | {avg:.3f} | {qs:.3f} | {status_icon} |")

        # 内容提取质量
        extraction = report_data.get('extraction_quality', {})
        if extraction:
            lines.extend(["", "### 🔍 内容提取质量"])
            total = extraction.get('total_players', 0)
            lines.append(f"- 已分析玩家: {total} 个")
            lines.append(f"- 核心功能有效率: {extraction.get('core_functions_valid', 0)}/{total} ({extraction.get('core_functions_rate', 0)*100:.0f}%)")
            lines.append(f"- 定价信息有效率: {extraction.get('pricing_valid', 0)}/{total} ({extraction.get('pricing_rate', 0)*100:.0f}%)")
            lines.append(f"- 综合有效率: {extraction.get('overall_rate', 0)*100:.0f}%")

        # 头部玩家（带详情）
        players = report_data.get('top_players', [])
        if players:
            lines.extend(["", "## 🏢 头部玩家"])
            lines.append("")
            lines.append("| 名称 | 核心功能 | 定价 |")
            lines.append("|------|----------|------|")
            for p in players:
                name = p.get('name', '未知')[:35]
                func = p.get('core_functions', '未提及')[:40]
                pricing = p.get('pricing', '未提及')[:30]
                func_clean = func.replace('|', '\\|').replace('\n', ' ')
                pricing_clean = pricing.replace('|', '\\|').replace('\n', ' ')
                lines.append(f"| {name} | {func_clean} | {pricing_clean} |")

        # 最新动态
        news = report_data.get('latest_news', [])
        if news:
            lines.extend(["", "## 📰 最新动态"])
            for n in news[:8]:
                title = n.get('title', '未知')[:60]
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
            for t in trends[:6]:
                lines.append(f"- {t}")

        # 社区评价
        community = report_data.get('community', [])
        if community:
            lines.extend(["", "## 💬 社区评价"])
            for c in community[:5]:
                title = c.get('title', '')[:60]
                url = c.get('url', '')
                source = c.get('source', '')
                lines.append(f"- [{title}]({url}) — {source}")

        # 洞察分析
        insight_lines = self._generate_insights_section(report_data)
        lines.extend(insight_lines)

        lines.extend(["", "---", f"*本报告由企业信息收集系统自动生成*"])

        return "\n".join(lines)

    def _generate_insights_section(self, report_data: Dict) -> List[str]:
        """生成洞察分析部分"""
        lines = []
        players = report_data.get('top_players', [])

        if not players:
            return lines

        lines.extend(["", "## 💡 关键洞察"])

        # 1. 定价区间分析
        pricing_players = [p for p in players if p.get('pricing', '未提及') != '未提及']
        if pricing_players:
            lines.extend(["", "### 定价区间"])
            pricing_texts = [p.get('pricing', '') for p in pricing_players]
            # 尝试提取价格数字
            import re
            prices = []
            for text in pricing_texts:
                nums = re.findall(r'[\d,]+\.?\d*\s*元', text)
                prices.extend(nums[:2])  # 每个player最多取2个价格
            if prices:
                lines.append(f"- 已获取定价的玩家: {len(pricing_players)}/{len(players)} 个")
                lines.append(f"- 价格样本: {', '.join(prices[:5])}")
            else:
                lines.append(f"- 已获取定价信息的玩家: {len(pricing_players)}/{len(players)} 个")
                lines.append(f"- 定价模式: {pricing_texts[0][:50]}...")

        # 2. 功能分布分析
        func_players = [p for p in players if p.get('core_functions', '未提及') != '未提及']
        if func_players:
            lines.extend(["", "### 功能分布"])
            lines.append(f"- 已获取功能描述的玩家: {len(func_players)}/{len(players)} 个")

            # 统计功能关键词
            all_funcs = ' '.join([p.get('core_functions', '') for p in func_players])
            keywords = {
                '供应链': ['供应链', '采购', '库存', '仓储'],
                '财务管理': ['财务', '记账', '账务', '发票'],
                '会员营销': ['会员', '营销', '优惠券', '积分'],
                '智能分析': ['分析', '报表', 'BI', '数据'],
                '门店管理': ['门店', '分店', '连锁', '店'],
            }
            for category, kws in keywords.items():
                count = sum(1 for kw in kws if kw in all_funcs)
                if count > 0:
                    lines.append(f"- 涉及{category}功能的玩家: 约{count}个")

        # 3. 市场格局总结
        lines.extend(["", "### 市场格局"])
        insights = report_data.get('key_insights', {})
        activity = insights.get('market_activity', 'unknown')
        if activity == 'high':
            lines.append("该行业市场竞争激烈，头部玩家活跃，新进入者需差异化定位。")
        elif activity == 'medium':
            lines.append("该行业市场处于稳定期，有明确的头部玩家，市场格局相对稳定。")
        else:
            lines.append("该行业市场相对分散，缺乏明确的绝对领导者。")

        return lines

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