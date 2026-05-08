# 信用评分与风险标签实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现独立信用评分服务 `api/services/creditScorer.js`，基于多源工商数据生成标准化信用评分和风险标签

**Architecture:** 信用评分作为独立服务，不依赖采集流程。评分服务接收合并后的企业数据，计算各维度得分，输出标准化评分结果。API 层负责调用评分服务并返回响应。

**Tech Stack:** Node.js (纯 JavaScript)

---

## 文件结构

```
api/services/
├── creditScorer.js    # 新增：独立信用评分服务
└── dataMerger.js     # 现有：数据合并

server/routes/
└── enterprise.js     # 修改：增加 /credit-score/:companyName 和 /credit-score/batch 端点
```

---

## Task 1: 创建 creditScorer.js 核心结构和维度评分函数

**Files:**
- Create: `api/services/creditScorer.js`

- [ ] **Step 1: 创建 creditScorer.js 文件结构**

在 `api/services/creditScorer.js` 中创建以下内容：

```javascript
/**
 * 信用评分服务
 * 基于多源工商数据生成标准化信用评分和风险标签
 */

// 评分维度权重配置
const DIMENSION_WEIGHTS = {
  basic: 0.20,      // 基础工商 20%
  judicial: 0.30,    // 司法风险 30%
  operation: 0.25,   // 经营状态 25%
  changes: 0.15,    // 变更记录 15%
  sentiment: 0.10    // 舆情 10%
};

// 评分等级阈值
const GRADE_THRESHOLDS = [
  { grade: 'A', min: 80 },
  { grade: 'B', min: 60 },
  { grade: 'C', min: 40 },
  { grade: 'D', min: 20 },
  { grade: 'E', min: 0 }
];

/**
 * 计算基础工商评分
 * @param {Object} data - 企业数据
 * @returns {Object} { score: number, max: 100 }
 */
function scoreBasic(data) {
  let score = 0;
  let factors = 0;

  // 成立年限评分
  if (data.establishment_date) {
    const years = getYearsSince(data.establishment_date);
    if (years >= 10) score += 40;
    else if (years >= 5) score += 32;
    else if (years >= 3) score += 24;
    else if (years >= 1) score += 16;
    else score += 8;
    factors++;
  }

  // 注册资本评分
  if (data.registered_capital) {
    const capital = parseCapital(data.registered_capital);
    if (capital >= 500) score += 30;
    else if (capital >= 100) score += 24;
    else if (capital >= 10) score += 18;
    else score += 12;
    factors++;
  }

  // 登记状态评分
  if (data.business_status) {
    const status = data.business_status;
    if (status === '存续') score += 30;
    else if (status === '在业') score += 27;
    else score += 10; // 其他状态
    factors++;
  }

  // 归一化到100分
  const maxScore = factors === 3 ? 100 : (factors === 2 ? 66 : 33);
  return {
    score: factors === 0 ? null : Math.round((score / (factors * 40)) * 100),
    max: 100
  };
}

/**
 * 计算司法风险评分
 * @param {Object} data - 企业数据
 * @returns {Object} { score: number, max: 100 }
 */
function scoreJudicial(data) {
  let score = 100;
  const riskTags = [];

  // judicial_risks 数组中存在被执行人记录
  if (data.judicial_risks && data.judicial_risks.length > 0) {
    for (const risk of data.judicial_risks) {
      if (risk.type === '被执行人') score -= 30;
      if (risk.type === '失信人') score -= 50;
    }
  }

  // 行政处罚
  if (data.administrative_penalties && data.administrative_penalties.length > 0) {
    score -= 20 * Math.min(data.administrative_penalties.length, 2);
  }

  // 经营异常
  if (data.business_status && !['存续', '在业'].includes(data.business_status)) {
    score -= 40;
  }

  return {
    score: Math.max(0, score),
    max: 100
  };
}

/**
 * 计算经营状态评分
 * @param {Object} data - 企业数据
 * @returns {Object} { score: number, max: 100 }
 */
function scoreOperation(data) {
  let score = 0;
  let factors = 0;

  // 年营收
  if (data.annual_revenue) {
    const revenue = parseRevenue(data.annual_revenue);
    if (revenue >= 1000) score += 40;
    else if (revenue >= 100) score += 28;
    else score += 20;
    factors++;
  }

  // 员工规模
  if (data.employee_count) {
    const employees = parseInt(data.employee_count) || 0;
    if (employees >= 100) score += 30;
    else if (employees >= 20) score += 21;
    else score += 15;
    factors++;
  }

  // 纳税人资质
  if (data.taxpayer_type) {
    if (data.taxpayer_type === '一般纳税人') score += 30;
    else if (data.taxpayer_type === '小规模') score += 21;
    factors++;
  }

  if (factors === 0) {
    return { score: null, max: 100 };
  }

  return {
    score: Math.round((score / (factors * 40)) * 100),
    max: 100
  };
}

/**
 * 计算变更记录评分
 * @param {Object} data - 企业数据
 * @returns {Object} { score: number, max: 100 }
 */
function scoreChanges(data) {
  let score = 100;

  // 变更记录（暂未实现数据结构，预留接口）
  // 后续扩展：从 data.change_records 读取

  return { score, max: 100 };
}

/**
 * 计算舆情评分
 * @param {Object} data - 企业数据
 * @returns {Object} { score: number, max: 100 }
 */
function scoreSentiment(data) {
  // 舆情暂未实现，返回 null 表示暂无数据
  return { score: null, max: 100 };
}

/**
 * 辅助函数：从日期字符串计算成立年限
 */
function getYearsSince(dateStr) {
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return 0;
    const now = new Date();
    return Math.floor((now - date) / (365.25 * 24 * 60 * 60 * 1000));
  } catch {
    return 0;
  }
}

/**
 * 辅助函数：解析注册资本
 * @param {string} capital - 注册资本字符串，如 "100万"、"500万元"
 * @returns {number} 数值（万为单位）
 */
function parseCapital(capital) {
  if (!capital) return 0;
  const str = String(capital);
  const match = str.match(/[\d.]+/);
  if (!match) return 0;
  let num = parseFloat(match[0]);
  if (str.includes('万') || str.includes('万元')) {
    // 已是万为单位
  } else if (str.includes('亿')) {
    num *= 10000;
  }
  return num;
}

/**
 * 辅助函数：解析年营收
 * @param {string} revenue - 年营收字符串
 * @returns {number} 数值（万为单位）
 */
function parseRevenue(revenue) {
  if (!revenue) return 0;
  const str = String(revenue);
  const match = str.match(/[\d.]+/);
  if (!match) return 0;
  let num = parseFloat(match[0]);
  if (str.includes('亿')) {
    num *= 10000;
  }
  // 其他默认为万
  return num;
}

module.exports = {
  scoreBasic,
  scoreJudicial,
  scoreOperation,
  scoreChanges,
  scoreSentiment,
  DIMENSION_WEIGHTS,
  GRADE_THRESHOLDS
};
```

- [ ] **Step 2: 测试维度评分函数**

```bash
node -e "
const { scoreBasic, scoreJudicial, scoreOperation } = require('./api/services/creditScorer');

// 测试基础工商评分
const basicData = {
  establishment_date: '2010-01-01',
  registered_capital: '500万',
  business_status: '存续'
};
console.log('basic score:', scoreBasic(basicData));

// 测试司法风险评分
const judicialData = {
  judicial_risks: [{ type: '被执行人' }],
  business_status: '存续'
};
console.log('judicial score:', scoreJudicial(judicialData));

// 测试经营状态评分
const opData = {
  annual_revenue: '500万',
  employee_count: 50,
  taxpayer_type: '一般纳税人'
};
console.log('operation score:', scoreOperation(opData));
"
```

Expected:
- basic score 应返回 { score: 100, max: 100 }
- judicial score 应返回 { score: 70, max: 100 }
- operation score 应返回合理分数

- [ ] **Step 3: Commit**

```bash
git add api/services/creditScorer.js
git commit -m "feat: add creditScorer with dimension scoring functions"
```

---

## Task 2: 实现信用评分和风险标签主函数

**Files:**
- Modify: `api/services/creditScorer.js`

- [ ] **Step 1: 添加 generateCreditScore 和 detectRiskTags 函数**

在 `creditScorer.js` 文件末尾添加：

```javascript
/**
 * 检测风险标签
 * @param {Object} data - 企业数据
 * @returns {Array} 风险标签数组
 */
function detectRiskTags(data) {
  const tags = [];

  // 失信：存在失信被执行人记录
  if (data.judicial_risks) {
    if (data.judicial_risks.some(r => r.type === '失信人')) {
      tags.push('失信');
    }
    if (data.judicial_risks.some(r => r.type === '老赖')) {
      tags.push('老赖');
    }
  }

  // 经营异常
  if (data.business_status && !['存续', '在业'].includes(data.business_status)) {
    tags.push('经营异常');
  }

  // 欠税
  if (data.tax_arrears || data.tax_status === '异常') {
    tags.push('欠税');
  }

  // 新设企业
  if (data.establishment_date) {
    const years = getYearsSince(data.establishment_date);
    if (years < 1) {
      tags.push('新设企业');
    }
  }

  return tags;
}

/**
 * 计算信用评分
 * @param {Object} data - 合并后的企业数据
 * @returns {Object} 信用评分结果
 */
function generateCreditScore(data) {
  if (!data || !data.company_name) {
    return {
      company_name: null,
      credit_score: null,
      credit_grade: null,
      risk_tags: [],
      dimensions: {},
      summary: '数据不足，无法评分',
      generated_at: new Date().toISOString()
    };
  }

  // 计算各维度得分
  const dimensions = {
    basic: scoreBasic(data),
    judicial: scoreJudicial(data),
    operation: scoreOperation(data),
    changes: scoreChanges(data),
    sentiment: scoreSentiment(data)
  };

  // 计算加权总分
  let totalScore = 0;
  let totalWeight = 0;
  let validDimensions = 0;

  for (const [dim, weight] of Object.entries(DIMENSION_WEIGHTS)) {
    const dimScore = dimensions[dim].score;
    if (dimScore !== null) {
      totalScore += dimScore * weight;
      totalWeight += weight;
      validDimensions++;
    }
  }

  let creditScore = null;
  let creditGrade = null;
  let summary = '';

  if (validDimensions >= 3 && totalWeight > 0) {
    creditScore = Math.round(totalScore / totalWeight);

    // 确定等级
    for (const threshold of GRADE_THRESHOLDS) {
      if (creditScore >= threshold.min) {
        creditGrade = threshold.grade;
        break;
      }
    }
  } else {
    summary = '数据不足，无法生成有效评分（有效维度少于3个）';
  }

  // 检测风险标签
  const riskTags = detectRiskTags(data);

  // 生成摘要
  if (summary === '' && creditGrade) {
    const gradeDesc = {
      'A': '优质客户，低风险',
      'B': '良好客户，轻微关注',
      'C': '中等客户，适度关注',
      'D': '高风险客户，谨慎合作',
      'E': '极高风险，建议拒绝'
    };
    summary = gradeDesc[creditGrade];
    if (riskTags.length > 0) {
      summary += '，' + riskTags.join('、') + '需关注';
    }
  }

  return {
    company_name: data.company_name,
    credit_score: creditScore,
    credit_grade: creditGrade,
    risk_tags: riskTags,
    dimensions: dimensions,
    summary: summary,
    generated_at: new Date().toISOString()
  };
}

module.exports = {
  ...module.exports,
  generateCreditScore,
  detectRiskTags
};
```

- [ ] **Step 2: 测试 generateCreditScore 函数**

```bash
node -e "
const { generateCreditScore } = require('./api/services/creditScorer');

// 测试完整评分
const testData = {
  company_name: '测试公司',
  establishment_date: '2010-01-01',
  registered_capital: '500万',
  business_status: '存续',
  employee_count: 100,
  annual_revenue: '1000万',
  taxpayer_type: '一般纳税人',
  judicial_risks: []
};

const result = generateCreditScore(testData);
console.log('credit_score:', result.credit_score);
console.log('credit_grade:', result.credit_grade);
console.log('risk_tags:', result.risk_tags);
console.log('summary:', result.summary);
"
```

Expected:
- credit_score 应为 80-100 之间
- credit_grade 应为 'A'
- risk_tags 应为空数组

- [ ] **Step 3: Commit**

```bash
git add api/services/creditScorer.js
git commit -m "feat: add generateCreditScore and detectRiskTags functions"
```

---

## Task 3: 实现 API 端点

**Files:**
- Modify: `server/routes/enterprise.js`

- [ ] **Step 1: 添加信用评分 API 端点**

在 `server/routes/enterprise.js` 末尾添加：

```javascript
// 信用评分查询
router.get('/credit-score/:companyName', async (req, res) => {
  const { companyName } = req.params;

  try {
    // 先采集多源数据
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
    for (const result of results) {
      if (result.status === 'fulfilled' && result.value && !result.value.error) {
        successResults.push(result.value);
      }
    }

    if (successResults.length === 0) {
      return res.json({
        success: false,
        error: '未找到企业数据，请先执行采集'
      });
    }

    // 合并数据
    const { mergeCompanyData } = require('../../api/services/dataMerger');
    const { generateCreditScore } = require('../../api/services/creditScorer');
    const mergedData = mergeCompanyData(successResults);
    const creditScore = generateCreditScore(mergedData);

    res.json({
      success: true,
      data: creditScore
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// 批量信用评分
router.post('/credit-score/batch', async (req, res) => {
  const { companies } = req.body;

  if (!companies || !Array.isArray(companies) || companies.length === 0) {
    return res.status(400).json({
      success: false,
      error: 'companies 参数无效'
    });
  }

  try {
    const { generateCreditScore } = require('../../api/services/creditScorer');
    const { mergeCompanyData } = require('../../api/services/dataMerger');
    const { runPythonScraper } = require('../../api/services/aggregator');

    const results = [];

    for (const companyName of companies) {
      try {
        // 并行采集
        const scrapers = [
          { name: 'qichacha', args: [companyName] },
          { name: 'aiqicha', args: [companyName] },
          { name: 'qixin', args: [companyName] },
          { name: 'tianyancha', args: [companyName] }
        ];

        const scrapeResults = await Promise.allSettled(
          scrapers.map(scraper => runPythonScraper(scraper.name, scraper.args))
        );

        const successResults = scrapeResults
          .filter(r => r.status === 'fulfilled' && r.value && !r.value.error)
          .map(r => r.value);

        if (successResults.length === 0) {
          results.push({
            company_name: companyName,
            credit_score: null,
            credit_grade: null,
            error: '采集失败'
          });
          continue;
        }

        const merged = mergeCompanyData(successResults);
        const score = generateCreditScore(merged);

        results.push({
          company_name: companyName,
          credit_score: score.credit_score,
          credit_grade: score.credit_grade,
          risk_tags: score.risk_tags
        });
      } catch (e) {
        results.push({
          company_name: companyName,
          credit_score: null,
          credit_grade: null,
          error: e.message
        });
      }
    }

    res.json({
      success: true,
      data: {
        results: results,
        total: results.length,
        generated_at: new Date().toISOString()
      }
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});
```

- [ ] **Step 2: 提交代码**

```bash
git add server/routes/enterprise.js
git commit -m "feat: add credit score API endpoints"
```

---

## Task 4: 验收测试

**Files:**
- Modify: `api/services/creditScorer.js` (测试通过后确认)

- [ ] **Step 1: 测试信用评分各维度**

```bash
node -e "
const { generateCreditScore, scoreBasic, scoreJudicial, scoreOperation } = require('./api/services/creditScorer');

// 测试1: 优质客户
const goodCompany = {
  company_name: '优质公司',
  establishment_date: '2010-01-01',
  registered_capital: '500万',
  business_status: '存续',
  employee_count: 100,
  annual_revenue: '1000万',
  taxpayer_type: '一般纳税人',
  judicial_risks: []
};
const goodResult = generateCreditScore(goodCompany);
console.log('=== 优质公司测试 ===');
console.log('score:', goodResult.credit_score, 'grade:', goodResult.credit_grade);
console.log('dimensions:', JSON.stringify(goodResult.dimensions, null, 2));

// 测试2: 高风险客户
const badCompany = {
  company_name: '高风险公司',
  establishment_date: '2025-01-01',
  registered_capital: '5万',
  business_status: '存续',
  judicial_risks: [{ type: '失信人' }]
};
const badResult = generateCreditScore(badCompany);
console.log('\\n=== 高风险公司测试 ===');
console.log('score:', badResult.credit_score, 'grade:', badResult.credit_grade);
console.log('risk_tags:', badResult.risk_tags);

// 测试3: 数据不足
const poorData = {
  company_name: '数据不足公司'
};
const poorResult = generateCreditScore(poorData);
console.log('\\n=== 数据不足测试 ===');
console.log('score:', poorResult.credit_score, 'summary:', poorResult.summary);
"
```

Expected:
- 优质公司: grade = 'A', score ≈ 85-100
- 高风险公司: grade = 'C'或'D', risk_tags包含'失信'
- 数据不足: score = null, summary 提示数据不足

- [ ] **Step 2: 自检清单**

1. **Spec 覆盖检查：**
   - [ ] creditScorer.js 实现完整，包含所有维度评分函数
   - [ ] 评分等级划分正确（A/B/C/D/E）
   - [ ] 风险标签检测实现（失信、老赖、经营异常、欠税、新设企业）
   - [ ] API 端点返回标准化响应格式
   - [ ] 数据不足时给出明确提示

2. **占位符检查：** 无 TBD/TODO

3. **数据正确性：**
   - [ ] 基础工商评分计算正确
   - [ ] 司法风险扣分逻辑正确
   - [ ] 经营状态评分计算正确
   - [ ] 加权总分计算正确
   - [ ] 等级判定正确

