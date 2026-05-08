#!/usr/bin/env python3
"""
行业网站采集器 - 使用1688作为数据源
采集阿里巴巴上的企业信息、产品和行业行情
"""

import asyncio
import json
import sys
import io
from pathlib import Path

# 设置stdout为utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.async_api import async_playwright


async def scrape_1688_company(page, company_name: str, timeout: int = 30000) -> dict:
    """
    采集1688企业信息

    Args:
        page: Playwright页面对象
        company_name: 公司名称
        timeout: 超时时间

    Returns:
        dict: 企业信息字典
    """
    result = {
        "source": "1688",
        "company": company_name,
        "enterprise_info": {},
        "error": None
    }

    try:
        # 1688搜索URL
        search_url = f"https://s.1688.com/company/search.htm?keyword={company_name}&pageSize=20"
        await page.goto(search_url, timeout=timeout)
        await page.wait_for_load_state("domcontentloaded", timeout=timeout)

        # 等待搜索结果加载
        await asyncio.sleep(2)

        # 提取公司列表
        try:
            company_items = await page.query_selector_all(".company-list .company-item, .company-item")

            for item in company_items[:5]:
                try:
                    name_elem = await item.query_selector(".company-name, .name a, a.company-name")
                    if name_elem:
                        name = await name_elem.inner_text()
                        if company_name in name or any(c in name for c in company_name):
                            # 找到了匹配的公司，提取更多信息
                            result["enterprise_info"]["name"] = name.strip()

                            # 尝试获取详细信息
                            detail_link = await name_elem.get_attribute("href")
                            if detail_link:
                                result["enterprise_info"]["detail_url"] = detail_link

                            break
                except Exception:
                    continue

        except Exception as e:
            result["error"] = f"解析1688企业信息失败: {str(e)}"

    except Exception as e:
        result["error"] = f"访问1688失败: {str(e)}"

    return result


async def scrape_1688_products(page, company_name: str, timeout: int = 30000) -> dict:
    """
    采集1688产品信息

    Args:
        page: Playwright页面对象
        company_name: 公司名称
        timeout: 超时时间

    Returns:
        dict: 产品信息字典
    """
    result = {
        "source": "1688",
        "company": company_name,
        "products": [],
        "error": None
    }

    try:
        # 1688产品搜索
        search_url = f"https://s.1688.com/company/search.htm?keyword={company_name}%20纸箱&pageSize=20"
        await page.goto(search_url, timeout=timeout)
        await page.wait_for_load_state("domcontentloaded", timeout=timeout)
        await asyncio.sleep(2)

        # 提取产品列表
        try:
            product_items = await page.query_selector_all(".offer-list .offer-item, .product-item")

            for item in product_items[:10]:
                try:
                    title_elem = await item.query_selector(".offer-title, .product-title, .title")
                    price_elem = await item.query_selector(".price, .price-text, .offer-price")

                    if title_elem:
                        title = await title_elem.inner_text()
                        price = await price_elem.inner_text() if price_elem else ""

                        result["products"].append({
                            "title": title.strip(),
                            "price": price.strip() if price else "面议"
                        })
                except Exception:
                    continue
        except Exception as e:
            result["error"] = f"解析1688产品信息失败: {str(e)}"

    except Exception as e:
        result["error"] = f"访问1688产品页失败: {str(e)}"

    return result


async def scrape_news(page, company_name: str, timeout: int = 30000) -> dict:
    """
    从百度搜索采集行业新闻

    Args:
        page: Playwright页面对象
        company_name: 公司名称
        timeout: 超时时间

    Returns:
        dict: 新闻信息字典
    """
    result = {
        "source": "baidu_news",
        "company": company_name,
        "news": [],
        "error": None
    }

    try:
        # 百度新闻搜索
        search_url = f"https://www.baidu.com/s?wd={company_name}%20纸箱&tn=news"
        await page.goto(search_url, timeout=timeout)
        await page.wait_for_load_state("domcontentloaded", timeout=timeout)
        await asyncio.sleep(2)

        # 提取新闻
        try:
            news_items = await page.query_selector_all(".c-title a, .news-title")

            for item in news_items[:10]:
                try:
                    title = await item.inner_text()
                    url = await item.get_attribute("href")

                    if title:
                        result["news"].append({
                            "title": title.strip(),
                            "url": url.strip() if url else ""
                        })
                except Exception:
                    continue
        except Exception as e:
            result["error"] = f"解析新闻失败: {str(e)}"

    except Exception as e:
        result["error"] = f"访问百度新闻失败: {str(e)}"

    return result


async def collect_industry_info(company_name: str, timeout: int = 30000) -> dict:
    """
    主函数：采集行业信息

    Args:
        company_name: 公司名称
        timeout: 超时时间

    Returns:
        dict: 包含所有采集结果的字典
    """
    results = {
        "company": company_name,
        "enterprise_info": {},
        "products": [],
        "news": [],
        "errors": []
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            # 采集1688企业信息
            enterprise_result = await scrape_1688_company(page, company_name, timeout)
            if enterprise_result.get("enterprise_info"):
                results["enterprise_info"] = enterprise_result["enterprise_info"]
            if enterprise_result.get("error"):
                results["errors"].append(enterprise_result["error"])

            # 采集1688产品
            product_result = await scrape_1688_products(page, company_name, timeout)
            if product_result.get("products"):
                results["products"] = product_result["products"]
            if product_result.get("error"):
                results["errors"].append(product_result["error"])

            # 采集新闻
            news_result = await scrape_news(page, company_name, timeout)
            if news_result.get("news"):
                results["news"] = news_result["news"]
            if news_result.get("error"):
                results["errors"].append(news_result["error"])

        finally:
            await browser.close()

    return results


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "请提供公司名称作为参数"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    company_name = sys.argv[1]
    result = asyncio.run(collect_industry_info(company_name))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
