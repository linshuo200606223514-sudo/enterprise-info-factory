/**
 * 报告生成路由
 * 生成企业画像HTML报告
 */

const path = require('path');
const fs = require('fs');

/**
 * 简单的模板引擎 - 替换 {{variable}} 和 {{#if}}...{{/if}} 块
 * @param {string} template - HTML模板
 * @param {Object} data - 数据对象
 * @returns {string} - 渲染后的HTML
 */
function renderTemplate(template, data) {
  let result = template;

  // 处理 {{variable}} 替换
  result = result.replace(/\{\{(\w+(?:\.\w+)*)\}\}/g, (match, path) => {
    const keys = path.split('.');
    let value = data;
    for (const key of keys) {
      if (value && typeof value === 'object' && key in value) {
        value = value[key];
      } else {
        return match; // 保持原样
      }
    }
    return value !== undefined ? String(value) : match;
  });

  // 处理 {{#if condition}}...{{/if}} 块
  result = result.replace(/\{\{#if (\w+(?:\.\w+)*)\}\}([\s\S]*?)\{\{\/if\}\}/g, (match, path, content) => {
    const keys = path.split('.');
    let value = data;
    for (const key of keys) {
      if (value && typeof value === 'object' && key in value) {
        value = value[key];
      } else {
        value = undefined;
        break;
      }
    }
    return value ? content : '';
  });

  // 处理 {{#each array}}...{{/each}} 块
  result = result.replace(/\{\{#each (\w+(?:\.\w+)*)\}\}([\s\S]*?)\{\{\/each\}\}/g, (match, path, content) => {
    const keys = path.split('.');
    let array = data;
    for (const key of keys) {
      if (array && typeof array === 'object' && key in array) {
        array = array[key];
      } else {
        return match;
      }
    }
    if (!Array.isArray(array)) return match;

    return array.map((item, index) => {
      let itemContent = content;
      // 处理 {{this.property}} 引用
      itemContent = itemContent.replace(/\{\{this\.(\w+)\}\}/g, (m, prop) => {
        return item[prop] !== undefined ? String(item[prop]) : m;
      });
      // 处理 {{@index}} 引用
      itemContent = itemContent.replace(/\{\{@index\}\}/g, String(index));
      return itemContent;
    }).join('');
  });

  return result;
}

/**
 * 生成HTML报告
 * @param {Object} data - 企业数据
 * @param {Object} options - 配置选项
 * @param {string} options.outputDir - 输出目录，默认为项目output/reports目录
 * @param {string} options.templatePath - 模板路径，默认使用内置模板
 * @returns {Promise<Object>} - 包含报告路径和HTML内容
 */
async function generateReport(data, options = {}) {
  const outputDir = options.outputDir || path.join(__dirname, '../../output/reports');
  const templatePath = options.templatePath || path.join(__dirname, '../../templates/report.html');

  // 读取模板
  let template;
  try {
    template = fs.readFileSync(templatePath, 'utf-8');
  } catch (err) {
    throw new Error(`读取模板失败: ${templatePath} - ${err.message}`);
  }

  // 准备模板数据
  const templateData = {
    companyName: data.companyName || data.enterpriseName || '未知企业',
    generatedAt: new Date().toLocaleString('zh-CN'),
    basicInfo: data.basicInfo || data.basic_info || null,
    businessInfo: data.businessInfo || data.business_info || null,
    contactInfo: data.contactInfo || data.contact_info || null,
    news: data.news || [],
    webInfo: data.webInfo || data.web_info || null
  };

  // 渲染模板
  const html = renderTemplate(template, templateData);

  // 生成文件名
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const safeName = (templateData.companyName).replace(/[/\\?%*:|"<>]/g, '-');
  const filename = `${safeName}_${timestamp}.html`;
  const reportPath = path.join(outputDir, filename);

  // 保存报告
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, html, 'utf-8');

  console.log(`[Report] 报告已生成: ${reportPath}`);

  return {
    success: true,
    reportPath,
    filename,
    html
  };
}

module.exports = {
  generateReport
};