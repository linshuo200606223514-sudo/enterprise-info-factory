"""舆情分析模块 - 企业口碑和情感分析"""
import os
import sys
import json
import time
import random
import subprocess
from typing import Dict, List, Optional
from urllib.parse import urlparse

class SentimentAnalyzer:
    """舆情分析器 - 检测企业口碑和负面信息"""

    def __init__(self, company_name: str = ""):
        self.company_name = company_name
        # 负面关键词（造纸箱行业特定）
        self.negative_keywords = [
            "投诉", "污染", "环保", "违规", "处罚", "关停", "整改",
            "事故", "火灾", "爆炸", "纠纷", "举报", "欠薪", "质量",
            "欺骗", "欺诈", "跑路", "倒闭", "破产"
        ]
        # 正面关键词
        self.positive_keywords = [
            "优秀", "先进", "获奖", "认证", "好评", "推荐", "合作",
            "扩产", "投资", "创新", "绿色", "环保认证"
        ]

    def analyze(self, search_results: List[Dict]) -> Dict:
        """
        分析搜索结果的舆情

        Args:
            search_results: 搜索结果列表

        Returns:
            Dict - 舆情分析结果
        """
        if not search_results:
            return self._empty_result()

        total = len(search_results)
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        negative_items = []
        positive_items = []
        neutral_items = []

        for item in search_results:
            title = item.get('title', '')
            abstract = item.get('abstract', item.get('content', ''))
            url = item.get('url', '')
            text = f"{title} {abstract}"

            sentiment = self._classify_sentiment(title, abstract)

            entry = {
                "title": title,
                "url": url,
                "snippet": abstract[:100] if abstract else "",
                "source": self._extract_source(url)
            }

            if sentiment == "negative":
                negative_count += 1
                negative_items.append(entry)
            elif sentiment == "positive":
                positive_count += 1
                positive_items.append(entry)
            else:
                neutral_count += 1
                neutral_items.append(entry)

        # 计算情感得分 (-1 到 1)
        sentiment_score = (positive_count - negative_count) / max(total, 1)

        return {
            "total_mentions": total,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "sentiment_score": round(sentiment_score, 2),  # -1 到 1
            "sentiment_label": self._get_sentiment_label(sentiment_score),
            "negative_items": negative_items[:10],  # 限制数量
            "positive_items": positive_items[:10],
            "neutral_items": neutral_items[:10],
            "key_concerns": self._extract_key_concerns(negative_items),
            "praise_points": self._extract_praise_points(positive_items)
        }

    def _classify_sentiment(self, title: str, abstract: str) -> str:
        """分类单条信息的情感"""
        text = f"{title} {abstract}".lower()

        # 检查负面
        has_negative = any(kw in text for kw in self.negative_keywords)
        # 检查正面
        has_positive = any(kw in text for kw in self.positive_keywords)

        if has_negative and not has_positive:
            return "negative"
        elif has_positive and not has_negative:
            return "positive"
        elif has_negative and has_positive:
            return "mixed"
        else:
            return "neutral"

    def _get_sentiment_label(self, score: float) -> str:
        """根据得分获取情感标签"""
        if score >= 0.3:
            return "positive"
        elif score <= -0.3:
            return "negative"
        else:
            return "neutral"

    def _extract_source(self, url: str) -> str:
        """提取来源域名"""
        try:
            domain = urlparse(url).netloc.replace("www.", "")
            source_map = {
                "mp.weixin.qq.com": "微信公众号",
                "zhihu.com": "知乎",
                "baidu.com": "百度",
                "sina.com.cn": "新浪",
                "people.com.cn": "人民网",
                "gov.cn": "政府官网",
            }
            return next((v for k, v in source_map.items() if k in domain), domain or "未知")
        except:
            return "未知"

    def _extract_key_concerns(self, negative_items: List[Dict]) -> List[str]:
        """提取主要负面关切"""
        concerns = []
        for item in negative_items:
            title = item.get('title', '')
            for kw in self.negative_keywords:
                if kw in title.lower():
                    concerns.append(kw)
        # 统计出现频率
        from collections import Counter
        concern_counts = Counter(concerns)
        return [f"{kw}({count}次)" for kw, count in concern_counts.most_common(5)]

    def _extract_praise_points(self, positive_items: List[Dict]) -> List[str]:
        """提取正面评价点"""
        praises = []
        for item in positive_items:
            title = item.get('title', '')
            for kw in self.positive_keywords:
                if kw in title.lower():
                    praises.append(kw)
        from collections import Counter
        praise_counts = Counter(praises)
        return [f"{kw}({count}次)" for kw, count in praise_counts.most_common(5)]

    def _empty_result(self) -> Dict:
        """返回空结果"""
        return {
            "total_mentions": 0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "sentiment_score": 0,
            "sentiment_label": "unknown",
            "negative_items": [],
            "positive_items": [],
            "neutral_items": [],
            "key_concerns": [],
            "praise_points": []
        }


class MultiSourceSentimentSearch:
    """多数据源舆情搜索"""

    def __init__(self, company_name: str):
        self.company_name = company_name
        self.analyzer = SentimentAnalyzer(company_name)

    def search(self, keywords: List[str] = None) -> Dict:
        """
        执行多数据源舆情搜索

        Args:
            keywords: 可选，自定义关键词列表

        Returns:
            Dict - 包含搜索结果和舆情分析
        """
        if keywords is None:
            # 默认关键词组合
            keywords = [
                self.company_name,
                f"{self.company_name} 投诉",
                f"{self.company_name} 口碑",
                f"{self.company_name} 评价",
                f"{self.company_name} 新闻"
            ]

        all_results = []

        # 使用Tavily搜索每个关键词
        for kw in keywords:
            results = self._search_tavily(kw)
            all_results.extend(results)
            time.sleep(random.uniform(1, 2))

        # 去重
        seen_urls = set()
        unique_results = []
        for r in all_results:
            if r['url'] not in seen_urls:
                seen_urls.add(r['url'])
                unique_results.append(r)

        # 分析舆情
        sentiment_analysis = self.analyzer.analyze(unique_results)

        return {
            "company": self.company_name,
            "search_keywords": keywords,
            "total_results": len(unique_results),
            "search_results": unique_results[:50],  # 限制数量
            "sentiment_analysis": sentiment_analysis,
            "search_time": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def _search_tavily(self, keyword: str) -> List[Dict]:
        """使用Tavily搜索"""
        output_file = f"C:/tmp/sentiment_tavily_{hash(keyword)}.json"
        cmd = f'tvly search "{keyword}" --max-results 5 -o {output_file}'

        try:
            subprocess.run(cmd, shell=True, capture_output=True, timeout=30)

            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            results = []
            for r in data.get('results', [])[:5]:
                results.append({
                    "title": r.get('title', ''),
                    "url": r.get('url', ''),
                    "abstract": r.get('content', '')[:200],
                    "source": "tavily"
                })

            if os.path.exists(output_file):
                os.remove(output_file)

            return results
        except Exception as e:
            return []


def analyze_company_sentiment(company_name: str, search_results: List[Dict] = None) -> Dict:
    """
    便捷函数：分析公司舆情

    如果没有提供搜索结果，会自动进行多数据源搜索
    """
    analyzer = SentimentAnalyzer(company_name)

    if search_results is None:
        # 自动搜索
        searcher = MultiSourceSentimentSearch(company_name)
        result = searcher.search()
        return result
    else:
        # 分析已有结果
        return analyzer.analyze(search_results)


if __name__ == "__main__":
    company_name = None
    for arg in sys.argv[1:]:
        if arg.startswith("company_name="):
            company_name = arg.split("=", 1)[1]

    if not company_name:
        print("Error: company_name is required")
        sys.exit(1)

    result = analyze_company_sentiment(company_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))