"""行业研究报告生成器 - 专注行业研究，不聚焦具体企业"""
import os
import sys
import json
import subprocess
import time
from typing import Dict, List, Tuple
from datetime import datetime

from ai.website_extractor import WebsiteContentExtractor

# 并行搜索任务配置
SEARCH_TASKS = [
    {"name": "main", "keyword_suffix": "头部玩家 平台 官网 2026", "max_results": 8, "file": "main.json"},
    {"name": "news", "keyword_suffix": "最新动态 行业新闻 2026", "max_results": 6, "file": "news.json"},
    {"name": "compare", "keyword_suffix": "竞品对比 推荐 选型", "max_results": 6, "file": "compare.json"},
    {"name": "trend", "keyword_suffix": "趋势 数字化转型 技术动态", "max_results": 5, "file": "trend.json"},
    {"name": "community", "keyword_suffix": "用户评价 知乎 v2ex", "max_results": 5, "file": "community.json"},
]

class IndustryReportGenerator:
    """行业报告生成器"""

    def __init__(self, output_dir: str = None):
        # 默认输出到项目根目录的reports/文件夹
        if output_dir is None:
            # 从 src/python/industry_report.py 向上两级到项目根目录
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(root, "reports")
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.search_timings = {}  # 存储各路搜索耗时

    @staticmethod
    def get_default_output_dir() -> str:
        """获取默认输出目录路径"""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(root, "reports")

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

        # 保存报告
        self.save_json(report_data)
        self._save_markdown_report(report_data)

        return report_data

    def _save_markdown_report(self, report_data: Dict) -> None:
        """保存Markdown格式报告"""
        from industry_markdown_reporter import IndustryMarkdownReporter
        reporter = IndustryMarkdownReporter(self.output_dir)
        reporter.save(report_data)

    def _parallel_search(self, keyword: str) -> None:
        """并行执行5条搜索，使用ThreadPoolExecutor真正异步"""
        import concurrent.futures

        output_dir = "C:/tmp/industry_report"
        os.makedirs(output_dir, exist_ok=True)

        def run_single_search(task: Dict) -> Tuple[str, float, bool]:
            """执行单条搜索，返回(task_name, elapsed, success)"""
            start = time.time()
            output_file = os.path.join(output_dir, task["file"])
            cmd = f'tvly search "{keyword} {task["keyword_suffix"]}" --max-results {task["max_results"]} -o {output_file}'
            try:
                subprocess.run(cmd, shell=True, capture_output=True, timeout=120)
                elapsed = time.time() - start
                return (task["name"], elapsed, True)
            except Exception as e:
                elapsed = time.time() - start
                print(f"搜索失败 [{task['name']}]: {e}")
                return (task["name"], elapsed, False)

        # 并行执行所有搜索任务
        self.search_timings = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(run_single_search, task): task for task in SEARCH_TASKS}
            for future in concurrent.futures.as_completed(futures):
                name, elapsed, success = future.result()
                self.search_timings[name] = {"elapsed": round(elapsed, 2), "success": success}
                status = "[OK]" if success else "[FAIL]"
                print(f"  {status} {name} search completed in {elapsed:.1f}s")

    def _load_json(self, filepath: str) -> Dict:
        """加载JSON文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            # 尝试用errors='replace'修复编码问题
            try:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                # 清理常见的无效字符
                content = content.replace('﻿', '')  # BOM
                return json.loads(content)
            except Exception:
                return {}
        except Exception:
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
            "search_timings": self.search_timings,
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
        os.makedirs(output_dir, exist_ok=True)
        extract_file = os.path.join(output_dir, "extract.json")

        # 构建URL列表（最多5个）
        urls = [p.get('url', '') for p in players[:5] if p.get('url')]
        if not urls:
            return

        # 优先用Tavily extract
        url_args = ' '.join(f'"{u}"' for u in urls)
        cmd = f'tvly extract {url_args} --json -o {extract_file}'
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        subprocess.run(cmd, shell=True, capture_output=True, env=env)

        # 检查Tavily结果质量
        extract_data = self._load_json(extract_file)
        results = extract_data.get('results', [])

        # 检查是否有乱码
        garbled_count = 0
        for r in results:
            raw = r.get('raw_content', '')
            if raw and self._is_garbled(raw):
                garbled_count += 1

        # 为每个player补充详情，优先用LLM提取
        llm_extractor = WebsiteContentExtractor()
        for i, player in enumerate(players[:5]):
            url = player.get('url', '')
            if i < len(results):
                raw_content = results[i].get('raw_content', '')
                if not self._is_garbled(raw_content) and len(raw_content) > 200:
                    # 内容正常，用LLM提取结构化信息
                    llm_result = llm_extractor.extract(raw_content, url)
                    player['core_functions'] = llm_result.get('core_functions', '')
                    player['pricing'] = llm_result.get('pricing', '')
                    player['target_users'] = llm_result.get('target_users', '')
                    player['highlights'] = llm_result.get('highlights', '')
                else:
                    # 内容乱码，用scrapling备用
                    self._extract_single_with_scrapling(player)
                    # 尝试用LLM提取
                    if player.get('core_functions'):
                        llm_result = llm_extractor.extract(player.get('core_functions', ''), url)
                        player['core_functions'] = llm_result.get('core_functions', player.get('core_functions', ''))
                        player['pricing'] = llm_result.get('pricing', player.get('pricing', ''))
            elif url:
                # 无Tavily结果，直接用scrapling
                self._extract_single_with_scrapling(player)

    def _extract_single_with_scrapling(self, player: Dict) -> None:
        """使用scrapling提取单个player详情"""
        try:
            from scrapling.fetchers import Fetcher
        except ImportError:
            return

        url = player.get('url', '')
        if not url:
            return
        try:
            page = Fetcher.get(url)
            # 提取标题和链接作为主要内容
            content_parts = []
            title = page.css('title::text').get()
            if title:
                content_parts.append(f"标题: {title}")
            # 提取meta描述
            meta_desc = page.css('meta[name="description"]::attr(content)').get()
            if meta_desc:
                content_parts.append(f"描述: {meta_desc}")
            # 提取正文段落
            for p in page.css('p::text')[:10]:
                text = p.get().strip() if hasattr(p, 'get') else str(p).strip()
                if text and len(text) > 20:
                    content_parts.append(text)
            if content_parts:
                content = ' '.join(content_parts)
                if not player.get('core_functions'):
                    player['core_functions'] = content[:300] + '...' if len(content) > 300 else content
        except Exception:
            pass

    def _parse_core_functions(self, content: str) -> str:
        """从内容中解析核心功能"""
        if not content or len(content) < 50:
            return "官网未提供详细信息"
        # 检查是否乱码（替换字符过多）
        if self._is_garbled(content):
            return "内容解析失败（编码问题）"
        # 清理乱码字符（显示为 ? 或 �）
        cleaned = self._clean_garbled(content)
        if len(cleaned) < 50:
            return "官网未提供详细信息"
        # 简单关键词匹配
        keywords = ['核心功能', '主要功能', '产品功能', '功能介绍', '解决方案', '库存管理', '财务管理', '订单管理']
        for kw in keywords:
            if kw in cleaned:
                # 找到关键词后的100-300字
                idx = cleaned.find(kw)
                snippet = cleaned[idx:idx+300]
                # 清理多余空白
                snippet = ' '.join(snippet.split())[:200]
                return snippet + "..." if len(snippet) >= 200 else snippet
        return cleaned[:150] + "..." if len(cleaned) >= 150 else cleaned

    def _parse_pricing(self, content: str) -> str:
        """从内容中解析定价模式"""
        if not content or len(content) < 50:
            return "官网未提供定价信息"
        # 检查是否乱码
        if self._is_garbled(content):
            return "定价信息解析失败（编码问题）"
        # 清理乱码字符
        cleaned = self._clean_garbled(content)
        if len(cleaned) < 50:
            return "官网未提供定价信息"

        # 跳过导航/标签链接模式（如 [文字](URL) 形式的导航）
        if self._is_navigation_content(cleaned):
            return "官网未提供定价信息"

        keywords = ['定价', '价格', '收费', '费用', '套餐', '版本', '元/', '元/年', '元/月', '元起', '元/人']
        for kw in keywords:
            if kw in cleaned:
                idx = cleaned.find(kw)
                snippet = cleaned[idx:idx+200]
                snippet = ' '.join(snippet.split())[:150]
                # 再次检查是否是导航
                if self._is_navigation_content(snippet):
                    continue
                return snippet + "..." if len(snippet) >= 150 else snippet
        return "官网未提供定价信息"

    def _is_navigation_content(self, content: str) -> bool:
        """检测是否是导航/标签类内容（非正文）"""
        if not content:
            return False
        # 统计导航模式的比例
        nav_patterns = [
            '](/',           # Markdown链接模式
            'tag-',          # 标签路径
            'article/',      # 文章路径
            'category/',     # 分类路径
        ]
        nav_count = sum(content.count(p) for p in nav_patterns)
        # 如果导航模式超过3个，或者超过内容长度的10%，认为是导航
        if nav_count > 3:
            return True
        if len(content) > 0 and nav_count / len(content) > 0.1:
            return True
        return False

    def _is_garbled(self, content: str) -> bool:
        """检测内容是否乱码"""
        if not content:
            return True
        # 统计替换字符和问号的比例
        replacement_count = content.count('�')  # �
        question_count = content.count('?')
        total_chars = len(content)
        if total_chars == 0:
            return True
        # 如果替换字符或问号超过5%，认为是乱码
        return (replacement_count + question_count) / total_chars > 0.05

    def _clean_garbled(self, content: str) -> str:
        """清理乱码字符，保留可读中文"""
        import re
        # 替换常见的乱码模式为空格
        # 移除控制字符但保留中文、英文、数字、常见标点
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', ' ', content)
        # 移除过多的问号（乱码标记）
        cleaned = re.sub(r'\?{3,}', ' ', cleaned)
        # 将非可打印字符序列替换为单空格（Windows代码页字符）
        cleaned = re.sub(r'[\x93\x94\x95\x96\x97\x98\x99\x9c\x9d\x9e\x9f\x91\x92]', ' ', cleaned)
        return cleaned

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