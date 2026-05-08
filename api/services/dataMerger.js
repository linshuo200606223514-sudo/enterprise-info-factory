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