# Data Quality Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在数据合并后生成数据完整性报告，标记缺失字段和数据来源

**Architecture:** 在 dataMerger.js 中新增 generateDataQualityReport 函数，输出标准格式报告

**Tech Stack:** Node.js (纯 JavaScript)

---

## 文件结构

```
api/services/
├── dataMerger.js    # 修改：新增 generateDataQualityReport 函数
└── aggregator.js     # 修改：集成质量报告到 API 响应
```

---

## Task 1: 在 dataMerger.js 中新增报告生成函数

**Files:**
- Modify: `api/services/dataMerger.js`

- [ ] **Step 1: 新增 generateDataQualityReport 函数**

在 `dataMerger.js` 末尾添加：

```javascript
/**
 * 生成数据质量报告
 * @param {Object} mergedData - 合并后的数据（包含 _sources 字段）
 * @param {Array} sourcesData - 原始数据源列表
 * @returns {Object} 数据质量报告
 */
function generateDataQualityReport(mergedData, sourcesData) {
  const fields = [
    { key: "company_name", label: "企业名称", critical: true },
    { key: "legal_representative", label: "法人代表", critical: true },
    { key: "registered_capital", label: "注册资本", critical: false },
    { key: "employee_count", label: "员工人数", critical: false },
    { key: "business_status", label: "经营状态", critical: true },
    { key: "address", label: "地址", critical: false },
    { key: "unified_social_credit_code", label: "统一社会信用代码", critical: true },
    { key: "registration_authority", label: "登记机关", critical: false },
    { key: "company_type", label: "企业类型", critical: false },
    { key: "business_scope", label: "经营范围", critical: false },
    { key: "establishment_date", label: "成立日期", critical: false },
    { key: "annual_revenue", label: "年营收", critical: false },
    { key: "taxpayer_type", label: "纳税人资质", critical: false }
  ];

  const fieldReports = fields.map(f => ({
    key: f.key,
    label: f.label,
    critical: f.critical,
    populated: !!mergedData[f.key],
    value: mergedData[f.key],
    source: mergedData._sources ? mergedData._sources[f.key] : null
  }));

  const populatedCount = fieldReports.filter(f => f.populated).length;
  const totalCount = fields.length;
  const completenessScore = Math.round((populatedCount / totalCount) * 100);

  const criticalFields = fieldReports.filter(f => f.critical);
  const populatedCritical = criticalFields.filter(f => f.populated).length;

  return {
    summary: {
      total_fields: totalCount,
      populated_fields: populatedCount,
      completeness_score: completenessScore,
      critical_completeness: `${populatedCritical}/${criticalFields.length}`,
      sources_count: sourcesData.length,
      overall_status: completenessScore >= 80 ? "excellent" : completenessScore >= 60 ? "good" : "poor"
    },
    fields: fieldReports,
    sources: sourcesData.map(s => ({
      name: s.source,
      field_count: s.data ? Object.keys(s.data).filter(k => s.data[k] && k !== '_sources').length : 0
    }))
  };
}

module.exports = { mergeCompanyData, deduplicate, generateDataQualityReport };
```

- [ ] **Step 2: 测试报告生成函数**

Run:
```bash
node -e "
const { mergeCompanyData, generateDataQualityReport } = require('./api/services/dataMerger');
const testData = [
  { source: 'tianyancha', data: { company_name: '测试公司', legal_representative: '张三', employee_count: 50 } },
  { source: 'qichacha', data: { company_name: '测试公司', registered_capital: '100万' } }
];
const merged = mergeCompanyData(testData);
console.log(JSON.stringify(generateDataQualityReport(merged, testData), null, 2));
"
```

Expected:
- summary.completeness_score 应为数字
- fields 数组包含所有字段
- sources 数组包含两个数据源

- [ ] **Step 3: Commit**

```bash
git add api/services/dataMerger.js
git commit -m "feat: add data quality report generation"
```

---

## Task 2: 集成质量报告到 API 响应

**Files:**
- Modify: `server/routes/enterprise.js`

- [ ] **Step 1: 在多源采集 API 中集成质量报告**

找到现有的 `/collect/:companyName/all` 路由，在返回响应前添加质量报告：

修改返回部分，从：
```javascript
res.json({
  success: true,
  data: {
    merged: mergedData,
    sources: successResults.map(r => r.source),
    source_count: successResults.length,
    errors: errors
  }
});
```

改为：
```javascript
const { generateDataQualityReport } = require('../../api/services/dataMerger');
const qualityReport = generateDataQualityReport(mergedData, successResults);

res.json({
  success: true,
  data: {
    merged: mergedData,
    sources: successResults.map(r => r.source),
    source_count: successResults.length,
    errors: errors,
    quality_report: qualityReport
  }
});
```

- [ ] **Step 2: 测试 API 响应包含质量报告**

Run: `curl "http://localhost:3000/api/collect/%E4%B8%9C%E7%A4%BE%E9%80%A0%E7%BA%B8%E5%8E%82/all"`

检查返回的 JSON 中是否包含 `quality_report` 字段。

- [ ] **Step 3: Commit**

```bash
git add server/routes/enterprise.js
git commit -m "feat: integrate data quality report into API response"
```

---

## Task 3: 验收测试

**验证步骤:**

- [ ] **Step 1: 测试质量报告函数**

Run:
```bash
node -e "
const { mergeCompanyData, generateDataQualityReport } = require('./api/services/dataMerger');
const testData = [
  { source: 'tianyancha', data: { company_name: '测试公司', employee_count: 50, business_status: '存续' } },
  { source: 'qichacha', data: { company_name: '测试公司', registered_capital: '100万' } },
  { source: 'aiqicha', data: { company_name: '测试公司' } }
];
const merged = mergeCompanyData(testData);
const report = generateDataQualityReport(merged, testData);
console.log('completeness_score:', report.summary.completeness_score);
console.log('overall_status:', report.summary.overall_status);
console.log('missing_fields:', report.fields.filter(f => !f.populated).map(f => f.label));
"
```
Expected:
- completeness_score 为数字
- overall_status 为 "good" 或 "excellent"
- missing_fields 列出未填充的字段

- [ ] **Step 2: 测试 API 端点**

Run: `curl "http://localhost:3000/api/collect/%E4%B8%9C%E7%A4%BE%E9%80%A0%E7%BA%B8%E5%8E%82/all" 2>/dev/null | node -e "const d=JSON.parse(require('fs').readFileSync(0,'utf8')); console.log('quality_score:', d.data.quality_report?.summary?.completeness_score); console.log('has_report:', !!d.data.quality_report);"`

Expected: quality_score 有值，has_report 为 true

---

## 自检清单

1. **Spec 覆盖检查：**
   - [ ] generateDataQualityReport 函数实现完整
   - [ ] API 响应集成质量报告
   - [ ] 字段定义包含 critical 标记

2. **占位符检查：** 无 TBD/TODO

3. **数据正确性：**
   - [ ] completeness_score 计算正确
   - [ ] overall_status 分类正确（≥80 excellent，≥60 good，<60 poor）
   - [ ] missing_fields 正确列出未填充字段
