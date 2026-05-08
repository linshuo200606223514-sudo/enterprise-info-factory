# 多源工商数据采集设计文档

> **状态：** 已批准

## 1. 目标

扩展数据采集能力，接入企查查(qcc.com)、爱企查(aiqicha.baidu.com)、启信宝(qixin.com)，实现工商数据的多源并行采集和标准化合并。

## 2. 架构概览

```
scrapers/
├── baidu_search.py       # 百度搜索（现有）
├── tianyancha.py         # 天眼查（现有）
├── industry_sites.py     # 1688行业站（现有）
├── qichacha.py           # 企查查（新增）
├── aiqicha.py            # 爱企查（新增）
└── qixin.py             # 启信宝（新增）
```

## 3. 数据标准化

### 3.1 统一数据格式

所有采集器输出统一格式，便于后续聚合：

```json
{
  "source": "qichacha",
  "company": "公司名称",
  "data": {
    "company_name": "公司全称",
    "legal_representative": "法定代表人",
    "registered_capital": "注册资本",
    "employee_count": 100,
    "business_status": "存续",
    "address": "注册地址",
    "unified_social_credit_code": "91110000XXXXXXXX",
    "registration_authority": "登记机关",
    "company_type": "有限责任公司",
    "business_scope": "经营范围",
    "establishment_date": "2010-01-01",
    "annual_revenue": "1000万",
    "taxpayer_type": "一般纳税人",
    "shareholders": [...],
    "investments": [...],
    "judicial_risks": [...],
    "administrative_penalties": [...]
  },
  "requires_login": false,
  "error": null
}
```

### 3.2 字段优先级映射

| 字段 | 优先级 | 来源 |
|------|--------|------|
| 基础工商信息 | 1 | 天眼查 |
| 员工规模 | 1 | 企查查 > 启信宝 > 天眼查 |
| 股东/股权结构 | 1 | 企查查 > 启信宝 |
| 财务数据 | 1 | 启信宝 > 企查查 |
| 司法风险 | 2 | 企查查 |
| 行政处罚 | 2 | 天眼查 |
| 年报信息 | 2 | 启信宝 |

## 4. 各数据源采集器设计

### 4.1 企查查 (qichacha.py)

**特点：** 功能全面，有企业族谱、股权结构穿透

**采集内容：**
- 基础工商信息
- 股东及股权比例
- 对外投资
- 法定代表人其他任职
- 司法风险（被执行人、失信人）
- 经营异常、行政处罚

**搜索URL：** `https://www.qcc.com/search?key={company_name}`

**关键选择器：**
```python
selectors = {
    "company_name": ".company-name, .bname",
    "legal_person": ".legal-person a",
    "capital": ".capital",
    "status": ".status",
    "employee_count": ".employee-count"
}
```

### 4.2 爱企查 (aiqicha.py)

**特点：** 百度系，免费额度多，舆情集成

**采集内容：**
- 基础工商信息
- 地图位置（经纬度）
- 舆情新闻关联
- 企业图谱（简化版）

**搜索URL：** `https://aiqicha.baidu.com/s?q={company_name}`

**关键选择器：**
```python
selectors = {
    "company_name": ".company-name, .title",
    "legal_person": ".legal-person",
    "capital": ".capital",
    "status": ".status",
    "address": ".address"
}
```

### 4.3 启信宝 (qixin.py)

**特点：** 数据更新快，财务数据全

**采集内容：**
- 基础工商信息
- 财务数据（营收、利润）
- 纳税人资质
- 税务信用等级
- 上下游关系

**搜索URL：** `https://www.qixin.com/search?key={company_name}`

**关键选择器：**
```python
selectors = {
    "company_name": ".company-name",
    "legal_person": ".legal-person",
    "capital": ".registered-capital",
    "status": ".business-status",
    "employee_count": ".staff-num",
    "financial": ".financial-data"
}
```

## 5. 聚合策略

### 5.1 数据合并规则

```python
def merge_company_data(sources_data: list) -> dict:
    """
    合并多源数据，按优先级取最优值
    """
    merged = {
        "company_name": None,
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
        "taxpayer_type": None,
        "shareholders": [],
        "investments": [],
        "judicial_risks": [],
        "_sources": {}
    }

    # 字段优先级
    field_priority = {
        "employee_count": ["qichacha", "qixin", "tianyancha"],
        "shareholders": ["qichacha", "qixin"],
        "annual_revenue": ["qixin", "qichacha"]
    }

    for source in sources_data:
        source_name = source.get("source")
        data = source.get("data", {})

        for field, value in data.items():
            if not value:
                continue

            # 检查是否需要特殊合并
            if field in ["shareholders", "investments", "judicial_risks"]:
                merged[field].extend(value)
            elif merged[field] is None:
                # 取第一个非空值
                merged[field] = value
            elif field in field_priority:
                # 按优先级替换
                current_source = merged[f"_sources"].get(field)
                if field_priority[field].index(source_name) < field_priority[field].index(current_source):
                    merged[field] = value
                    merged[f"_sources"][field] = source_name

    # 去重
    for field in ["shareholders", "investments", "judicial_risks"]:
        merged[field] = deduplicate_list(merged[field])

    return merged
```

### 5.2 容错机制

```python
async def collect_with_fallback(company_name: str) -> dict:
    """
    多源采集，任一源失败不影响整体
    """
    scrapers = [
        ("qichacha", scrape_qichacha),
        ("aiqicha", scrape_aiqicha),
        ("qixin", scrape_qixin),
        ("tianyancha", scrape_tianyancha)
    ]

    results = []
    errors = []

    for name, scraper_func in scrapers:
        try:
            result = await call_with_retry(scraper_func, company_name, max_retries=2)
            if result and not result.get("error"):
                results.append(result)
            else:
                errors.append({"source": name, "error": result.get("error")})
        except Exception as e:
            errors.append({"source": name, "error": str(e)})

    return {
        "results": results,
        "errors": errors,
        "success_count": len(results),
        "total": len(scrapers)
    }
```

## 6. 反爬应对策略

### 6.1 User-Agent 轮换

```python
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
]
```

### 6.2 请求间隔

```python
import random
import asyncio

async def polite_request(page, url):
    await asyncio.sleep(random.uniform(1, 3))  # 1-3秒随机间隔
    await page.goto(url)
```

### 6.3 失败重试

```python
async def call_with_retry(func, *args, max_retries=2, delay=1):
    for attempt in range(max_retries):
        try:
            result = await func(*args)
            if not result.get("error"):
                return result
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(delay * (attempt + 1))
```

## 7. API 扩展

在 `api/services/aggregator.js` 中新增多源采集入口：

```javascript
// 新增接口
router.get('/collect/:companyName/all', async (req, res) => {
  // 并行调用所有工商数据源
  const results = await Promise.allSettled([
    runPythonScraper('qichacha', [companyName]),
    runPythonScraper('aiqicha', [companyName]),
    runPythonScraper('qixin', [companyName]),
    runPythonScraper('tianyancha', [companyName])
  ]);
  // 合并结果
  const merged = mergeCompanyData(results);
  res.json({ success: true, data: merged });
});
```

## 8. 数据输出

采集结果保存到 `output/` 目录：

```
output/
├── {company}_qichacha.json      # 企查查原始数据
├── {company}_aiqicha.json       # 爱企查原始数据
├── {company}_qixin.json         # 启信宝原始数据
├── {company}_merged.json        # 合并后的完整数据
└── {company}_meta_config.json  # 元模型配置
```

## 9. 依赖

新增依赖：
```json
{
  "dependencies": {
    "playwright": "^1.40.0"
  }
}
```

## 10. 验收标准

- [ ] 企查查采集器能正确采集企业信息
- [ ] 爱企查采集器能正确采集企业信息
- [ ] 启信宝采集器能正确采集企业信息
- [ ] 多源数据能正确合并
- [ ] 单个源失败不影响整体流程
- [ ] 合并后的数据格式统一
- [ ] 反爬策略有效（请求间隔、UA轮换）
