"""爱企查爬虫模块"""
import asyncio
import json
import sys
import io
import random
from typing import Dict, Optional
from playwright.async_api import async_playwright

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def random_ua():
    return random.choice(USER_AGENTS)

class AiqichaScraper:
    """爱企查企业信息爬虫"""

    def __init__(self, timeout: int = 30000):
        self.timeout = timeout

    def scrape(self, company_name: str) -> Dict:
        """同步接口，调用异步爬虫"""
        return asyncio.run(self._scrape_async(company_name))

    async def _scrape_async(self, company_name: str) -> Dict:
        """异步爬取企业信息"""
        result = {
            "source": "aiqicha",
            "company": company_name,
            "data": {},
            "success": False,
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
                search_url = f"https://aiqicha.baidu.com/s?q={company_name}"
                await page.goto(search_url, timeout=self.timeout)
                await page.wait_for_load_state("networkidle", timeout=self.timeout)
                await asyncio.sleep(random.uniform(1, 2))

                # 检查登录
                login_elem = await page.query_selector(".login-btn")
                if login_elem:
                    result["requires_login"] = True

                # 提取搜索结果
                company_items = await page.query_selector_all(".company-item, .result-item")

                if company_items:
                    first_company = company_items[0]
                    data = {}

                    # 公司名称
                    name_elem = await first_company.query_selector(".company-name, .title")
                    if name_elem:
                        data["company_name"] = (await name_elem.inner_text()).strip()

                    # 法人代表
                    legal_elem = await first_company.query_selector(".legal-person, .legal")
                    if legal_elem:
                        data["legal_representative"] = (await legal_elem.inner_text()).strip()

                    # 注册资本
                    capital_elem = await first_company.query_selector(".capital, .reg-capital")
                    if capital_elem:
                        data["registered_capital"] = (await capital_elem.inner_text()).strip()

                    # 员工数量
                    employee_elem = await first_company.query_selector(".employee-count, .staff")
                    if employee_elem:
                        data["employee_count"] = (await employee_elem.inner_text()).strip()

                    # 状态
                    status_elem = await first_company.query_selector(".status, .business-status")
                    if status_elem:
                        data["business_status"] = (await status_elem.inner_text()).strip()

                    # 地址
                    addr_elem = await first_company.query_selector(".address, .addr")
                    if addr_elem:
                        data["address"] = (await addr_elem.inner_text()).strip()

                    result["data"] = data
                    result["success"] = True

            except Exception as e:
                result["error"] = str(e)

            finally:
                await browser.close()

        return result


def scrape_company(company_name: str) -> Dict:
    """便捷函数：爬取公司信息"""
    scraper = AiqichaScraper()
    return scraper.scrape(company_name)


if __name__ == "__main__":
    company_name = None
    for arg in sys.argv[1:]:
        if arg.startswith("company_name="):
            company_name = arg.split("=", 1)[1]

    if not company_name:
        print("Error: company_name is required")
        sys.exit(1)

    result = scrape_company(company_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))