/**
 * 造纸行业痛点规则引擎
 * 用于分析企业信息化现状，识别痛点并推荐解决方案
 */

const RULES = [
  {
    id: 'orders_001',
    category: '订单管理',
    severity: 'high',
    conditions: (data) => data.employee_count > 50 || !data.has_erp,
    evidence: '收集规模和ERP信息',
    recommendation: '建议部署订单管理模块'
  },
  {
    id: 'inventory_001',
    category: '库存管理',
    severity: 'high',
    conditions: (data) => data.product_types && data.product_types.length > 10 || !data.has_wms,
    evidence: '收集产品和WMS信息',
    recommendation: '建议部署库存管理模块'
  },
  {
    id: 'planning_001',
    category: '生产计划',
    severity: 'medium',
    conditions: (data) => data.product_types && data.product_types.length > 5 && !data.has_mes,
    evidence: '收集产品和MES信息',
    recommendation: '建议部署生产计划模块'
  },
  {
    id: 'finance_001',
    category: '账款管理',
    severity: 'high',
    conditions: (data) => data.customer_count > 20 || !data.has_crm,
    evidence: '收集客户数和CRM信息',
    recommendation: '建议部署账款管理模块'
  },
  {
    id: 'procurement_001',
    category: '采购协同',
    severity: 'medium',
    conditions: (data) => data.material_types && data.material_types.length > 20 || !data.has_scm,
    evidence: '收集材料和SCM信息',
    recommendation: '建议部署采购管理模块'
  }
];

/**
 * 分析数据，匹配痛点规则
 * @param {Object} data - 企业数据
 * @returns {Array} 匹配的痛点列表
 */
function analyze(data) {
  const painPoints = [];

  for (const rule of RULES) {
    try {
      if (rule.conditions(data)) {
        painPoints.push({
          id: rule.id,
          category: rule.category,
          severity: rule.severity,
          evidence: rule.evidence,
          recommendation: rule.recommendation
        });
      }
    } catch (error) {
      // 规则评估出错时跳过该规则
      console.warn(`规则 ${rule.id} 评估出错:`, error.message);
    }
  }

  return painPoints;
}

module.exports = {
  RULES,
  analyze
};