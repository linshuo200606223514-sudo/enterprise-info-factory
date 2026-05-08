#!/usr/bin/env python3
"""
百度搜索采集器
使用Playwright爬取百度搜索结果
"""

import asyncio
import json
import sys
import io
from pathlib import Path

# 设置stdout为utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright


async def search_baidu(company_name: str, timeout: int = 30000) -> dict:
    """
    使用Playwright爬取百度搜索结果

    Args:
        company_name: 公司名称
        timeout: 超时时间（毫秒）

    Returns:
        dict: 包含搜索结果和新闻的字典
    """
    results = {
        "source": "baidu_search",
        "company": company_name,
        "search_results": [],
        "news_results": [],
        "error": None
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            # 访问百度搜索
            search_url = f"https://www.baidu.com/s?wd={company_name}"
            await page.goto(search_url, timeout=timeout)

            # 等待搜索结果加载
            await page.wait_for_selector(".result, .c-container", timeout=timeout)

            # 提取搜索结果
            search_items = await page.query_selector_all(".result, .c-container")
            for item in search_items[:20]:  # 限制最多20条
                try:
                    title_elem = await item.query_selector("h3 a, h3.qb-something a, .c-title a")
                    if title_elem:
                        title = await title_elem.inner_text()
                        url = await title_elem.get_attribute("href")
                    else:
                        continue

                    # 提取摘要
                    abstract_elem = await item.query_selector(".c-abstract, .c-span-last, .result-footer")
                    abstract = await abstract_elem.inner_text() if abstract_elem else ""

                    if title and url:
                        results["search_results"].append({
                            "title": title.strip(),
                            "url": url.strip(),
                            "abstract": abstract.strip()
                        })
                except Exception:
                    continue

            # 提取新闻结果
            news_items = await page.query_selector_all(".c-title, .news-title, .c-blockitem")
            for item in news_items[:10]:  # 限制最多10条新闻
                try:
                    title_elem = await item.query_selector("a")
                    if title_elem:
                        title = await title_elem.inner_text()
                        news_url = await title_elem.get_attribute("href")
                        if title and news_url:
                            results["news_results"].append({
                                "title": title.strip(),
                                "url": news_url.strip()
                            })
                except Exception:
                    continue

        except Exception as e:
            results["error"] = str(e)

        finally:
            await browser.close()

    return results


async def main():
    """主入口"""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "请提供公司名称作为参数"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    company_name = sys.argv[1]
    result = await search_baidu(company_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
