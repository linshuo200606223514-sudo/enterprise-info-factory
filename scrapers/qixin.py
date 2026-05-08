#!/usr/bin/env python3
"""
启信宝采集器
使用Playwright爬取启信宝公开企业信息
"""

import asyncio
import json
import sys
import io
import re
import random
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.async_api import async_playwright

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

def random_ua():
    return random.choice(USER_AGENTS)


async def scrape_qixin(company_name: str, timeout: int = 30000) -> dict:
    """采集启信宝企业信息"""
    result = {
        "source": "qixin",
        "company": company_name,
        "data": {
            "company_name": company_name,
            "legal_representative": None,
            "registered_capital": None,
            "employee_count": None,
            "business_status": None,
            "address": None,
            "unified_social_credit_code": None,
            "registration_authority": None,
            "company_type": None,
            "business_scope": None,
            "establishment_date": None,
            "annual_revenue": None,
            "taxpayer_type": None
        },
        "requires_login": False,
        "error": None
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=random_ua(),
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        try:
            search_url = f"https://www.qixin.com/search?key={company_name}"
            await page.goto(search_url, timeout=timeout)
            await page.wait_for_load_state("networkidle", timeout=timeout)
            await asyncio.sleep(random.uniform(1, 2))

            # 检查登录
            login_elem = await page.query_selector(".login-btn, .login-modal")
            if login_elem:
                result["requires_login"] = True

            # 提取搜索结果
            company_items = await page.query_selector_all(".company-list .company-item, .search-result .item")

            if company_items:
                first_company = company_items[0]

                # 公司名称
                name_elem = await first_company.query_selector(".company-name, .name")
                if name_elem:
                    result["data"]["company_name"] = await name_elem.inner_text()

                # 法人代表
                legal_elem = await first_company.query_selector(".legal-person, .legal")
                if legal_elem:
                    result["data"]["legal_representative"] = await legal_elem.inner_text()

                # 注册资本
                capital_elem = await first_company.query_selector(".registered-capital, .capital")
                if capital_elem:
                    result["data"]["registered_capital"] = await capital_elem.inner_text()

                # 经营状态
                status_elem = await first_company.query_selector(".business-status, .status")
                if status_elem:
                    result["data"]["business_status"] = await status_elem.inner_text()

                # 地址
                addr_elem = await first_company.query_selector(".address, .addr")
                if addr_elem:
                    result["data"]["address"] = await addr_elem.inner_text()

                # 点击进入详情
                if name_elem:
                    detail_href = await name_elem.get_attribute("href")
                    if detail_href and not detail_href.startswith("javascript"):
                        await page.goto(detail_href, timeout=timeout)
                        await page.wait_for_load_state("networkidle", timeout=timeout)
                        await asyncio.sleep(random.uniform(1, 2))

                        # 统一社会信用代码
                        credit_elem = await page.query_selector(".credit-code, [class*='credit']")
                        if credit_elem:
                            result["data"]["unified_social_credit_code"] = await credit_elem.inner_text()

                        # 成立日期
                        date_elem = await page.query_selector(".establishment-date, [class*='date']")
                        if date_elem:
                            result["data"]["establishment_date"] = await date_elem.inner_text()

                        # 公司类型
                        type_elem = await page.query_selector(".company-type")
                        if type_elem:
                            result["data"]["company_type"] = await type_elem.inner_text()

                        # 员工人数
                        emp_elem = await page.query_selector(".staff-num, .employee-count")
                        if emp_elem:
                            emp_text = await emp_elem.inner_text()
                            match = re.search(r'(\d+)', emp_text)
                            if match:
                                result["data"]["employee_count"] = int(match.group(1))

        except Exception as e:
            result["error"] = str(e)

        finally:
            await browser.close()

    # 清理数据
    for key, value in result["data"].items():
        if isinstance(value, str):
            result["data"][key] = value.strip()

    return result


async def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "请提供公司名称作为参数"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    company_name = sys.argv[1]
    result = await scrape_qixin(company_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())