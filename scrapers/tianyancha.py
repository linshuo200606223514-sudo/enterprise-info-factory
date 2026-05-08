#!/usr/bin/env python3
"""
天眼查采集器
使用Playwright爬取天眼查公开企业信息
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


async def extract_employee_count(page) -> int:
    """从天眼查详情页提取员工人数"""
    # 尝试多种选择器
    selectors = [
        ".employee-count",
        ".staff-count",
        ".num-employment",
        "[class*='employee']",
        "[class*='staff']",
        ".company-index-item:nth-child(5) .num",
        ".info-col:contains('人员规模')"
    ]

    for selector in selectors:
        try:
            elem = await page.query_selector(selector)
            if elem:
                text = await elem.inner_text()
                # 提取数字
                import re
                match = re.search(r'(\d+)', text)
                if match:
                    return int(match.group(1))
        except:
            continue

    # 尝试从页面文本中查找
    try:
        content = await page.content()
        import re
        # 匹配 "人员规模：XXX人" 或 "员工：XXX人" 等模式
        patterns = [
            r'人员规模[：:]\s*(\d+)',
            r'员工[：:]\s*(\d+)',
            r'人员[：:]\s*(\d+)',
            r'(\d+)\s*人\s*$'
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return int(match.group(1))
    except:
        pass

    return None


async def search_tianyancha(company_name: str, timeout: int = 30000) -> dict:
    """
    使用Playwright爬取天眼查企业信息

    Args:
        company_name: 公司名称
        timeout: 超时时间（毫秒）

    Returns:
        dict: 包含企业基本信息的字典
    """
    results = {
        "source": "tianyancha",
        "company": company_name,
        "data": {
            "company_name": company_name,
            "legal_representative": None,
            "registered_capital": None,
            "establishment_date": None,
            "business_status": None,
            "unified_social_credit_code": None,
            "registration_authority": None,
            "company_type": None,
            "address": None,
            "employee_count": None
        },
        "requires_login": False,
        "error": None
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        try:
            # 访问天眼查搜索页
            search_url = f"https://www.tianyancha.com/search?key={company_name}"
            await page.goto(search_url, timeout=timeout)

            # 等待页面加载
            await page.wait_for_load_state("networkidle", timeout=timeout)

            # 检查是否需要登录
            login_selector = ".login-btn, .login-modal, [class*='login']"
            login_elem = await page.query_selector(login_selector)
            if login_elem:
                results["requires_login"] = True

            # 尝试提取搜索结果列表中的公司信息
            company_items = await page.query_selector_all(".search-result-company, .company-item, .search-item")

            if company_items:
                # 取第一个搜索结果
                first_company = company_items[0]

                # 提取公司名称
                name_elem = await first_company.query_selector(".company-name, .name, [class*='name']")
                if name_elem:
                    results["data"]["company_name"] = await name_elem.inner_text()

                # 提取法人代表
                legal_elem = await first_company.query_selector(".legal-person, .legal-person-name, [class*='legal']")
                if legal_elem:
                    results["data"]["legal_representative"] = await legal_elem.inner_text()

                # 提取注册资本
                capital_elem = await first_company.query_selector(".registered-capital, .capital, [class*='capital']")
                if capital_elem:
                    results["data"]["registered_capital"] = await capital_elem.inner_text()

                # 提取成立日期
                date_elem = await first_company.query_selector(".establishment-date, .date, [class*='date']")
                if date_elem:
                    results["data"]["establishment_date"] = await date_elem.inner_text()

                # 提取经营状态
                status_elem = await first_company.query_selector(".business-status, .status, [class*='status']")
                if status_elem:
                    results["data"]["business_status"] = await status_elem.inner_text()

            # 如果搜索结果为空，尝试从页面中提取更多信息
            if not company_items or results["data"]["company_name"] == company_name:
                # 尝试直接访问公司详情页
                detail_link = await page.query_selector("a[href*='/company/']")
                if detail_link:
                    detail_url = await detail_link.get_attribute("href")
                    if detail_url and not detail_url.startswith("javascript"):
                        await page.goto(detail_url, timeout=timeout)
                        await page.wait_for_load_state("networkidle", timeout=timeout)

                        # 提取详细信息
                        # 公司名称
                        name_elem = await page.query_selector(".company-name, .name-content, [class*='name']")
                        if name_elem:
                            results["data"]["company_name"] = await name_elem.inner_text()

                        # 法人代表
                        legal_elem = await page.query_selector(".legal-person-name, [class*='legal-person']")
                        if legal_elem:
                            results["data"]["legal_representative"] = await legal_elem.inner_text()

                        # 注册资本
                        capital_elem = await page.query_selector(".registered-capital, [class*='capital']")
                        if capital_elem:
                            results["data"]["registered_capital"] = await capital_elem.inner_text()

                        # 成立日期
                        date_elem = await page.query_selector(".establishment-date, [class*='establishment']")
                        if date_elem:
                            results["data"]["establishment_date"] = await date_elem.inner_text()

                        # 经营状态
                        status_elem = await page.query_selector(".business-status, [class*='status']")
                        if status_elem:
                            results["data"]["business_status"] = await status_elem.inner_text()

                        # 统一社会信用代码
                        credit_elem = await page.query_selector(".credit-code, [class*='credit']")
                        if credit_elem:
                            results["data"]["unified_social_credit_code"] = await credit_elem.inner_text()

                        # 登记机关
                        authority_elem = await page.query_selector(".registration-authority, [class*='authority']")
                        if authority_elem:
                            results["data"]["registration_authority"] = await authority_elem.inner_text()

                        # 公司类型
                        type_elem = await page.query_selector(".company-type, [class*='company-type']")
                        if type_elem:
                            results["data"]["company_type"] = await type_elem.inner_text()

                        # 地址
                        address_elem = await page.query_selector(".address, [class*='address']")
                        if address_elem:
                            results["data"]["address"] = await address_elem.inner_text()

                        # 员工人数
                        employee_count = await extract_employee_count(page)
                        if employee_count:
                            results["data"]["employee_count"] = employee_count

        except Exception as e:
            results["error"] = str(e)

        finally:
            await browser.close()

    # 清理数据，去除空白字符
    for key, value in results["data"].items():
        if isinstance(value, str):
            results["data"][key] = value.strip()

    return results


async def main():
    """主入口"""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "请提供公司名称作为参数"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    company_name = sys.argv[1]
    result = await search_tianyancha(company_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())