/**
 * 信用评分服务
 * 基于多源工商数据生成标准化信用评分和风险标签
 */

// 评分维度权重配置
const DIMENSION_WEIGHTS = {
  basic: 0.20,      // 基础工商 20%
  judicial: 0.30,   // 司法风险 30%
  operation: 0.25,   // 经营状态 25%
  changes: 0.15,     // 变更记录 15%
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

  if (factors === 0) {
    return { score: null, max: 100 };
  }

  // 归一化到100分
  return {
    score: Math.round((score / (factors * 40)) * 100),
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