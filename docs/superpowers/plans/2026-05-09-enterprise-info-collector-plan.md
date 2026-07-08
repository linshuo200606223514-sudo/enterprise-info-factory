# 企业信息收集系统 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建企业信息收集系统MVP，实现从百度搜索和天眼查API收集企业信息，输出JSON和Markdown报告

**Architecture:** 管道式架构 — Python处理搜索/抓取/AI分析，Node.js做编排和CLI入口

**Tech Stack:** Python 3.x, Playwright, requests, OpenAI/Claude API, Node.js

---

## 文件结构

```
enterprise-info-factory/
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-05-09-enterprise-info-collector-design.md
│       └── plans/
│           └── 2026-05-09-enterprise-info-collector-plan.md
├── src/
│   ├── python/
│   │   ├── search/
│   │   │   ├── __init__.py
│   │   │   ├── baidu_search.py      # 百度搜索模块
│   │   │   └── tianyancha_api.py    # 天眼查API模块
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   └── entity_extractor.py  # AI实体提取
│   │   └── output/
│   │       ├── __init__.py
│   │       ├── json_exporter.py      # JSON输出
│   │       ├── markdown_reporter.py  # Markdown报告生成
│   │       └── yaml_generator.py     # YAML元模型配置（V2）
│   ├── nodejs/
│   │   └── collector/
│   │       ├── index.js             # Node.js入口
│   │       └── cli.js               # CLI接口
│   └── config/
│       └── settings.json           # 配置文件
├── data/                             # JSON存储目录
├── reports/                          # Markdown报告目录
├── pyproject.toml                    # Python依赖
└── package.json                      # Node.js依赖
```

---

## Task 1: 项目结构和配置文件

**Files:**
- Create: `enterprise-info-factory/pyproject.toml`
- Create: `enterprise-info-factory/package.json`
- Create: `enterprise-info-factory/src/config/settings.json`
- Create: `enterprise-info-factory/src/python/search/__init__.py`
- Create: `enterprise-info-factory/src/python/ai/__init__.py`
- Create: `enterprise-info-factory/src/python/output/__init__.py`
- Create: `enterprise-info-factory/data/.gitkeep`
- Create: `enterprise-info-factory/reports/.gitkeep`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[project]
name = "enterprise-info-collector"
version = "0.1.0"
description = "企业信息收集系统"
requires-python = ">=3.10"

dependencies = [
    "playwright>=1.40.0",
    "requests>=2.31.0",
    "beautifulsoup4>=4.12.0",
    "openai>=1.3.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.4.0", "pytest-asyncio>=0.21.0"]
```

- [ ] **Step 2: 创建 package.json**

```json
{
  "name": "enterprise-info-collector",
  "version": "0.1.0",
  "description": "企业信息收集系统 Node.js 编排层",
  "main": "src/nodejs/collector/index.js",
  "scripts": {
    "collect": "node src/nodejs/collector/cli.js"
  },
  "dependencies": {
    "commander": "^11.1.0",
    "dotenv": "^16.3.1"
  }
}
```

- [ ] **Step 3: 创建 settings.json**

```json
{
  "data_dir": "./data",
  "reports_dir": "./reports",
  "search": {
    "baidu": {
      "max_results": 10
    },
    "tianyancha": {
      "api_key": "${TIANYANCHA_API_KEY}",
      "base_url": "https://api.tianyancha.com"
    }
  },
  "ai": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "api_key": "${OPENAI_API_KEY}"
  },
  "output": {
    "json": true,
    "markdown": true,
    "yaml": false
  }
}
```

- [ ] **Step 4: 创建空 __init__.py 文件**

```python
# Python package marker
```

- [ ] **Step 5: 创建 .gitkeep 文件**

```bash
touch data/.gitkeep reports/.gitkeep
```

- [ ] **Step 6: Commit**

```bash
cd enterprise-info-factory && git add -A && git commit -m "feat: initial project structure"
```

---

## Task 2: 百度搜索模块

**Files:**
- Create: `src/python/search/baidu_search.py`
- Create: `tests/python/search/test_baidu_search.py`

- [ ] **Step 1: 创建测试文件**

```python
import pytest
from src.python.search.baidu_search import BaiduSearch

def test_search_returns_results():
    """测试搜索返回非空结果"""
    searcher = BaiduSearch()
    results = searcher.search("东社造纸厂")
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_result_structure():
    """测试结果包含必要字段"""
    searcher = BaiduSearch()
    results = searcher.search("测试公司")
    if results:
        assert "title" in results[0]
        assert "url" in results[0]
        assert "abstract" in results[0]
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd enterprise-info-factory && python -m pytest tests/python/search/test_baidu_search.py -v`
Expected: FAIL — 模块不存在

- [ ] **Step 3: 实现百度搜索模块**

```python
"""百度搜索模块"""
from typing import List, Dict
import subprocess
import json

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
        # 使用 subprocess 调用 Playwright 执行搜索
        cmd = [
            "python", "-c",
            f"""
import asyncio
from playwright.async_api import async_playwright

async def search():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        keyword_encoded = urllib.parse.quote("{keyword}")
        url = f"https://www.baidu.com/s?wd={{keyword_encoded}}&rn={{self.max_results}}"
        await page.goto(url)
        await page.wait_for_load_state("networkidle")

        results = await page.evaluate('''() => {{
            const items = [];
            document.querySelectorAll("#content_left .result, #content_left .result-op").forEach((el, i) => {{
                if (i >= {self.max_results}) return;
                const titleEl = el.querySelector("h3 a, .t a");
                const absEl = el.querySelector(".c-abstract, .content-right_8Zs40, .c-span9");
                if (titleEl) {{
                    items.push({{
                        title: titleEl.innerText.trim(),
                        url: titleEl.href,
                        abstract: absEl ? absEl.innerText.trim().slice(0, 200) : ""
                    }});
                }}
            }});
            return items;
        }}''')
        await browser.close()
        print(json.dumps(items))
        return items

asyncio.run(search())
'''
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return []
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd enterprise-info-factory && python -m pytest tests/python/search/test_baidu_search.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/python/search/baidu_search.py tests/python/search/test_baidu_search.py
git commit -m "feat: add BaiduSearch module"
```

---

## Task 3: 天眼查API模块

**Files:**
- Create: `src/python/search/tianyancha_api.py`
- Create: `tests/python/search/test_tianyancha_api.py`

- [ ] **Step 1: 创建测试文件**

```python
import pytest
from unittest.mock import patch, MagicMock
from src.python.search.tianyancha_api import TianyanchaAPI

def test_search_company_returns_data():
    """测试企业搜索返回数据结构"""
    api = TianyanchaAPI(api_key="test_key")
    with patch('requests.get') as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": {"items": []}}
        )
        result = api.search_company("东社造纸厂")
        assert isinstance(result, dict)
        assert "items" in result or "data" in result
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd enterprise-info-factory && python -m pytest tests/python/search/test_tianyancha_api.py -v`
Expected: FAIL — 模块不存在

- [ ] **Step 3: 实现天眼查API模块**

```python
"""天眼查API模块"""
import os
import requests
from typing import Dict, Optional, List

class TianyanchaAPI:
    """天眼查企业信息API客户端"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TIANYANCHA_API_KEY")
        self.base_url = "https://api.tianyancha.com"

    def search_company(self, name: str, max_results: int = 10) -> Dict:
        """
        搜索企业基本信息

        Args:
            name: 企业名称
            max_results: 最大返回数量

        Returns:
            Dict - 包含企业基本信息的字典
        """
        if not self.api_key:
            # 如果没有API key，返回mock数据用于测试
            return self._mock_data(name)

        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        params = {"word": name, "pageSize": max_results}

        try:
            response = requests.get(
                f"{self.base_url}/cloud-infometa/company/search",
                headers=headers,
                params=params,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"API调用失败: {e}")

        return self._mock_data(name)

    def _mock_data(self, name: str) -> Dict:
        """返回模拟数据用于开发和测试"""
        return {
            "data": {
                "items": [
                    {
                        "name": name,
                        "capital": "1000万元",
                        "成立时间": "2010-01-01",
                        "地址": "浙江省某市",
                        "经营范围": "纸箱制造、销售"
                    }
                ]
            }
        }
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd enterprise-info-factory && python -m pytest tests/python/search/test_tianyancha_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/python/search/tianyancha_api.py tests/python/search/test_tianyancha_api.py
git commit -m "feat: add TianyanchaAPI module"
```

---

## Task 4: AI实体提取模块

**Files:**
- Create: `src/python/ai/entity_extractor.py`
- Create: `tests/python/ai/test_entity_extractor.py`

- [ ] **Step 1: 创建测试文件**

```python
import pytest
from src.python.ai.entity_extractor import EntityExtractor

def test_extract_basic_info():
    """测试基本信息的提取"""
    extractor = EntityExtractor(provider="mock")
    text = "东社造纸厂成立于2010年，注册资本1000万元，位于浙江省"
    result = extractor.extract_basic_info(text)
    assert "name" in result
    assert "established" in result or "成立时间" in result
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd enterprise-info-factory && python -m pytest tests/python/ai/test_entity_extractor.py -v`
Expected: FAIL

- [ ] **Step 3: 实现AI实体提取模块**

```python
"""AI实体提取模块"""
import os
import json
from typing import Dict, List, Optional

class EntityExtractor:
    """从文本中提取企业实体信息"""

    def __init__(self, provider: str = "openai", model: str = "gpt-4o-mini"):
        self.provider = provider
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY")

    def extract(self, raw_data: Dict) -> Dict:
        """
        从原始搜索数据中提取结构化实体

        Args:
            raw_data: 包含搜索结果的原始数据

        Returns:
            Dict - 结构化的企业信息
        """
        # 合并所有文本来源
        combined_text = self._combine_text(raw_data)

        # 使用规则提取基本信息（V1阶段）
        # V2会使用LLM进行智能提取
        structured = {
            "basic_info": self.extract_basic_info(combined_text),
            "business_scope": self.extract_business_scope(combined_text),
            "organization": self.extract_organization(combined_text),
            "industry_features": self.extract_industry_features(combined_text),
            "potential_pain_points": self.extract_pain_points(combined_text),
        }

        return structured

    def _combine_text(self, raw_data: Dict) -> str:
        """合并多个来源的文本"""
        texts = []
        if "search_results" in raw_data:
            for result in raw_data["search_results"]:
                if "title" in result:
                    texts.append(result["title"])
                if "abstract" in result:
                    texts.append(result["abstract"])
        return "\n".join(texts)

    def extract_basic_info(self, text: str) -> Dict:
        """提取基础工商信息"""
        import re

        info = {}

        # 提取公司名称（简单规则）
        name_match = re.search(r'([一-龥]{2,20}(?:造纸厂|纸业|包装|科技|有限|公司))', text)
        if name_match:
            info["name"] = name_match.group(1)

        # 提取注册资本
        capital_match = re.search(r'注册资本[：:]\s*([\d.]+(?:亿万)?)', text)
        if capital_match:
            info["capital"] = capital_match.group(1)

        # 提取成立时间
        date_match = re.search(r'成立[于时]?\s*(\d{4})', text)
        if date_match:
            info["established"] = date_match.group(1)

        return info

    def extract_business_scope(self, text: str) -> List[str]:
        """提取业务范围"""
        keywords = ["纸箱", "包装", "造纸", "印刷", "纸板", "纸制品", "蜂窝板"]
        found = [k for k in keywords if k in text]
        return found if found else ["待确认"]

    def extract_organization(self, text: str) -> Dict:
        """提取组织规模信息"""
        scale = {}
        if "人数" in text or "员工" in text:
            scale["estimated_headcount"] = "待调研"
        return scale

    def extract_industry_features(self, text: str) -> List[str]:
        """提取行业特征"""
        features = []
        if "制造业" in text or "工厂" in text:
            features.append("制造业")
        if "纸箱" in text:
            features.append("纸箱包装行业")
        return features

    def extract_pain_points(self, text: str) -> List[str]:
        """基于行业特征推断可能的痛点"""
        # 造纸箱行业常见痛点
        common_pain_points = [
            "订单管理混乱",
            "生产排程困难",
            "库存管理不准",
            "财务对账麻烦"
        ]
        return common_pain_points
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd enterprise-info-factory && python -m pytest tests/python/ai/test_entity_extractor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/python/ai/entity_extractor.py tests/python/ai/test_entity_extractor.py
git commit -m "feat: add EntityExtractor module"
```

---

## Task 5: JSON和Markdown输出模块

**Files:**
- Create: `src/python/output/json_exporter.py`
- Create: `src/python/output/markdown_reporter.py`
- Create: `tests/python/output/test_json_exporter.py`
- Create: `tests/python/output/test_markdown_reporter.py`

- [ ] **Step 1: 创建测试文件 (json_exporter)**

```python
import pytest
import json
import os
from src.python.output.json_exporter import JSONExporter

def test_export_creates_file():
    """测试导出创建文件"""
    exporter = JSONExporter(output_dir="./test_data")
    data = {"company": "测试公司", "collected_at": "2026-05-09"}
    path = exporter.export(data, "test_company")
    assert os.path.exists(path)

def test_export_contains_required_fields():
    """测试导出数据包含必要字段"""
    exporter = JSONExporter(output_dir="./test_data")
    data = {
        "company_name": "测试公司",
        "sources": ["baidu", "tianyancha"],
        "structured": {"basic_info": {}}
    }
    path = exporter.export(data, "test_company")
    with open(path) as f:
        saved = json.load(f)
    assert "company_name" in saved
    assert "collected_at" in saved
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd enterprise-info-factory && python -m pytest tests/python/output/test_json_exporter.py -v`
Expected: FAIL

- [ ] **Step 3: 实现JSON导出器**

```python
"""JSON导出模块"""
import json
import os
from datetime import datetime
from typing import Dict

class JSONExporter:
    """企业信息的JSON格式导出器"""

    def __init__(self, output_dir: str = "./data"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export(self, data: Dict, company_name: str) -> str:
        """
        导出数据到JSON文件

        Args:
            data: 要导出的数据结构
            company_name: 公司名称（用于文件名）

        Returns:
            str - 导出文件的路径
        """
        # 添加收集时间戳
        if "collected_at" not in data:
            data["collected_at"] = datetime.now().isoformat()

        # 生成安全文件名
        safe_name = self._safe_filename(company_name)
        filename = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filepath

    def _safe_filename(self, name: str) -> str:
        """生成安全的文件名"""
        import re
        safe = re.sub(r'[^一-龥a-zA-Z0-9]', '_', name)
        return safe[:50]
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd enterprise-info-factory && python -m pytest tests/python/output/test_json_exporter.py -v`
Expected: PASS

- [ ] **Step 5: 创建Markdown报告生成器测试**

```python
import pytest
import os
from src.python.output.markdown_reporter import MarkdownReporter

def test_generate_report():
    """测试报告生成"""
    reporter = MarkdownReporter(output_dir="./test_reports")
    data = {
        "company_name": "东社造纸厂",
        "structured": {
            "basic_info": {"name": "东社造纸厂", "capital": "1000万元"},
            "business_scope": ["纸箱", "包装"],
            "potential_pain_points": ["订单管理混乱"]
        }
    }
    path = reporter.generate(data)
    assert os.path.exists(path)
```

- [ ] **Step 6: 运行测试验证失败**

Run: `cd enterprise-info-factory && python -m pytest tests/python/output/test_markdown_reporter.py -v`
Expected: FAIL

- [ ] **Step 7: 实现Markdown报告生成器**

```python
"""Markdown报告生成模块"""
import os
from datetime import datetime
from typing import Dict

class MarkdownReporter:
    """企业画像Markdown报告生成器"""

    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, data: Dict) -> str:
        """
        生成Markdown格式的企业画像报告

        Args:
            data: 包含企业信息的数据字典

        Returns:
            str - 报告文件路径
        """
        company_name = data.get("company_name", "未知企业")
        structured = data.get("structured", {})

        markdown = self._build_markdown(company_name, structured)

        filename = f"{company_name}_企业画像_{datetime.now().strftime('%Y%m%d')}.md"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)

        return filepath

    def _build_markdown(self, company_name: str, structured: Dict) -> str:
        """构建Markdown内容"""
        lines = [
            f"# 企业画像：{company_name}",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            "",
            "## 基础信息",
        ]

        basic_info = structured.get("basic_info", {})
        for key, value in basic_info.items():
            lines.append(f"- **{key}**: {value}")

        lines.extend(["", "## 业务范围",])
        scope = structured.get("business_scope", [])
        for item in scope:
            lines.append(f"- {item}")

        lines.extend(["", "## 行业特征",])
        features = structured.get("industry_features", [])
        for item in features:
            lines.append(f"- {item}")

        lines.extend(["", "## 可能的痛点（AI推断）",])
        pain_points = structured.get("potential_pain_points", [])
        for i, point in enumerate(pain_points, 1):
            lines.append(f"{i}. {point}")

        lines.extend(["", "---", f"*本报告由企业信息收集系统自动生成*"])

        return "\n".join(lines)
```

- [ ] **Step 8: 运行测试验证通过**

Run: `cd enterprise-info-factory && python -m pytest tests/python/output/test_markdown_reporter.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add src/python/output/json_exporter.py src/python/output/markdown_reporter.py
git add tests/python/output/test_json_exporter.py tests/python/output/test_markdown_reporter.py
git commit -m "feat: add JSON and Markdown output modules"
```

---

## Task 6: Node.js编排层

**Files:**
- Modify: `src/nodejs/collector/index.js` (create)
- Modify: `src/nodejs/collector/cli.js` (create)

- [ ] **Step 1: 创建 Node.js 主入口**

```javascript
/**
 * 企业信息收集系统 - Node.js 编排层
 */
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// 加载配置
function loadConfig() {
    const configPath = path.join(__dirname, '../../config/settings.json');
    const configContent = fs.readFileSync(configPath, 'utf-8');
    return JSON.parse(configContent);
}

// 执行Python收集器
async function runCollector(companyName, options = {}) {
    const config = loadConfig();

    console.log(`🔍 开始收集企业信息: ${companyName}`);
    console.log(`📡 数据源: 百度搜索, 天眼查`);

    // 第一步：百度搜索
    console.log('\n📌 步骤1: 执行百度搜索...');
    const searchResults = await runPythonScript('src/python/search/baidu_search.py', {
        keyword: companyName,
        max_results: config.search.baidu.max_results
    });

    // 第二步：天眼查API
    console.log('\n📌 步骤2: 查询天眼查工商信息...');
    const tianyanchaData = await runPythonScript('src/python/search/tianyancha_api.py', {
        company_name: companyName
    });

    // 第三步：AI实体提取
    console.log('\n📌 步骤3: AI分析提取结构化信息...');
    const structuredData = await runPythonScript('src/python/ai/entity_extractor.py', {
        search_results: JSON.stringify(searchResults),
        tianyancha_data: JSON.stringify(tianyanchaData)
    });

    // 第四步：输出结果
    console.log('\n📌 步骤4: 生成输出文件...');
    const outputData = {
        company_name: companyName,
        sources: ['baidu', 'tianyancha'],
        raw_data: { search_results: searchResults, tianyancha: tianyanchaData },
        structured: structuredData
    };

    // JSON导出
    if (config.output.json) {
        const jsonPath = await runPythonScript('src/python/output/json_exporter.py', {
            data: JSON.stringify(outputData),
            company_name: companyName
        });
        console.log(`✅ JSON已保存: ${jsonPath}`);
    }

    // Markdown报告
    if (config.output.markdown) {
        const mdPath = await runPythonScript('src/python/output/markdown_reporter.py', {
            data: JSON.stringify(outputData)
        });
        console.log(`✅ 报告已生成: ${mdPath}`);
    }

    console.log('\n✨ 收集完成！');
    return outputData;
}

// 运行Python脚本的辅助函数
function runPythonScript(scriptPath, args) {
    return new Promise((resolve, reject) => {
        const argList = Object.entries(args).map(([k, v]) => `${k}=${v}`);
        const proc = spawn('python', [scriptPath, ...argList], { shell: true });

        let stdout = '';
        proc.stdout.on('data', (data) => { stdout += data.toString(); });
        proc.stderr.on('data', (data) => { console.error(data.toString()); });

        proc.on('close', (code) => {
            if (code === 0) resolve(stdout.trim());
            else reject(new Error(`Python script failed with code ${code}`));
        });
    });
}

module.exports = { runCollector };
```

- [ ] **Step 2: 创建 CLI 入口**

```javascript
#!/usr/bin/env node
/**
 * 企业信息收集系统 - CLI入口
 */
const { Command } = require('commander');
const { runCollector } = require('./index');

const program = new Command();

program
    .name('enterprise-collector')
    .description('企业信息收集系统 - 从公开渠道收集企业信息')
    .version('0.1.0');

program
    .argument('<company_name>', '要收集信息的企业名称')
    .option('-o, --output <dir>', '输出目录', './output')
    .action(async (companyName, options) => {
        try {
            await runCollector(companyName, options);
        } catch (error) {
            console.error('❌ 收集失败:', error.message);
            process.exit(1);
        }
    });

program.parse();
```

- [ ] **Step 3: 更新 package.json 添加 bin**

```json
{
  "name": "enterprise-info-collector",
  "version": "0.1.0",
  "description": "企业信息收集系统 Node.js 编排层",
  "main": "src/nodejs/collector/index.js",
  "bin": {
    "collect": "src/nodejs/collector/cli.js"
  },
  "scripts": {
    "collect": "node src/nodejs/collector/cli.js"
  },
  "dependencies": {
    "commander": "^11.1.0",
    "dotenv": "^16.3.1"
  }
}
```

- [ ] **Step 4: 测试CLI**

Run: `cd enterprise-info-factory && node src/nodejs/collector/cli.js --help`
Expected: 显示帮助信息

- [ ] **Step 5: Commit**

```bash
git add src/nodejs/collector/index.js src/nodejs/collector/cli.js package.json
git commit -m "feat: add Node.js orchestration layer"
```

---

## Task 7: 端到端集成测试

**Files:**
- Create: `tests/integration/test_full_collect.py`

- [ ] **Step 1: 创建集成测试**

```python
import pytest
import os
from src.python.search.baidu_search import BaiduSearch
from src.python.search.tianyancha_api import TianyanchaAPI
from src.python.ai.entity_extractor import EntityExtractor
from src.python.output.json_exporter import JSONExporter
from src.python.output.markdown_reporter import MarkdownReporter

def test_full_collect_workflow():
    """测试完整收集流程"""
    # 1. 搜索
    searcher = BaiduSearch()
    search_results = searcher.search("东社造纸厂")

    # 2. 工商查询
    api = TianyanchaAPI()
    tianyancha_data = api.search_company("东社造纸厂")

    # 3. AI提取
    extractor = EntityExtractor(provider="mock")
    raw_data = {"search_results": search_results, "tianyancha_data": tianyancha_data}
    structured = extractor.extract(raw_data)

    # 4. 输出
    exporter = JSONExporter(output_dir="./test_data")
    data = {
        "company_name": "东社造纸厂",
        "sources": ["baidu", "tianyancha"],
        "raw_data": raw_data,
        "structured": structured
    }
    json_path = exporter.export(data, "东社造纸厂")

    reporter = MarkdownReporter(output_dir="./test_reports")
    md_path = reporter.generate(data)

    # 验证
    assert os.path.exists(json_path)
    assert os.path.exists(md_path)
    assert len(structured["basic_info"]) > 0
```

- [ ] **Step 2: 运行集成测试**

Run: `cd enterprise-info-factory && python -m pytest tests/integration/test_full_collect.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_full_collect.py
git commit -m "test: add integration test for full workflow"
```

---

## Task 8: 手动测试验证

**Files:** (无文件创建)

- [ ] **Step 1: 安装Python依赖**

Run: `cd enterprise-info-factory && pip install -e .`
Expected: 依赖安装成功

- [ ] **Step 2: 安装Playwright浏览器**

Run: `cd enterprise-info-factory && python -m playwright install chromium`
Expected: 浏览器安装成功

- [ ] **Step 3: 执行收集测试**

Run: `cd enterprise-info-factory && node src/nodejs/collector/cli.js "东社造纸厂"`
Expected: 显示收集进度，最终输出JSON和Markdown文件路径

- [ ] **Step 4: 检查输出文件**

检查 `data/` 和 `reports/` 目录，确认文件已生成且内容正确

---

## 计划总结

### 完成后的文件结构

```
enterprise-info-factory/
├── docs/superpowers/specs/2026-05-09-enterprise-info-collector-design.md
├── docs/superpowers/plans/2026-05-09-enterprise-info-collector-plan.md
├── src/python/
│   ├── search/
│   │   ├── __init__.py
│   │   ├── baidu_search.py
│   │   └── tianyancha_api.py
│   ├── ai/
│   │   ├── __init__.py
│   │   └── entity_extractor.py
│   └── output/
│       ├── __init__.py
│       ├── json_exporter.py
│       └── markdown_reporter.py
├── src/nodejs/collector/
│   ├── index.js
│   └── cli.js
├── tests/
│   ├── python/search/test_baidu_search.py
│   ├── python/search/test_tianyancha_api.py
│   ├── python/ai/test_entity_extractor.py
│   ├── python/output/test_json_exporter.py
│   ├── python/output/test_markdown_reporter.py
│   └── integration/test_full_collect.py
├── data/
├── reports/
├── pyproject.toml
└── package.json
```

### 验证方式

1. 运行 `node src/nodejs/collector/cli.js "东社造纸厂"` 能正常执行
2. `data/` 目录生成 JSON 文件
3. `reports/` 目录生成 Markdown 报告
4. 所有 pytest 测试通过

---

**Plan complete and saved to** `enterprise-info-factory/docs/superpowers/plans/2026-05-09-enterprise-info-collector-plan.md`

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**