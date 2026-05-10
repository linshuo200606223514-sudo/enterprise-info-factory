"""行业研究报告生成器 - 专注行业研究，不聚焦具体企业"""
import os
import sys
import json
import re
import subprocess
import time
from typing import Dict, List, Tuple
from datetime import datetime

from ai.website_extractor import WebsiteContentExtractor

# 多关键词搜索维度配置
# 每个维度使用多个不同角度的关键词，覆盖更多数据源
SEARCH_DIMENSIONS = {
    "main": {
        "keywords": [
            "{keyword} 头部玩家 平台 官网 2026",
            "{keyword} 主流产品 品牌排行榜",
            "{keyword} 领先厂商 解决方案",
            "{keyword} 知名品牌 供应商",
        ],
        "max_per_keyword": 15,
        "output_file": "main.json",
    },
    "news": {
        "keywords": [
            "{keyword} 最新动态 行业新闻 2026",
            "{keyword} 产品发布 融资 收购 2026",
            "{keyword} 战略合作 技术突破",
        ],
        "max_per_keyword": 12,
        "output_file": "news.json",
    },
    "compare": {
        "keywords": [
            "{keyword} 竞品对比 推荐 选型",
            "{keyword} 哪个好 评测 对比",
            "{keyword} 十大品牌 排名榜",
        ],
        "max_per_keyword": 12,
        "output_file": "compare.json",
    },
    "trend": {
        "keywords": [
            "{keyword} 趋势 数字化转型 技术动态",
            "{keyword} 市场规模 报告 白皮书",
            "{keyword} 行业分析 研究报告",
        ],
        "max_per_keyword": 10,
        "output_file": "trend.json",
    },
    "community": {
        "keywords": [
            "{keyword} 用户体验 口碑 论坛 讨论",
            "{keyword} 案例分享 行业论坛",
            "{keyword} 用户评价 真实点评",
        ],
        "max_per_keyword": 10,
        "output_file": "community.json",
    },
}

class IndustryReportGenerator:
    """行业报告生成器"""

    def __init__(self, output_dir: str = None):
        # 默认输出到项目根目录的reports/文件夹
        if output_dir is None:
            # 从 src/python/industry_report.py 向上三级到项目根目录
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(root, "reports")
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.search_timings = {}  # 存储各路搜索耗时

    @staticmethod
    def get_default_output_dir() -> str:
        """获取默认输出目录路径"""
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
        """多关键词并行搜索 + 合并去重"""
        import concurrent.futures
        from collections import OrderedDict

        output_dir = "C:/tmp/industry_report"
        os.makedirs(output_dir, exist_ok=True)

        def run_keyword_search(dim_name: str, kw: str, max_results: int, idx: int) -> Tuple[str, str, float, List[Dict], bool]:
            """执行单个关键词搜索，返回(dim_name, keyword, elapsed, results, success)"""
            start = time.time()
            tmp_file = os.path.join(output_dir, f"_tmp_{dim_name}_{idx}.json")
            cmd = f'tvly search "{kw}" --max-results {max_results} -o {tmp_file}'
            try:
                subprocess.run(cmd, shell=True, capture_output=True, timeout=120)
                elapsed = time.time() - start
                data = self._load_json(tmp_file)
                results = data.get('results', [])
                # 清理临时文件
                try:
                    os.remove(tmp_file)
                except:
                    pass
                return (dim_name, kw, elapsed, results, True)
            except Exception as e:
                elapsed = time.time() - start
                print(f"  搜索失败 [{dim_name}/{idx}]: {e}")
                return (dim_name, kw, elapsed, [], False)

        # 构建所有关键词搜索任务
        all_tasks = []  # (dim_name, keyword, max_results, idx)
        for dim_name, dim_config in SEARCH_DIMENSIONS.items():
            for idx, kw_template in enumerate(dim_config["keywords"]):
                kw = kw_template.format(keyword=keyword)
                all_tasks.append((dim_name, kw, dim_config["max_per_keyword"], idx))

        # 并行执行所有关键词搜索
        print(f"  启动 {len(all_tasks)} 个关键词搜索任务...")
        self.search_timings = {}
        dim_results = {}  # dim_name -> list of (kw, results)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(run_keyword_search, dim_name, kw, max_r, idx): (dim_name, kw)
                for dim_name, kw, max_r, idx in all_tasks
            }
            for future in concurrent.futures.as_completed(futures):
                dim_name, kw = futures[future]
                result_dim, result_kw, elapsed, results, success = future.result()
                if dim_name not in dim_results:
                    dim_results[dim_name] = []
                dim_results[dim_name].append((result_kw, results))

                if dim_name not in self.search_timings:
                    self.search_timings[dim_name] = {"elapsed": 0, "success": True}
                self.search_timings[dim_name]["elapsed"] = max(
                    self.search_timings[dim_name]["elapsed"], elapsed
                )
                self.search_timings[dim_name]["success"] = self.search_timings[dim_name]["success"] and success

        # 合并每个维度的结果（按URL去重，保留最高分）
        for dim_name, dim_config in SEARCH_DIMENSIONS.items():
            kw_results = dim_results.get(dim_name, [])
            merged = OrderedDict()  # url -> result (保留最高分)

            for kw, results in kw_results:
                for r in results:
                    url = r.get('url', '')
                    if not url:
                        continue
                    # 排除乱码和导航内容
                    title = r.get('title', '')
                    if self._is_garbled(title) or self._is_navigation_content(title):
                        continue
                    # 已有该URL且分数更高则跳过
                    if url in merged and merged[url].get('score', 0) >= r.get('score', 0):
                        continue
                    merged[url] = r

            # 保存合并后的结果
            merged_list = list(merged.values())
            output_file = os.path.join(output_dir, dim_config["output_file"])
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({"results": merged_list}, f, ensure_ascii=False)

            status = "[OK]" if self.search_timings.get(dim_name, {}).get("success") else "[FAIL]"
            elapsed = self.search_timings.get(dim_name, {}).get("elapsed", 0)
            print(f"  {status} {dim_name} search completed in {elapsed:.1f}s ({len(merged_list)} results after dedup)")

        # 分析搜索结果质量
        self._analyze_search_quality()

    def _analyze_search_quality(self) -> None:
        """分析各路搜索结果的质量 - 基于内容可用性评估"""
        output_dir = "C:/tmp/industry_report"
        self.search_quality = {}

        for dim_name, dim_config in SEARCH_DIMENSIONS.items():
            filepath = os.path.join(output_dir, dim_config["output_file"])
            data = self._load_json(filepath)
            results = data.get('results', [])

            if not results:
                self.search_quality[dim_name] = {
                    "status": "empty", "count": 0,
                    "valid_count": 0, "garbled": 0, "nav_heavy": 0,
                    "avg_score": 0, "quality_score": 0
                }
                continue

            # 基础指标
            total = len(results)
            garbled_count = sum(1 for r in results if self._is_garbled(r.get('title', '')))
            nav_count = sum(1 for r in results if self._is_navigation_content(r.get('title', '')))
            avg_score = sum(r.get('score', 0) for r in results) / total if total > 0 else 0

            # 可用结果：非乱码、非导航
            valid_count = total - garbled_count - nav_count
            valid_ratio = valid_count / total if total > 0 else 0

            # 域名多样性：统计不同域名数量
            domains = set()
            for r in results:
                domain = self._extract_domain(r.get('url', ''))
                if domain:
                    domains.add(domain)
            domain_diversity = len(domains)

            # 高质量结果比例（ Tavily score > 0.5）
            high_quality_count = sum(1 for r in results if r.get('score', 0) > 0.5)
            high_quality_ratio = high_quality_count / total if total > 0 else 0

            # 综合质量分：可用率 * 0.4 + 高质量率 * 0.3 + 域名多样性 * 0.15 + Tavily平均分 * 0.25
            # 域名多样性归一化：超过10个域名就认为多样性足够
            quality_score = (
                valid_ratio * 0.40 +
                high_quality_ratio * 0.30 +
                min(domain_diversity / 10, 1.0) * 0.15 +
                avg_score * 0.15
            )

            # status 判断基于综合质量分
            if quality_score >= 0.6:
                status = "good"
            elif quality_score >= 0.4:
                status = "warning"
            else:
                status = "poor"

            self.search_quality[dim_name] = {
                "count": total,
                "valid_count": valid_count,
                "avg_score": round(avg_score, 3),
                "quality_score": round(quality_score, 3),
                "garbled": garbled_count,
                "nav_heavy": nav_count,
                "domain_diversity": domain_diversity,
                "high_quality_count": high_quality_count,
                "status": status
            }

    def _load_json(self, filepath: str) -> Dict:
        """加载JSON文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            # JSON格式错误，尝试修复常见的转义问题后重试
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                # 清理BOM和控制字符
                content = content.replace('﻿', '').replace('​', '')
                # 修复不完整的转义（如果有用反斜杠转义的引号）
                content = content.replace('\\"', '"')
                # 尝试修复常见的JSON截断问题（截断到最后完整的对象）
                if content.strip().endswith(','):
                    content = content.rstrip(',')
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
            # 第一轮：并行提取前5个player的详情（主页+3内页）
            self._extract_player_details(top_players[:5])
            # 第二轮：为每个player执行专项搜索，获取更多上下文
            self._search_player_details(top_players[:5])

        report = {
            "industry": keyword,
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "search_timings": self.search_timings,
            "search_quality": self.search_quality,
            "top_players": top_players[:30],
            "latest_news": self._extract_news(news_data),
            "competitors": competitors,
            "trends": self._extract_trends(trend_data),
            "community": self._extract_community(community_data),
            "key_insights": self._generate_insights(main_data, news_data, compare_data, trend_data, top_players)
        }

        return report

    def _extract_player_details(self, players: List[Dict]) -> None:
        """对头部玩家URL提取详情（核心功能、定价模式）- 并行处理"""
        if not players:
            return

        import concurrent.futures
        from industry_markdown_reporter import IndustryMarkdownReporter

        output_dir = "C:/tmp/industry_report"
        os.makedirs(output_dir, exist_ok=True)

        # 并行提取每个player的详情
        def extract_single_player(player: Dict) -> Dict:
            """提取单个player的详情"""
            url = player.get('url', '')
            if not url:
                return player

            # 使用新的_fetch_with_scrapling（包含深度爬取）
            raw_content = self._fetch_with_scrapling(url, max_inner_pages=3)

            if raw_content and len(raw_content) > 100 and not self._is_garbled(raw_content):
                # 内容有效，用提取器分析
                extractor = WebsiteContentExtractor()
                result = extractor.extract(raw_content, url)
                player['core_functions'] = result.get('core_functions', '未提及')
                player['pricing'] = result.get('pricing', '未提及')
                player['target_users'] = result.get('target_users', '未提及')
                player['highlights'] = result.get('highlights', '未提及')
            elif raw_content:
                # 内容太短或乱码，尝试从原始内容中找关键词
                player['core_functions'] = self._parse_core_functions(raw_content)
                player['pricing'] = self._parse_pricing(raw_content)

            return player

        # 并行处理最多8个player（每个player会爬取3个内页）
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(extract_single_player, p): p for p in players[:8]}
            for future in concurrent.futures.as_completed(futures):
                updated_player = future.result()
                # player已经通过引用更新

    def _search_player_details(self, players: List[Dict]) -> None:
        """
        为每个player执行专项搜索，获取更多相关信息
        在已有主页内容基础上，通过搜索补充功能/定价信息
        """
        for player in players:
            name = player.get('name', '')
            if not name or len(name) < 4:
                continue
            # 构建专项搜索词：player名称 + 功能/定价关键词
            search_queries = [
                f"{name} 核心功能 主要功能",
                f"{name} 定价 价格 收费",
                f"{name} ERP 系统 功能介绍",
            ]
            for query in search_queries:
                self._search_single_player(query, player)

    def _search_single_player(self, query: str, player: Dict) -> None:
        """为单个player执行专项搜索并更新player信息"""
        import subprocess
        import json as json_lib

        output_dir = "C:/tmp/industry_report"
        tmp_file = os.path.join(output_dir, f"_player_search_{abs(hash(query)) % 10000}.json")

        try:
            cmd = f'tvly search "{query}" --max-results 3 -o {tmp_file}'
            subprocess.run(cmd, shell=True, capture_output=True, timeout=60)

            with open(tmp_file, 'r', encoding='utf-8') as f:
                data = json_lib.load(f)

            results = data.get('results', [])
            for r in results:
                # 如果搜索结果包含有用的功能/定价信息，更新player
                content = r.get('content', '')
                if content and len(content) > 50:
                    # 尝试提取功能信息
                    if '功能' in content or '系统' in content:
                        existing = player.get('core_functions', '')
                        if existing == '未提及' or len(existing) < len(content):
                            player['core_functions'] = content[:200]
                    # 尝试提取定价信息
                    if any(kw in content for kw in ['元', '价', '费', '套餐', '年费', '月租']):
                        existing = player.get('pricing', '')
                        if existing == '未提及' or len(existing) < len(content):
                            player['pricing'] = content[:150]
        except Exception:
            pass
        finally:
            try:
                os.remove(tmp_file)
            except:
                pass

    def _fetch_with_scrapling(self, url: str) -> str:
        """获取页面内容 - 使用requests直接获取原始HTML，正确处理编码"""
        try:
            import requests
            import re

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
            }
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()

            html = response.text

            content_parts = []

            # 提取标题
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
            if title_match:
                content_parts.append(f"标题: {title_match.group(1).strip()}")

            # 提取meta描述
            desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if not desc_match:
                desc_match = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']description["\']', html, re.IGNORECASE)
            if desc_match:
                content_parts.append(f"描述: {desc_match.group(1).strip()}")

            # 移除script和style标签
            html_clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html_clean = re.sub(r'<style[^>]*>.*?</style>', '', html_clean, flags=re.DOTALL | re.IGNORECASE)

            # 提取多类内容元素
            # 1. 段落文本
            for p in re.findall(r'<p[^>]*>(.*?)</p>', html_clean, re.DOTALL | re.IGNORECASE):
                text = re.sub(r'<[^>]+>', '', p).strip()
                if len(text) > 20 and self._has_chinese(text):
                    content_parts.append(text[:200])

            # 2. 列表项
            for li in re.findall(r'<li[^>]*>(.*?)</li>', html_clean, re.DOTALL | re.IGNORECASE):
                text = re.sub(r'<[^>]+>', '', li).strip()
                if len(text) > 5 and self._has_chinese(text):
                    content_parts.append(text[:150])

            # 3. 标题文本
            for h in re.findall(r'<h[1-6][^>]*>(.*?)</h[1-6]>', html_clean, re.DOTALL | re.IGNORECASE):
                text = re.sub(r'<[^>]+>', '', h).strip()
                if len(text) > 3 and self._has_chinese(text):
                    content_parts.append(text[:100])

            # 4. 表格单元格
            for td in re.findall(r'<td[^>]*>(.*?)</td>', html_clean, re.DOTALL | re.IGNORECASE):
                text = re.sub(r'<[^>]+>', '', td).strip()
                if len(text) > 10 and self._has_chinese(text):
                    content_parts.append(text[:150])

            # 5. div/span中的长文本
            for div in re.findall(r'<div[^>]*>(.*?)</div>', html_clean, re.DOTALL | re.IGNORECASE):
                text = re.sub(r'<[^>]+>', '', div).strip()
                if len(text) > 30 and self._has_chinese(text):
                    content_parts.append(text[:200])

            # 如果元素提取不足，补充段落模式
            if len(content_parts) < 3:
                for para in re.findall(r'[一-鿿][^\n]{20,}', html_clean):
                    if len(para) > 30 and len(content_parts) < 20:
                        content_parts.append(para[:200])

            result = ' '.join(content_parts) if content_parts else html_clean[:500]
            return result if len(result) > 50 else ""

        except Exception:
            return ""

    def _has_chinese(self, text: str) -> bool:
        """检查文本是否包含中文"""
        return bool(re.search(r'[一-鿿]', text))

    def _parse_core_functions(self, content: str) -> str:
        """从内容中解析核心功能"""
        if not content or len(content) < 50:
            return "官网未提供详细信息"
        if self._is_garbled(content):
            return "内容解析失败（编码问题）"
        cleaned = self._clean_garbled(content)
        if len(cleaned) < 50:
            return "官网未提供详细信息"

        keywords = ['核心功能', '主要功能', '产品功能', '功能介绍', '解决方案', '系统功能',
                    '库存管理', '财务管理', '订单管理', '采购管理', '销售管理', '生产管理',
                    '质量管理', '供应商管理', '客户管理', '人力资源', '报表分析', '数据分析',
                    '移动端', '云端', 'SaaS', '智能化', '自动化', '数字化', '信息化']
        for kw in keywords:
            if kw in cleaned:
                idx = cleaned.find(kw)
                snippet = cleaned[idx:idx+300]
                snippet = ' '.join(snippet.split())[:200]
                return snippet + "..." if len(snippet) >= 200 else snippet
        return cleaned[:150] + "..." if len(cleaned) >= 150 else cleaned

    def _parse_pricing(self, content: str) -> str:
        """从内容中解析定价模式"""
        if not content or len(content) < 50:
            return "官网未提供定价信息"
        if self._is_garbled(content):
            return "定价信息解析失败（编码问题）"
        cleaned = self._clean_garbled(content)
        if len(cleaned) < 50:
            return "官网未提供定价信息"

        if self._is_navigation_content(cleaned):
            return "官网未提供定价信息"

        keywords = ['定价', '价格', '收费', '费用', '套餐', '版本', '报价', '收费', '年费', '月费',
                    '元/', '元/年', '元/月', '元起', '元/人', '万元', '千元',
                    '免费', '试用', '折扣', '优惠', '多少钱', '怎么收费', '如何收费', '价格表']
        for kw in keywords:
            if kw in cleaned:
                idx = cleaned.find(kw)
                snippet = cleaned[idx:idx+200]
                snippet = ' '.join(snippet.split())[:150]
                if self._is_navigation_content(snippet):
                    continue
                return snippet + "..." if len(snippet) >= 150 else snippet
        return "官网未提供定价信息"

    def _fetch_with_scrapling(self, url: str, max_inner_pages: int = 3) -> str:
        """获取页面内容 - 使用requests直接获取原始HTML，正确处理编码"""
        try:
            import requests
            import re
            from urllib.parse import urljoin, urlparse

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
            }
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()

            html = response.text

            content_parts = []

            # 提取标题
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
            if title_match:
                content_parts.append(f"标题: {title_match.group(1).strip()}")

            # 提取meta描述
            desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if not desc_match:
                desc_match = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']description["\']', html, re.IGNORECASE)
            if desc_match:
                content_parts.append(f"描述: {desc_match.group(1).strip()}")

            # 移除script和style标签
            html_clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html_clean = re.sub(r'<style[^>]*>.*?</style>', '', html_clean, flags=re.DOTALL | re.IGNORECASE)

            # 提取多类内容元素
            # 1. 段落文本
            for p in re.findall(r'<p[^>]*>(.*?)</p>', html_clean, re.DOTALL | re.IGNORECASE):
                text = re.sub(r'<[^>]+>', '', p).strip()
                if len(text) > 20 and self._has_chinese(text):
                    content_parts.append(text[:200])

            # 2. 列表项
            for li in re.findall(r'<li[^>]*>(.*?)</li>', html_clean, re.DOTALL | re.IGNORECASE):
                text = re.sub(r'<[^>]+>', '', li).strip()
                if len(text) > 5 and self._has_chinese(text):
                    content_parts.append(text[:150])

            # 3. 标题文本
            for h in re.findall(r'<h[1-6][^>]*>(.*?)</h[1-6]>', html_clean, re.DOTALL | re.IGNORECASE):
                text = re.sub(r'<[^>]+>', '', h).strip()
                if len(text) > 3 and self._has_chinese(text):
                    content_parts.append(text[:100])

            # 4. 表格单元格
            for td in re.findall(r'<td[^>]*>(.*?)</td>', html_clean, re.DOTALL | re.IGNORECASE):
                text = re.sub(r'<[^>]+>', '', td).strip()
                if len(text) > 10 and self._has_chinese(text):
                    content_parts.append(text[:150])

            # 5. div/span中的长文本
            for div in re.findall(r'<div[^>]*>(.*?)</div>', html_clean, re.DOTALL | re.IGNORECASE):
                text = re.sub(r'<[^>]+>', '', div).strip()
                if len(text) > 30 and self._has_chinese(text):
                    content_parts.append(text[:200])

            # 如果元素提取不足，补充段落模式
            if len(content_parts) < 3:
                for para in re.findall(r'[一-鿿][^\n]{20,}', html_clean):
                    if len(para) > 30 and len(content_parts) < 20:
                        content_parts.append(para[:200])

            # 深度爬取：从主页面提取内链
            if max_inner_pages > 0:
                inner_links = self._find_inner_links(html, url)
                for inner_url in inner_links[:max_inner_pages]:
                    inner_content = self._fetch_single_page(inner_url)
                    if inner_content and len(inner_content) > 100:
                        content_parts.append(f"[内页] {inner_content}")

            result = ' '.join(content_parts) if content_parts else html_clean[:500]
            return result if len(result) > 50 else ""

        except Exception:
            return ""

    def _find_inner_links(self, html: str, base_url: str) -> List[str]:
        """从页面HTML中提取同域名的内链"""
        try:
            import re
            from urllib.parse import urljoin, urlparse

            parsed_base = urlparse(base_url)
            base_domain = parsed_base.netloc

            # 提取所有a标签的href
            hrefs = re.findall(r'<a[^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE)

            inner_links = []
            for href in hrefs:
                if not href or href.startswith('#') or href.startswith('javascript:'):
                    continue
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)

                # 只保留同域名链接
                if parsed.netloc == base_domain and parsed.scheme in ('http', 'https'):
                    # 过滤掉明显的导航/列表页
                    path = parsed.path.lower()
                    skip_patterns = ['/tag/', '/category/', '/article/', '/blog/page', '/news/page',
                                   '/page/', '/list', '/archive', '/sitemap', '/feed', '/tag']
                    if not any(p in path for p in skip_patterns):
                        inner_links.append(full_url)

            # 去重并返回
            return list(dict.fromkeys(inner_links))[:10]
        except Exception:
            return []

    def _fetch_single_page(self, url: str) -> str:
        """获取单个页面的内容（用于深度爬取）"""
        try:
            import requests
            import re

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            if response.status_code != 200:
                return ""

            html = response.text

            # 移除script和style
            html_clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html_clean = re.sub(r'<style[^>]*>.*?</style>', '', html_clean, flags=re.DOTALL | re.IGNORECASE)

            content_parts = []

            # 提取标题
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
            if title_match:
                content_parts.append(f"标题: {title_match.group(1).strip()}")

            # 提取段落
            for p in re.findall(r'<p[^>]*>(.*?)</p>', html_clean, re.DOTALL | re.IGNORECASE):
                text = re.sub(r'<[^>]+>', '', p).strip()
                if len(text) > 20 and self._has_chinese(text):
                    content_parts.append(text[:200])

            return ' '.join(content_parts)
        except Exception:
            return ""

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
        return players[:30]
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
        return news[:20]

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
        return competitors[:20]

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
        return community[:15]

    def _extract_trends(self, data: Dict) -> List[str]:
        """提取趋势"""
        results = data.get('results', [])
        trends = []
        for r in results:
            if r.get('title'):
                trends.append(r.get('title', ''))
        return trends[:15]

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