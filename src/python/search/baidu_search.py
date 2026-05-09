"""百度搜索模块"""
from typing import List, Dict
import urllib.parse
import asyncio
from playwright.async_api import async_playwright

class BaiduSearch:
    """百度搜索执行器"""

    def __init__(self, max_results: int = 10):
        self.max_results = max_results

    def search(self, keyword: str) -> List[Dict]:
        """
        执行百度搜索并返回结构化结果

        Args:
            keyword: 搜索关键词

        Returns:
            List[Dict] - 搜索结果列表，每项包含 title, url, abstract
        """
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

            results = await page.evaluate(f'''
                () => {{
                    const items = [];
                    document.querySelectorAll("#content_left .result, #content_left .result-op").forEach((el, i) => {{
                        if (i >= {self.max_results}) return;
                        const titleEl = el.querySelector("h3 a, .t a");
                        const absEl = el.querySelector(".c-abstract, .content-right_8Yz40, .c-span9");
                        if (titleEl) {{
                            items.push({{
                                title: titleEl.innerText.trim(),
                                url: titleEl.href,
                                abstract: absEl ? absEl.innerText.trim().slice(0, 200) : ""
                            }});
                        }}
                    }});
                    return items;
                }}
            ''')

            await browser.close()
            return results if results else []