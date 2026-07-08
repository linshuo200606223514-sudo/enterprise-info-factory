"""百度搜索模块"""
import sys
import json
import urllib.parse
import asyncio
from playwright.async_api import async_playwright
from typing import List, Dict

class BaiduSearch:
    """百度搜索执行器"""

    def __init__(self, max_results: int = 10):
        self.max_results = max_results

    def search(self, keyword: str) -> List[Dict]:
        """执行百度搜索并返回结构化结果"""
        return asyncio.run(self._search_async(keyword))

    async def _search_async(self, keyword: str) -> List[Dict]:
        """异步执行搜索"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            keyword_encoded = urllib.parse.quote(keyword)
            url = f"https://www.baidu.com/s?wd={keyword_encoded}&rn={self.max_results}"

            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)  # 等待动态内容加载

            results = await page.evaluate(f'''
                () => {{
                    const items = [];
                    // 选择所有可能的搜索结果容器
                    const selectors = [
                        '#content_left .result',
                        '#content_left .result-op',
                        '#content_left > div'
                    ];

                    let count = 0;
                    selectors.forEach(sel => {{
                        document.querySelectorAll(sel).forEach((el, i) => {{
                            if (count >= {self.max_results}) return;

                            // 获取标题：尝试多种选择器
                            const titleSelectors = [
                                'h3 a',
                                '.cosc-title a',
                                '.title-box a',
                                '[class*=title] a'
                            ];
                            let titleEl = null;
                            for (const ts of titleSelectors) {{
                                const found = el.querySelector(ts);
                                if (found) {{ titleEl = found; break; }}
                            }}

                            if (!titleEl) return;

                            // 获取摘要：尝试多种选择器
                            const absSelectors = [
                                'p[class*=abstract]',
                                'div[class*=abstract]',
                                '.c-abstract',
                                '[class*=summary]',
                                '[class*=desc]',
                                'span[class*=info]'
                            ];
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
                                abstract: abstract
                            }});
                            count++;
                        }});
                    }});
                    return items;
                }}
            ''')

            await browser.close()
            return results or []


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

    searcher = BaiduSearch(max_results=max_results)
    results = searcher.search(keyword)
    print(json.dumps(results, ensure_ascii=False))