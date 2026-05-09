"""行业研究报告生成器 - 专注行业研究，不聚焦具体企业"""
import os
import sys
import json
import subprocess
from typing import Dict, List, Optional
from datetime import datetime

class IndustryReportGenerator:
    """行业报告生成器"""

    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, industry_keyword: str) -> Dict:
        """
        生成行业研究报告

        Args:
            industry_keyword: 行业关键词，如"造纸箱行业 ERP"

        Returns:
            Dict - 包含完整行业研究数据
        """
        # 并行执行4条搜索
        self._parallel_search(industry_keyword)

        # 编译研究报告
        report_data = self._compile_report(industry_keyword)

        return report_data

    def _parallel_search(self, keyword: str) -> None:
        """并行执行4条搜索"""
        output_dir = "C:/tmp/industry_report"
        os.makedirs(output_dir, exist_ok=True)

        main_file = os.path.join(output_dir, "main.json")
        news_file = os.path.join(output_dir, "news.json")
        compare_file = os.path.join(output_dir, "compare.json")
        trend_file = os.path.join(output_dir, "trend.json")

        cmd1 = f'tvly search "{keyword} 头部玩家 平台 官网 2026" --max-results 8 -o {main_file}'
        cmd2 = f'tvly search "{keyword} 最新动态 融资 产品发布 2026" --max-results 6 --topic news -o {news_file}'
        cmd3 = f'tvly search "{keyword} 竞品对比 推荐 选型" --max-results 6 -o {compare_file}'
        cmd4 = f'tvly search "{keyword} 趋势 数字化转型 技术动态" --max-results 5 -o {trend_file}'

        combined = f"({cmd1}) & ({cmd2}) & ({cmd3}) & ({cmd4}) & wait"
        subprocess.run(combined, shell=True, capture_output=True)

    def _load_json(self, filepath: str) -> Dict:
        """加载JSON文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def _compile_report(self, keyword: str) -> Dict:
        """编译研究报告"""
        output_dir = "C:/tmp/industry_report"

        main_data = self._load_json(os.path.join(output_dir, "main.json"))
        news_data = self._load_json(os.path.join(output_dir, "news.json"))
        compare_data = self._load_json(os.path.join(output_dir, "compare.json"))
        trend_data = self._load_json(os.path.join(output_dir, "trend.json"))

        report = {
            "industry": keyword,
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "top_players": self._extract_players(main_data),
            "latest_news": self._extract_news(news_data),
            "competitors": self._extract_competitors(compare_data),
            "trends": self._extract_trends(trend_data),
            "key_insights": self._generate_insights(main_data, news_data, compare_data, trend_data)
        }

        return report

    def _extract_players(self, data: Dict) -> List[Dict]:
        """提取头部玩家"""
        # 放宽筛选条件，score >= 0.5
        exclude_domains = ['wikipedia.org', 'baike.baidu.com']  # 只排除百科类
        results = data.get('results', [])
        players = []
        for r in results:
            if r.get('score', 0) >= 0.5:
                url = r.get('url', '')
                domain = url.split('/')[2] if '/' in url else ''
                if domain not in exclude_domains:
                    players.append({
                        "name": r.get('title', ''),
                        "url": url,
                        "score": r.get('score', 0),
                        "domain": domain
                    })
        return players[:8]

    def _extract_news(self, data: Dict) -> List[Dict]:
        """提取最新动态"""
        results = data.get('results', [])
        news = []
        for r in results[:6]:
            news.append({
                "title": r.get('title', ''),
                "url": r.get('url', ''),
                "date": "2026",  # Tavily不返回日期，使用年 approximate
                "source": self._extract_domain(r.get('url', ''))
            })
        return news

    def _extract_competitors(self, data: Dict) -> List[Dict]:
        """提取竞品信息"""
        results = data.get('results', [])
        competitors = []
        for r in results:
            if r.get('score', 0) >= 0.5:
                competitors.append({
                    "name": r.get('title', ''),
                    "url": r.get('url', ''),
                    "score": r.get('score', 0)
                })
        return competitors[:6]

    def _extract_trends(self, data: Dict) -> List[str]:
        """提取趋势"""
        results = data.get('results', [])
        trends = []
        for r in results:
            if r.get('title'):
                trends.append(r.get('title', ''))
        return trends[:5]

    def _extract_domain(self, url: str) -> str:
        """提取域名"""
        try:
            return url.split('/')[2].replace('www.', '') if '/' in url else ''
        except:
            return ''

    def _generate_insights(self, main_data: Dict, news_data: Dict, compare_data: Dict, trend_data: Dict) -> Dict:
        """生成关键洞察"""
        # 统计数量
        player_count = len([r for r in main_data.get('results', []) if r.get('score', 0) >= 0.6])
        news_count = len(news_data.get('results', []))
        competitor_count = len([r for r in compare_data.get('results', []) if r.get('score', 0) >= 0.5])

        # 简单洞察
        insights = {
            "player_count": player_count,
            "news_count": news_count,
            "competitor_count": competitor_count,
            "market_activity": "high" if news_count >= 5 else "medium" if news_count >= 3 else "low",
            "summary": f"该行业有{player_count}个主要玩家，当前市场动态{news_count}条，相关竞品讨论{competitor_count}条。"
        }

        return insights

    def save_json(self, report_data: Dict, filename: str = None) -> str:
        """保存JSON格式报告"""
        if filename is None:
            safe_keyword = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in report_data['industry'])
            filename = f"{safe_keyword[:20]}_行业报告_{datetime.now().strftime('%Y%m%d_%H%M')}.json"

        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        return filepath


def generate_industry_report(industry_keyword: str) -> Dict:
    """便捷函数：生成行业报告"""
    generator = IndustryReportGenerator()
    return generator.generate(industry_keyword)


if __name__ == "__main__":
    keyword = None
    for arg in sys.argv[1:]:
        if arg.startswith("keyword="):
            keyword = arg.split("=", 1)[1]

    if not keyword:
        print("Error: keyword is required")
        sys.exit(1)

    report = generate_industry_report(keyword)
    print(json.dumps(report, ensure_ascii=False, indent=2))