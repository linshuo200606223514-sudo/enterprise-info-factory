#!/usr/bin/env python3
"""
行业网站采集器
采集纸业网、中国纸业网、包装网、纸张行情等网站信息
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


async def scrape_enterprise_info(page, company_name: str, timeout: int = 30000) -> dict:
    """
    采集纸业网 (paper.com) 企业信息

    Args:
        page: Playwright页面对象
        company_name: 公司名称
        timeout: 超时时间（毫秒）

    Returns:
        dict: 企业信息字典
    """
    result = {
        "source": "paper.com",
        "company": company_name,
        "enterprise_info": {},
        "error": None
    }

    try:
        # 构造搜索URL
        search_url = f"https://search.paper.com/search?keyword={company_name}"
        await page.goto(search_url, timeout=timeout)

        # 等待页面加载
        await page.wait_for_load_state("networkidle", timeout=timeout)

        # 提取企业信息（根据实际页面结构调整选择器）
        try:
            # 企业基本信息
            name_elem = await page.query_selector(".company-name, .enterprise-name, h1.title")
            if name_elem:
                result["enterprise_info"]["name"] = await name_elem.inner_text()

            # 联系方式
            contact_elem = await page.query_selector(".contact-info, .phone, .tel")
            if contact_elem:
                result["enterprise_info"]["contact"] = await contact_elem.inner_text()

            # 地址
            address_elem = await page.query_selector(".address, .location")
            if address_elem:
                result["enterprise_info"]["address"] = await address_elem.inner_text()

            # 主营产品
            products_elem = await page.query_selector(".products, .main-products, .business")
            if products_elem:
                result["enterprise_info"]["products"] = await products_elem.inner_text()

            # 企业简介
            desc_elem = await page.query_selector(".description, .intro, .about")
            if desc_elem:
                result["enterprise_info"]["description"] = await desc_elem.inner_text()

        except Exception as e:
            result["error"] = f"解析企业信息失败: {str(e)}"

    except Exception as e:
        result["error"] = f"访问纸业网失败: {str(e)}"

    return result


async def scrape_news(page, company_name: str, timeout: int = 30000) -> dict:
    """
    采集包装网 (baoye.cn) 行业新闻

    Args:
        page: Playwright页面对象
        company_name: 公司名称
        timeout: 超时时间（毫秒）

    Returns:
        dict: 新闻信息字典
    """
    result = {
        "source": "baoye.cn",
        "company": company_name,
        "news": [],
        "error": None
    }

    try:
        # 访问包装网搜索
        search_url = f"https://www.baoye.cn/search/?keyword={company_name}"
        await page.goto(search_url, timeout=timeout)
        await page.wait_for_load_state("networkidle", timeout=timeout)

        # 提取新闻列表
        try:
            news_items = await page.query_selector_all(".news-item, .article-item, .list-item")
            for item in news_items[:20]:
                try:
                    title_elem = await item.query_selector("a.title, h3 a, .news-title")
                    date_elem = await item.query_selector(".date, .time, .publish-time")
                    abstract_elem = await item.query_selector(".abstract, .summary, .desc")

                    if title_elem:
                        title = await title_elem.inner_text()
                        url = await title_elem.get_attribute("href")
                        date = await date_elem.inner_text() if date_elem else ""
                        abstract = await abstract_elem.inner_text() if abstract_elem else ""

                        result["news"].append({
                            "title": title.strip(),
                            "url": url.strip() if url else "",
                            "date": date.strip(),
                            "abstract": abstract.strip()
                        })
                except Exception:
                    continue
        except Exception as e:
            result["error"] = f"解析新闻列表失败: {str(e)}"

    except Exception as e:
        result["error"] = f"访问包装网失败: {str(e)}"

    return result


async def scrape_price(page, timeout: int = 30000) -> dict:
    """
    采集纸张行情 (paper.cn) 价格信息

    Args:
        page: Playwright页面对象
        timeout: 超时时间（毫秒）

    Returns:
        dict: 价格信息字典
    """
    result = {
        "source": "paper.cn",
        "prices": [],
        "error": None
    }

    try:
        # 访问纸张行情首页
        await page.goto("https://www.paper.cn/price", timeout=timeout)
        await page.wait_for_load_state("networkidle", timeout=timeout)

        # 提取价格行情数据
        try:
            price_items = await page.query_selector_all(".price-item, .market-price, .price-trend")
            for item in price_items[:30]:
                try:
                    product_elem = await item.query_selector(".product-name, .name, .paper-type")
                    price_elem = await item.query_selector(".price, .current-price, .amount")
                    trend_elem = await item.query_selector(".trend, .change, .up-down")

                    product = await product_elem.inner_text() if product_elem else ""
                    price = await price_elem.inner_text() if price_elem else ""
                    trend = await trend_elem.inner_text() if trend_elem else ""

                    if product:
                        result["prices"].append({
                            "product": product.strip(),
                            "price": price.strip(),
                            "trend": trend.strip()
                        })
                except Exception:
                    continue
        except Exception as e:
            result["error"] = f"解析价格数据失败: {str(e)}"

    except Exception as e:
        result["error"] = f"访问纸张行情失败: {str(e)}"

    return result


async def collect_industry_info(company_name: str, timeout: int = 30000) -> dict:
    """
    主函数：采集行业信息

    Args:
        company_name: 公司名称
        timeout: 超时时间（毫秒）

    Returns:
        dict: 包含所有采集结果的字典
    """
    results = {
        "company": company_name,
        "enterprise_info": {},
        "news": [],
        "prices": [],
        "errors": []
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            # 采集纸业网企业信息
            enterprise_result = await scrape_enterprise_info(page, company_name, timeout)
            if enterprise_result.get("enterprise_info"):
                results["enterprise_info"] = enterprise_result["enterprise_info"]
            if enterprise_result.get("error"):
                results["errors"].append(enterprise_result["error"])

            # 采集包装网新闻
            news_result = await scrape_news(page, company_name, timeout)
            if news_result.get("news"):
                results["news"] = news_result["news"]
            if news_result.get("error"):
                results["errors"].append(news_result["error"])

            # 采集纸张行情价格
            price_result = await scrape_price(page, timeout)
            if price_result.get("prices"):
                results["prices"] = price_result["prices"]
            if price_result.get("error"):
                results["errors"].append(price_result["error"])

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