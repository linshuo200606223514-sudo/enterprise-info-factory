/**
 * 分析器主入口
 * 整合规则引擎和 AI 增强，输出元模型配置
 */

const fs = require('fs');
const path = require('path');
const { analyze } = require('./rules/paper_industry');
const { analyzeWithAI } = require('./ai/analyzer');

// ==================== 辅助函数 ====================

/**
 * 类别名转模块名
 * @param {string} category - 类别名称
 * @returns {string} 模块名称
 */
function getModuleName(category) {
  const mapping = {
    '订单管理': 'order_management',
    '库存管理': 'inventory_management',
    '生产计划': 'production_planning',
    '账款管理': 'accounts_receivable',
    '采购协同': 'procurement'
  };
  return mapping[category] || category.toLowerCase().replace(/[一-龥]/g, '_');
}

/**
 * 规模分类
 * @param {number|string} employeeCount - 员工数量
 * @returns {string} 规模分类
 */
function getScale(employeeCount) {
  const count = typeof employeeCount === 'string' ? parseInt(employeeCount, 10) : employeeCount;
  if (isNaN(count)) return 'unknown';
  if (count < 50) return 'small';
  if (count < 200) return 'medium';
  return 'large';
}

// ==================== 核心函数 ====================

/**
 * 分析企业数据
 * @param {Object} companyData - 企业数据
 * @returns {Promise<Object>} 分析结果和元模型配置
 */
async function analyzeCompany(companyData) {
  // 1. 调用规则引擎进行分析
  const ruleAnalysis = analyze(companyData);

  // 2. 调用 AI 增强分析（如果可用）
  let aiAnalysis = null;
  try {
    aiAnalysis = await analyzeWithAI(companyData);
  } catch (error) {
    console.warn('AI 增强分析失败:', error.message);
  }

  // 3. 合并结果（AI 优先级更高）
  const painPoints = mergePainPoints(ruleAnalysis, aiAnalysis);

  // 4. 生成元模型配置
  const metaConfig = generateMetaConfig(companyData, painPoints);

  return {
    analysis: {
      ruleBased: ruleAnalysis,
      aiEnhanced: aiAnalysis,
      merged: painPoints
    },
    metaConfig
  };
}

/**
 * 合并规则引擎和 AI 分析结果
 * AI 结果优先级更高
 * @param {Array} ruleResults - 规则引擎结果
 * @param {Object|null} aiResults - AI 分析结果
 * @returns {Array} 合并后的痛点列表
 */
function mergePainPoints(ruleResults, aiResults) {
  const painPoints = [];

  // 首先添加规则引擎识别的痛点
  for (const rule of ruleResults) {
    painPoints.push({
      id: rule.id,
      category: rule.category,
      severity: rule.severity,
      source: 'rules',
      recommendation: rule.recommendation
    });
  }

  // 如果有 AI 分析结果，合并 AI 痛点
  if (aiResults && aiResults.painPoints && Array.isArray(aiResults.painPoints)) {
    const existingCategories = new Set(painPoints.map(p => p.category));

    for (const aiPainPoint of aiResults.painPoints) {
      // AI 结果覆盖规则引擎的结果（如果类别相同）
      if (existingCategories.has(aiPainPoint.category)) {
        const existingIndex = painPoints.findIndex(p => p.category === aiPainPoint.category);
        painPoints[existingIndex] = {
          ...painPoints[existingIndex],
          description: aiPainPoint.description,
          severity: aiPainPoint.severity || painPoints[existingIndex].severity,
          suggestion: aiPainPoint.suggestion,
          source: 'ai_overridden'
        };
      } else {
        // 添加 AI 独有的痛点
        painPoints.push({
          id: `ai_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          category: aiPainPoint.category,
          description: aiPainPoint.description,
          severity: aiPainPoint.severity || 'medium',
          source: 'ai',
          suggestion: aiPainPoint.suggestion
        });
      }
    }
  }

  return painPoints;
}

/**
 * 生成元模型配置
 * @param {Object} companyData - 企业数据
 * @param {Array} painPoints - 痛点列表
 * @returns {Object} 元模型配置
 */
function generateMetaConfig(companyData, painPoints) {
  // 优先使用 enterpriseName，其次用 name，最后用中文"未知企业"
  const companyName = companyData.enterpriseName || companyData.name || companyData.enterprise_name || '未知企业';

  // 转换痛点为模块配置
  const modules = painPoints.map(painPoint => ({
    id: getModuleName(painPoint.category),
    name: painPoint.category,
    priority: painPoint.severity === 'high' ? 1 : painPoint.severity === 'medium' ? 2 : 3,
    features: [
      {
        name: '基础功能',
        status: 'recommended'
      },
      {
        name: painPoint.suggestion || painPoint.recommendation || '高级功能',
        status: 'recommended'
      }
    ],
    metadata: {
      source: painPoint.source,
      recommendation: painPoint.suggestion || painPoint.recommendation || ''
    }
  }));

  // 按优先级排序
  modules.sort((a, b) => a.priority - b.priority);

  // 构建完整配置
  return {
    company: {
      name: companyName,
      scale: getScale(companyData.employees || companyData.employee_count),
      industry: companyData.industry || '造纸箱'
    },
    modules: modules,
    metadata: {
      generatedAt: new Date().toISOString(),
      painPointCount: painPoints.length,
      version: '1.0.0'
    }
  };
}

/**
 * 保存元模型配置到文件
 * @param {Object} metaConfig - 元模型配置
 * @param {string} outputDir - 输出目录
 * @returns {Promise<string>} 保存的文件路径
 */
async function saveMetaConfig(metaConfig, outputDir) {
  // 创建输出目录（如果不存在）
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  // 生成文件名
  const companyName = metaConfig.company.name;
  const safeName = companyName.replace(/[<>:"/\\|?*\s]/g, '_');
  const fileName = `${safeName}_meta_config.json`;
  const filePath = path.join(outputDir, fileName);

  // 保存文件
  const content = JSON.stringify(metaConfig, null, 2);
  fs.writeFileSync(filePath, content, 'utf8');

  console.log(`元模型配置已保存到: ${filePath}`);
  return filePath;
}

module.exports = {
  analyzeCompany,
  generateMetaConfig,
  saveMetaConfig,
  getModuleName,
  getScale,
  mergePainPoints
};