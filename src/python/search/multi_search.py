"""搜索模块 - 支持多数据源"""
import os
import sys
import json
import urllib.parse
import asyncio
import subprocess
from typing import List, Dict, Optional
from playwright.async_api import async_playwright

class SearchResult:
    """搜索结果结构"""
    def __init__(self, title: str = "", url: str = "", abstract: str = "", source: str = ""):
        self.title = title
        self.url = url
        self.abstract = abstract
        self.source = source

    def to_dict(self) -> Dict:
        return {"title": self.title, "url": self.url, "abstract": self.abstract, "source": self.source}


class TavilySearch:
    """Tavily搜索 - 稳定的搜索API"""

    def __init__(self, max_results: int = 10):
        self.max_results = max_results
        self.api_key = os.getenv("TVLY_API_KEY")

    def search(self, keyword: str) -> List[Dict]:
        """使用Tavily搜索"""
        if not self.api_key:
            return []

        output_file = f"C:/tmp/tavily_search_{hash(keyword)}.json"
        cmd = f'tvly search "{keyword}" --max-results {self.max_results} -o {output_file}'

        try:
            subprocess.run(cmd, shell=True, capture_output=True, timeout=30)

            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            results = []
            for r in data.get('results', [])[:self.max_results]:
                results.append({
                    "title": r.get('title', ''),
                    "url": r.get('url', ''),
                    "abstract": r.get('content', '')[:200],
                    "source": "tavily"
                })

            # 清理临时文件
            if os.path.exists(output_file):
                os.remove(output_file)

            return results
        except Exception as e:
            print(f"Tavily搜索失败: {e}")
            return []


class BaiduSearch:
    """百度搜索执行器 - 备用数据源"""

    def __init__(self, max_results: int = 10):
        self.max_results = max_results
        self.blocked = False  # 标记是否被拦截

    def search(self, keyword: str) -> List[Dict]:
        """执行百度搜索"""
        return asyncio.run(self._search_async(keyword))

    async def _search_async(self, keyword: str) -> List[Dict]:
        """异步执行搜索"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # 设置更真实的UA
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })

            keyword_encoded = urllib.parse.quote(keyword)
            url = f"https://www.baidu.com/s?wd={keyword_encoded}&rn={self.max_results}"

            try:
                await page.goto(url, timeout=15000)
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(2)

                # 检查是否被安全验证拦截
                title = await page.title()
                if "安全" in title or "验证" in title:
                    self.blocked = True
                    return []

                results = await page.evaluate(f'''
                    () => {{
                        const items = [];
                        const selectors = [
                            '#content_left .result',
                            '#content_left .result-op',
                            '#content_left > div'
                        ];

                        let count = 0;
                        selectors.forEach(sel => {{
                            document.querySelectorAll(sel).forEach((el, i) => {{
                                if (count >= {self.max_results}) return;

                                const titleEl = el.querySelector('h3 a, .cosc-title a, .title-box a');
                                if (!titleEl) return;

                                // 尝试获取摘要
                                const absSelectors = ['p[class*=abstract]', 'div[class*=abstract]', '.c-abstract'];
                                let abstract = '';
                                for (const asel of absSelectors) {{
                                    const absEl = el.querySelector(asel);
                                    if (absEl) {{
                                        abstract = absEl.innerText.trim().slice(0, 200);
                                        break;
                                    }}
                                }}

                                items.push({{
                                    title: titleEl.innerText.trim().slice(0, 100),
                                    url: titleEl.href || '',
                                    abstract: abstract,
                                    source: 'baidu'
                                }});
                                count++;
                            }});
                        }});
                        return items;
                    }}
                ''')

                await browser.close()
                return results or []

            except Exception as e:
                print(f"百度搜索出错: {e}")
                await browser.close()
                self.blocked = True
                return []


class MultiSearch:
    """多数据源搜索聚合器"""

    def __init__(self, max_results_per_source: int = 10):
        self.max_results = max_results_per_source
        self.tavily = TavilySearch(max_results_per_source)
        self.baidu = BaiduSearch(max_results_per_source)

    def search(self, keyword: str) -> List[Dict]:
        """
        执行多数据源搜索

        优先使用Tavily（更稳定），如果Tavily失败则使用百度
        """
        results = []

        # 优先Tavily搜索
        tavily_results = self.tavily.search(keyword)
        if tavily_results:
            results.extend(tavily_results)
            print(f"Tavily搜索获得 {len(tavily_results)} 条结果")

        # 如果Tavily结果不足，补充百度结果
        if len(results) < self.max_results and not self.baidu.blocked:
            baidu_results = self.baidu.search(keyword)
            if baidu_results:
                # 去重（根据title）
                existing_titles = set(r['title'] for r in results)
                new_results = [r for r in baidu_results if r['title'] not in existing_titles]
                results.extend(new_results)
                print(f"百度搜索补充 {len(new_results)} 条结果")

        # 限制总数
        return results[:self.max_results]


def search_company(company_name: str, max_results: int = 10) -> List[Dict]:
    """便捷函数：搜索公司信息"""
    searcher = MultiSearch(max_results)
    return searcher.search(company_name)


if __name__ == "__main__":
    keyword = None
    max_results = 10

    for arg in sys.argv[1:]:
        if arg.startswith("keyword="):
            keyword = arg.split("=", 1)[1]
        elif arg.startswith("max_results="):
            max_results = int(arg.split("=", 1)[1])

    if not keyword:
        print("Error: keyword is required")
        sys.exit(1)

    results = search_company(keyword, max_results)
    print(json.dumps(results, ensure_ascii=False))