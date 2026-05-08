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