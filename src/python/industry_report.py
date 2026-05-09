"""行业研究报告生成器 - 专注行业研究，不聚焦具体企业"""
import os
import sys
import json
import subprocess
from typing import Dict, List
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
        """并行执行5条搜索"""
        output_dir = "C:/tmp/industry_report"
        os.makedirs(output_dir, exist_ok=True)

        main_file = os.path.join(output_dir, "main.json")
        news_file = os.path.join(output_dir, "news.json")
        compare_file = os.path.join(output_dir, "compare.json")
        trend_file = os.path.join(output_dir, "trend.json")
        community_file = os.path.join(output_dir, "community.json")

        cmd1 = f'tvly search "{keyword} 头部玩家 平台 官网 2026" --max-results 8 -o {main_file}'
        cmd2 = f'tvly search "{keyword} 最新动态 行业新闻 2026" --max-results 6 -o {news_file}'
        cmd3 = f'tvly search "{keyword} 竞品对比 推荐 选型" --max-results 6 -o {compare_file}'
        cmd4 = f'tvly search "{keyword} 趋势 数字化转型 技术动态" --max-results 5 -o {trend_file}'
        cmd5 = f'tvly search "{keyword} 用户评价 知乎 v2ex" --max-results 5 -o {community_file}'

        combined = f"({cmd1}) & ({cmd2}) & ({cmd3}) & ({cmd4}) & ({cmd5}) & wait"
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
        community_data = self._load_json(os.path.join(output_dir, "community.json"))

        # 从所有数据源提取头部玩家
        top_players = self._extract_players(main_data)
        competitors = self._extract_competitors(compare_data)

        # 如果top_players太少，从competitors补充
        if len(top_players) < 3:
            for c in competitors:
                if len(top_players) >= 5:
                    break
                name = c.get('name', '')
                if 'ERP' in name or '系统' in name or '软件' in name or '厂商' in name:
                    if c.get('score', 0) >= 0.6:
                        top_players.append(c)

        # 对头部玩家URL提取详情（核心功能、定价）
        if top_players:
            self._extract_player_details(top_players[:5])

        report = {
            "industry": keyword,
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "top_players": top_players[:8],
            "latest_news": self._extract_news(news_data),
            "competitors": competitors,
            "trends": self._extract_trends(trend_data),
            "community": self._extract_community(community_data),
            "key_insights": self._generate_insights(main_data, news_data, compare_data, trend_data, top_players)
        }

        return report

    def _extract_player_details(self, players: List[Dict]) -> None:
        """对头部玩家URL提取详情（核心功能、定价模式）"""
        if not players:
            return

        output_dir = "C:/tmp/industry_report"
        extract_file = os.path.join(output_dir, "extract.json")

        # 构建URL列表（最多5个）
        urls = [p.get('url', '') for p in players[:5] if p.get('url')]
        if not urls:
            return

        # 调用tavily extract
        url_args = ' '.join(f'"{u}"' for u in urls)
        cmd = f'tvly extract {url_args} --json -o {extract_file}'
        subprocess.run(cmd, shell=True, capture_output=True)

        # 解析提取结果
        extract_data = self._load_json(extract_file)
        results = extract_data.get('results', [])

        # 为每个player补充详情
        for i, player in enumerate(players[:5]):
            if i < len(results):
                raw_content = results[i].get('raw_content', '')
                player['core_functions'] = self._parse_core_functions(raw_content)
                player['pricing'] = self._parse_pricing(raw_content)

    def _parse_core_functions(self, content: str) -> str:
        """从内容中解析核心功能"""
        if not content:
            return "未知"
        # 简单关键词匹配
        keywords = ['核心功能', '主要功能', '产品功能', '功能介绍', '解决方案']
        for kw in keywords:
            if kw in content:
                # 找到关键词后的100-300字
                idx = content.find(kw)
                snippet = content[idx:idx+300]
                # 清理
                snippet = ' '.join(snippet.split())[:200]
                return snippet + "..." if len(snippet) >= 200 else snippet
        return "官网未提供详细信息"

    def _parse_pricing(self, content: str) -> str:
        """从内容中解析定价模式"""
        if not content:
            return "未知"
        keywords = ['定价', '价格', '收费', '费用', '套餐', '版本']
        for kw in keywords:
            if kw in content:
                idx = content.find(kw)
                snippet = content[idx:idx+200]
                snippet = ' '.join(snippet.split())[:150]
                return snippet + "..." if len(snippet) >= 150 else snippet
        return "官网未提供定价信息"

    def _extract_players(self, data: Dict) -> List[Dict]:
        """提取头部玩家 - 使用更低阈值捕获中文相关结果"""
        exclude_domains = ['wikipedia.org', 'baike.baidu.com', 'scribd.com',
                           'zhaopin.com', 'zhilian.com', '51job.com', 'liepin.com',  # 招聘网站
                           'csdn.net', 'iteye.com', 'cnblogs.com',  # 技术博客
                           'zhihu.com', 'baidu.com', 'sina.com.cn', 'sohu.com', 'qq.com']  # 聚合/门户
        results = data.get('results', [])
        players = []
        for r in results:
            score = r.get('score', 0)
            title = r.get('title', '')
            url = r.get('url', '')

            # 跳过低分
            if score < 0.25:
                continue

            # 跳过纯英文标题（无中文）
            if title and not any('一' <= c <= '鿿' for c in title):
                continue

            # 跳过招聘相关标题
            if any(kw in title for kw in ['招聘', '职位', '薪资', '面试', '简历', '猎头', 'job', 'career', 'hiring']):
                continue

            domain = url.split('/')[2] if '/' in url else ''
            if domain not in exclude_domains:
                players.append({
                    "name": title,
                    "url": url,
                    "score": score,
                    "domain": domain
                })
        return players[:8]

    def _extract_news(self, data: Dict) -> List[Dict]:
        """提取最新动态"""
        results = data.get('results', [])
        news = []
        for r in results:
            title = r.get('title', '')
            # 跳过无中文标题的新闻（国际新闻噪音太多）
            if not any('一' <= c <= '鿿' for c in title):
                continue
            news.append({
                "title": title,
                "url": r.get('url', ''),
                "date": "2026",  # Tavily不返回日期，使用年 approximate
                "source": self._extract_domain(r.get('url', ''))
            })
        return news[:6]

    def _extract_competitors(self, data: Dict) -> List[Dict]:
        """提取竞品信息"""
        results = data.get('results', [])
        competitors = []
        for r in results:
            title = r.get('title', '')
            score = r.get('score', 0)
            # 跳过纯英文和无中文标题
            if score < 0.3:
                continue
            if not any('一' <= c <= '鿿' for c in title):
                continue
            competitors.append({
                "name": title,
                "url": r.get('url', ''),
                "score": score
            })
        return competitors[:6]

    def _extract_community(self, data: Dict) -> List[Dict]:
        """提取社区评价"""
        results = data.get('results', [])
        community = []
        for r in results:
            title = r.get('title', '')
            url = r.get('url', '')
            score = r.get('score', 0)
            # 跳过低分
            if score < 0.25:
                continue
            # 跳过纯英文
            if not any('一' <= c <= '鿿' for c in title):
                continue
            community.append({
                "title": title,
                "url": url,
                "source": self._extract_domain(url),
                "score": score
            })
        return community[:5]

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

    def _generate_insights(self, main_data: Dict, news_data: Dict, compare_data: Dict, trend_data: Dict, top_players: List[Dict] = None) -> Dict:
        """生成关键洞察"""
        if top_players is None:
            top_players = []
        # 统计数量 - player_count用实际提取的top_players数量
        player_count = len(top_players)
        news_count = len(news_data.get('results', []))
        competitor_count = len([r for r in compare_data.get('results', []) if r.get('score', 0) >= 0.25])
        trend_count = len(trend_data.get('results', []))

        # 判断市场活跃度
        if news_count >= 5 and trend_count >= 3:
            activity = "high"
            desc = "非常活跃"
        elif news_count >= 3 or trend_count >= 2:
            activity = "medium"
            desc = "中等活跃"
        else:
            activity = "low"
            desc = "较为平静"

        insights = {
            "player_count": player_count,
            "news_count": news_count,
            "competitor_count": competitor_count,
            "trend_count": trend_count,
            "market_activity": activity,
            "summary": f"该行业市场{desc}，当前有{news_count}条最新动态，{trend_count}条趋势讨论。"
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