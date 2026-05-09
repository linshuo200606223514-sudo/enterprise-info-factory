"""百度搜索模块"""
import sys
import json
import argparse
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
            # 清理结果中的控制字符，避免JSON解析错误
            cleaned = []
            for item in (results or []):
                cleaned_item = {}
                for k, v in item.items():
                    if isinstance(v, str):
                        # 移除控制字符，换行符等替换为空格
                        v = ''.join(c if ord(c) >= 32 else ' ' for c in v)
                    cleaned_item[k] = v
                cleaned.append(cleaned_item)
            return cleaned

if __name__ == "__main__":
    # 解析 keyword=xxx max_results=N 格式的命令行参数
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