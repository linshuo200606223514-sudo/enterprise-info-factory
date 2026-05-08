/**
 * 企业信息工厂 - 主入口
 * 从公开渠道（百度搜索、天眼查等）收集企业信息
 */

const path = require('path');
const { searchEnterprise } = require('./services/aggregator');

/**
 * 收集企业信息
 * @param {string} companyName - 企业名称
 * @param {Object} options - 配置选项
 * @param {string} options.outputDir - 输出目录
 * @param {string} options.format - 输出格式
 */
async function collectCompanyInfo(companyName, options = {}) {
  const { outputDir = './output', format = 'json' } = options;

  console.log(`[企业信息工厂] 开始收集: ${companyName}`);

  try {
    const result = await searchEnterprise(companyName, { outputDir });
    console.log(`[企业信息工厂] 收集完成`);
    return result;
  } catch (error) {
    console.error(`[企业信息工厂] 收集失败:`, error.message);
    throw error;
  }
}

module.exports = {
  collectCompanyInfo
};
