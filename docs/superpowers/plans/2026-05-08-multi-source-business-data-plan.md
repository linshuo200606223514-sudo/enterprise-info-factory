# Multi-Source Business Data Collection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 接入企查查、爱企查、启信宝三个工商数据源，实现多源并行采集和标准化合并

**Architecture:** 每个数据源独立采集器（Python + Playwright），输出统一 JSON 格式，Node.js 聚合层按优先级合并结果

**Tech Stack:** Python 3, Playwright, Node.js, Express

---

## 文件结构

```
scrapers/
├── baidu_search.py       # 现有
├── tianyancha.py        # 现有
├── industry_sites.py     # 现有
├── qichacha.py           # 新增：企查查
├── aiqicha.py            # 新增：爱企查
└── qixin.py             # 新增：启信宝
```

---

## Task 1: 创建企查查采集器

**Files:**
- Create: `scrapers/qichacha.py`

- [ ] **Step 1: 编写企查查采集器**

```python
#!/usr/bin/env python3
"""
企查查采集器
使用Playwright爬取企查查公开企业信息
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
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
]

def random_ua():
    return random.choice(USER_AGENTS)


async def scrape_qichacha(company_name: str, timeout: int = 30000) -> dict:
    """采集企查查企业信息"""
    result = {
        "source": "qichacha",
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
            "shareholders": [],
            "investments": [],
            "judicial_risks": []
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
            search_url = f"https://www.qcc.com/search?key={company_name}"
            await page.goto(search_url, timeout=timeout)
            await page.wait_for_load_state("networkidle", timeout=timeout)
            await asyncio.sleep(random.uniform(1, 2))

            # 检查是否需要登录
            login_elem = await page.query_selector(".login-btn, .login-modal")
            if login_elem:
                result["requires_login"] = True

            # 提取搜索结果
            company_items = await page.query_selector_all(".search-result-item, .company-item")

            if company_items:
                first_company = company_items[0]

                # 公司名称
                name_elem = await first_company.query_selector(".company-name a, .bname a")
                if name_elem:
                    result["data"]["company_name"] = await name_elem.inner_text()

                # 法人代表
                legal_elem = await first_company.query_selector(".legal-person, .legal-person-name")
                if legal_elem:
                    result["data"]["legal_representative"] = await legal_elem.inner_text()

                # 注册资本
                capital_elem = await first_company.query_selector(".capital, .registered-capital")
                if capital_elem:
                    result["data"]["registered_capital"] = await capital_elem.inner_text()

                # 经营状态
                status_elem = await first_company.query_selector(".status, .business-status")
                if status_elem:
                    result["data"]["business_status"] = await status_elem.inner_text()

                # 点击进入详情页
                if name_elem:
                    detail_href = await name_elem.get_attribute("href")
                    if detail_href:
                        await page.goto(detail_href, timeout=timeout)
                        await page.wait_for_load_state("networkidle", timeout=timeout)
                        await asyncio.sleep(random.uniform(1, 2))

                        # 提取统一社会信用代码
                        credit_elem = await page.query_selector(".credit-code, [class*='credit']")
                        if credit_elem:
                            result["data"]["unified_social_credit_code"] = await credit_elem.inner_text()

                        # 提取地址
                        addr_elem = await page.query_selector(".address, [class*='address']")
                        if addr_elem:
                            result["data"]["address"] = await addr_elem.inner_text()

                        # 提取员工人数
                        employee_elem = await page.query_selector(".employee-count, .staff-num")
                        if employee_elem:
                            emp_text = await employee_elem.inner_text()
                            match = re.search(r'(\d+)', emp_text)
                            if match:
                                result["data"]["employee_count"] = int(match.group(1))

                        # 提取公司类型
                        type_elem = await page.query_selector(".company-type, [class*='company-type']")
                        if type_elem:
                            result["data"]["company_type"] = await type_elem.inner_text()

                        # 提取成立日期
                        date_elem = await page.query_selector(".establishment-date, [class*='establishment']")
                        if date_elem:
                            result["data"]["establishment_date"] = await date_elem.inner_text()

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
    result = await scrape_qichacha(company_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 测试企查查采集器**

Run: `python scrapers/qichacha.py "东社造纸厂"`
Expected: 输出 JSON 格式的企业信息

- [ ] **Step 3: Commit**

```bash
git add scrapers/qichacha.py
git commit -m "feat: add Qichacha scraper for business data collection"
```

---

## Task 2: 创建爱企查采集器

**Files:**
- Create: `scrapers/aiqicha.py`

- [ ] **Step 1: 编写爱企查采集器**

```python
#!/usr/bin/env python3
"""
爱企查采集器
使用Playwright爬取百度爱企查公开企业信息
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
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def random_ua():
    return random.choice(USER_AGENTS)


async def scrape_aiqicha(company_name: str, timeout: int = 30000) -> dict:
    """采集爱企查企业信息"""
    result = {
        "source": "aiqicha",
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
            "latitude": None,
            "longitude": None
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
            search_url = f"https://aiqicha.baidu.com/s?q={company_name}"
            await page.goto(search_url, timeout=timeout)
            await page.wait_for_load_state("networkidle", timeout=timeout)
            await asyncio.sleep(random.uniform(1, 2))

            # 检查登录
            login_elem = await page.query_selector(".login-btn")
            if login_elem:
                result["requires_login"] = True

            # 提取搜索结果
            company_items = await page.query_selector_all(".company-item, .result-item")

            if company_items:
                first_company = company_items[0]

                # 公司名称
                name_elem = await first_company.query_selector(".company-name, .title")
                if name_elem:
                    result["data"]["company_name"] = await name_elem.inner_text()

                # 法人代表
                legal_elem = await first_company.query_selector(".legal-person, .legal")
                if legal_elem:
                    result["data"]["legal_representative"] = await legal_elem.inner_text()

                # 注册资本
                capital_elem = await first_company.query_selector(".capital, .reg-capital")
                if capital_elem:
                    result["data"]["registered_capital"] = await capital_elem.inner_text()

                # 状态
                status_elem = await first_company.query_selector(".status, .business-status")
                if status_elem:
                    result["data"]["business_status"] = await status_elem.inner_text()

                # 地址
                addr_elem = await first_company.query_selector(".address, .addr")
                if addr_elem:
                    result["data"]["address"] = await addr_elem.inner_text()

                # 点击进入详情
                if name_elem:
                    detail_href = await name_elem.get_attribute("href")
                    if detail_href:
                        await page.goto(detail_href, timeout=timeout)
                        await page.wait_for_load_state("networkidle", timeout=timeout)
                        await asyncio.sleep(random.uniform(1, 2))

                        # 统一社会信用代码
                        credit_elem = await page.query_selector(".credit-code")
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
    result = await scrape_aiqicha(company_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 测试爱企查采集器**

Run: `python scrapers/aiqicha.py "东社造纸厂"`
Expected: 输出 JSON 格式的企业信息

- [ ] **Step 3: Commit**

```bash
git add scrapers/aiqicha.py
git commit -m "feat: add Aiqicha scraper for business data collection"
```

---

## Task 3: 创建启信宝采集器

**Files:**
- Create: `scrapers/qixin.py`

- [ ] **Step 1: 编写启信宝采集器**

```python
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
```

- [ ] **Step 2: 测试启信宝采集器**

Run: `python scrapers/qixin.py "东社造纸厂"`
Expected: 输出 JSON 格式的企业信息

- [ ] **Step 3: Commit**

```bash
git add scrapers/qixin.py
git commit -m "feat: add Qixin scraper for business data collection"
```

---

## Task 4: 实现数据合并服务

**Files:**
- Create: `api/services/dataMerger.js`

- [ ] **Step 1: 编写数据合并服务**

```javascript
// api/services/dataMerger.js
/**
 * 多源工商数据合并服务
 */

const FIELD_PRIORITY = {
  employee_count: ["qichacha", "qixin", "tianyancha", "aiqicha"],
  shareholders: ["qichacha", "qixin"],
  investments: ["qichacha", "qixin"],
  annual_revenue: ["qixin", "qichacha"],
  judicial_risks: ["qichacha"]
};

function deduplicate(list, keyFn = JSON.stringify) {
  const seen = new Set();
  return list.filter(item => {
    const key = keyFn(item);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function mergeList(existing, newItems) {
  if (!existing) return newItems || [];
  if (!newItems) return existing;
  return deduplicate([...existing, ...newItems]);
}

function mergeSingleValue(existing, newValue, priority, existingSource, newSource) {
  if (!newValue) return existing;
  if (!existing) return newValue;

  // 按优先级比较
  if (priority && existingSource && newSource) {
    const existingIdx = priority.indexOf(existingSource);
    const newIdx = priority.indexOf(newSource);
    if (newIdx !== -1 && (existingIdx === -1 || newIdx < existingIdx)) {
      return newValue;
    }
  }
  return existing;
}

function mergeCompanyData(sourcesData) {
  const merged = {
    company_name: null,
    legal_representative: null,
    registered_capital: null,
    employee_count: null,
    business_status: null,
    address: null,
    unified_social_credit_code: null,
    registration_authority: null,
    company_type: null,
    business_scope: null,
    establishment_date: null,
    annual_revenue: null,
    taxpayer_type: null,
    shareholders: [],
    investments: [],
    judicial_risks: [],
    _sources: {}
  };

  for (const sourceData of sourcesData) {
    if (!sourceData || !sourceData.data) continue;

    const sourceName = sourceData.source;
    const data = sourceData.data;

    // 简单字段：取非空值
    const simpleFields = [
      "company_name", "legal_representative", "registered_capital",
      "business_status", "address", "unified_social_credit_code",
      "registration_authority", "company_type", "business_scope",
      "establishment_date", "annual_revenue", "taxpayer_type"
    ];

    for (const field of simpleFields) {
      if (data[field]) {
        merged[field] = mergeSingleValue(
          merged[field],
          data[field],
          null,
          merged._sources[field],
          sourceName
        );
        if (data[field] && !merged._sources[field]) {
          merged._sources[field] = sourceName;
        }
      }
    }

    // 员工人数：按优先级
    if (data.employee_count) {
      const priority = FIELD_PRIORITY.employee_count;
      merged.employee_count = mergeSingleValue(
        merged.employee_count,
        data.employee_count,
        priority,
        merged._sources.employee_count,
        sourceName
      );
      merged._sources.employee_count = sourceName;
    }

    // 列表字段：合并去重
    if (data.shareholders) {
      merged.shareholders = mergeList(merged.shareholders, data.shareholders);
    }
    if (data.investments) {
      merged.investments = mergeList(merged.investments, data.investments);
    }
    if (data.judicial_risks) {
      merged.judicial_risks = mergeList(merged.judicial_risks, data.judicial_risks);
    }
  }

  return merged;
}

module.exports = { mergeCompanyData, deduplicate };
```

- [ ] **Step 2: 测试合并逻辑**

在 Node.js REPL 中测试：
```javascript
const { mergeCompanyData } = require('./api/services/dataMerger');
const testData = [
  { source: "tianyancha", data: { company_name: "测试公司", employee_count: 50 } },
  { source: "qichacha", data: { company_name: "测试公司", employee_count: 100 } },
  { source: "aiqicha", data: { company_name: "测试公司" } }
];
console.log(mergeCompanyData(testData));
// 应该显示 employee_count: 100（来自企查查，优先级更高）
```

- [ ] **Step 3: Commit**

```bash
git add api/services/dataMerger.js
git commit -m "feat: add multi-source data merger service"
```

---

## Task 5: 扩展 API 聚合入口

**Files:**
- Modify: `api/services/aggregator.js`

- [ ] **Step 1: 添加多源采集路由**

在 aggregator.js 中添加：

```javascript
// 多源工商数据采集
router.get('/collect/:companyName/all', async (req, res) => {
  const { companyName } = req.params;

  try {
    // 并行调用所有工商数据源
    const scrapers = [
      { name: 'qichacha', args: [companyName] },
      { name: 'aiqicha', args: [companyName] },
      { name: 'qixin', args: [companyName] },
      { name: 'tianyancha', args: [companyName] }
    ];

    const results = await Promise.allSettled(
      scrapers.map(scraper => runPythonScraper(scraper.name, scraper.args))
    );

    // 提取成功的结果
    const successResults = [];
    const errors = [];

    results.forEach((result, index) => {
      const scraperName = scrapers[index].name;
      if (result.status === 'fulfilled' && result.value && !result.value.error) {
        successResults.push(result.value);
      } else {
        errors.push({
          source: scraperName,
          error: result.reason?.message || result.value?.error || 'Unknown error'
        });
      }
    });

    // 合并数据
    const { mergeCompanyData } = require('./dataMerger');
    const mergedData = mergeCompanyData(successResults);

    res.json({
      success: true,
      data: {
        merged: mergedData,
        sources: successResults.map(r => r.source),
        source_count: successResults.length,
        errors: errors
      }
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});
```

- [ ] **Step 2: Commit**

```bash
git add api/services/aggregator.js
git commit -m "feat: add multi-source collection API endpoint"
```

---

## Task 6: 验收测试

**验证步骤:**

- [ ] **Step 1: 测试企查查采集器**

Run: `python scrapers/qichacha.py "汕头市澄海区溪南东社造纸厂"`
Expected: 输出包含企业信息的 JSON

- [ ] **Step 2: 测试爱企查采集器**

Run: `python scrapers/aiqicha.py "汕头市澄海区溪南东社造纸厂"`
Expected: 输出包含企业信息的 JSON

- [ ] **Step 3: 测试启信宝采集器**

Run: `python scrapers/qixin.py "汕头市澄海区溪南东社造纸厂"`
Expected: 输出包含企业信息的 JSON

- [ ] **Step 4: 测试多源 API**

确保服务器运行: `node server/index.js`
Run: `curl http://localhost:3000/api/collect/东社造纸厂/all`
Expected: 返回合并后的数据，包含多个 source

- [ ] **Step 5: 验证数据合并**

检查返回结果中：
- employee_count 来自优先级最高的数据源
- 列表字段（shareholders等）已去重

---

## 自检清单

1. **Spec 覆盖检查：**
   - [ ] 企查查采集器 - Task 1
   - [ ] 爱企查采集器 - Task 2
   - [ ] 启信宝采集器 - Task 3
   - [ ] 数据合并服务 - Task 4
   - [ ] API 入口扩展 - Task 5

2. **占位符检查：** 无 TBD/TODO

3. **反爬策略检查：**
   - [ ] User-Agent 轮换
   - [ ] 请求间隔随机化
   - [ ] 失败重试

4. **数据标准化检查：**
   - [ ] 所有采集器输出统一格式
   - [ ] 字段名称一致
