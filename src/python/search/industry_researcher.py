"""行业研究模块 - 自动收集行业动态和竞品信息"""
import os
import sys
import json
import subprocess
from typing import Dict, List, Optional

class IndustryResearcher:
    """行业研究器 - 使用tavily进行多路并行搜索"""

    def __init__(self, output_dir: str = "C:/tmp/research"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def research(self, industry_keyword: str, company_keyword: str = None) -> Dict:
        """
        执行完整行业研究

        Args:
            industry_keyword: 行业关键词，如"造纸箱行业 ERP"
            company_keyword: 可选，公司名称，用于聚焦

        Returns:
            Dict - 包含行业报告和竞品数据
        """
        # 如果有公司名，把公司名加入搜索
        if company_keyword:
            main_keyword = f"{industry_keyword} {company_keyword}"
        else:
            main_keyword = industry_keyword

        # 并行执行4条搜索
        self._parallel_search(main_keyword, industry_keyword)

        # 读取并分析结果
        report_data = self._compile_report(main_keyword, company_keyword)

        return report_data

    def _parallel_search(self, main_keyword: str, industry_keyword: str) -> None:
        """并行执行4条搜索"""
        # 构建4个搜索命令
        main_file = os.path.join(self.output_dir, "main.json")
        news_file = os.path.join(self.output_dir, "news.json")
        compare_file = os.path.join(self.output_dir, "compare.json")
        community_file = os.path.join(self.output_dir, "community.json")

        # 构建命令
        cmd1 = f'tvly search "{main_keyword} 头部 平台 官网" --max-results 8 -o {main_file}'
        cmd2 = f'tvly search "{industry_keyword} 最新动态 融资 2026" --max-results 6 --topic news -o {news_file}'
        cmd3 = f'tvly search "{industry_keyword} 竞品对比 推荐" --max-results 6 -o {compare_file}'
        cmd4 = f'tvly search "{industry_keyword} 用户评价 v2ex" --max-results 5 -o {community_file}'

        # 使用 & 并行执行，wait 等待全部完成
        combined = f"({cmd1}) & ({cmd2}) & ({cmd3}) & ({cmd4}) & wait"
        subprocess.run(combined, shell=True, capture_output=True)

    def _compile_report(self, main_keyword: str, company_keyword: str = None) -> Dict:
        """编译研究报告"""
        main_data = self._load_json("main.json")
        news_data = self._load_json("news.json")
        compare_data = self._load_json("compare.json")
        community_data = self._load_json("community.json")

        # 提取高权重来源
        top_sources = self._filter_top_sources(main_data)

        result = {
            "industry": main_keyword,
            "researched_at": self._get_timestamp(),
            "top_players": self._extract_players(main_data),
            "news": self._extract_news(news_data),
            "competitors": self._extract_competitors(compare_data),
            "community_sentiment": self._extract_sentiment(community_data),
            "key_findings": self._generate_findings(top_sources, news_data, compare_data)
        }

        return result

    def _load_json(self, filename: str) -> Dict:
        """加载JSON文件"""
        path = os.path.join(self.output_dir, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def _filter_top_sources(self, data: Dict, min_score: float = 0.7) -> List[Dict]:
        """筛选高权重来源"""
        exclude_domains = [
            'zhihu.com', 'baidu.com', 'weibo.com', 'toutiao.com',
            'reddit.com', 'v2ex.com', 'quora.com', 'wikipedia.org', 'baike.baidu.com'
        ]

        results = data.get('results', [])
        filtered = []
        for r in results:
            if r.get('score', 0) >= min_score:
                url = r.get('url', '')
                domain = url.split('/')[2] if '/' in url else ''
                if domain not in exclude_domains:
                    filtered.append(r)
        return filtered[:5]

    def _extract_players(self, data: Dict) -> List[Dict]:
        """提取头部玩家"""
        results = data.get('results', [])
        players = []
        for r in results:
            if r.get('score', 0) >= 0.7:
                players.append({
                    "title": r.get('title', ''),
                    "url": r.get('url', ''),
                    "score": r.get('score', 0)
                })
        return players[:5]

    def _extract_news(self, data: Dict) -> List[Dict]:
        """提取最新动态"""
        results = data.get('results', [])
        news = []
        for r in results:
            news.append({
                "title": r.get('title', ''),
                "url": r.get('url', ''),
                "score": r.get('score', 0)
            })
        return news[:5]

    def _extract_competitors(self, data: Dict) -> List[str]:
        """提取竞品信息"""
        results = data.get('results', [])
        competitors = []
        for r in results:
            title = r.get('title', '')
            if title and r.get('score', 0) >= 0.6:
                competitors.append(title)
        return competitors[:5]

    def _extract_sentiment(self, data: Dict) -> Dict:
        """提取社区情感"""
        results = data.get('results', [])
        titles = [r.get('title', '') for r in results if r.get('title')]
        return {
            "mentions": titles,
            "summary": "社区讨论较少，需进一步调研"
        }

    def _generate_findings(self, top_sources: List[Dict], news_data: Dict, compare_data: Dict) -> List[str]:
        """生成关键发现"""
        findings = []

        # 基于头部玩家
        if top_sources:
            findings.append(f"行业头部关注度: {len(top_sources)}个高质量来源")

        # 基于新闻
        news = news_data.get('results', [])
        if news:
            findings.append(f"近期动态: {len(news)}条相关报道")

        # 基于竞品
        competitors = compare_data.get('results', [])
        if competitors:
            findings.append(f"竞品讨论热度: {len(competitors)}个相关结果")

        return findings

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


if __name__ == "__main__":
    keyword = None
    company = None
    for arg in sys.argv[1:]:
        if arg.startswith("keyword="):
            keyword = arg.split("=", 1)[1]
        elif arg.startswith("company="):
            company = arg.split("=", 1)[1]

    if not keyword:
        print("Error: keyword is required")
        sys.exit(1)

    researcher = IndustryResearcher()
    result = researcher.research(keyword, company)

    print(json.dumps(result, ensure_ascii=False, indent=2))