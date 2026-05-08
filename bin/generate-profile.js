#!/usr/bin/env node
/**
 * 生成企业画像 HTML 报告
 * 用法: node bin/generate-profile.js <企业名称>
 */

const fs = require('fs');
const path = require('path');

// 读取最新数据文件
function findLatestData(companyName) {
  const outputDir = path.join(__dirname, '../output');
  if (!fs.existsSync(outputDir)) return null;

  const files = fs.readdirSync(outputDir)
    .filter(f => f.startsWith(companyName) && f.endsWith('.json') && f.includes('_2026'))
    .sort()
    .reverse();

  return files.length > 0 ? path.join(outputDir, files[0]) : null;
}

// 读取元模型配置
function findMetaConfig(companyName) {
  const outputDir = path.join(__dirname, '../output');
  const metaInOutput = path.join(outputDir, `${companyName}_meta_config.json`);
  if (fs.existsSync(metaInOutput)) {
    return metaInOutput;
  }

  const configDir = path.join(__dirname, '../output/meta-config');
  if (!fs.existsSync(configDir)) return null;

  const files = fs.readdirSync(configDir)
    .filter(f => f.startsWith(companyName) && f.endsWith('.json'))
    .sort()
    .reverse();

  return files.length > 0 ? path.join(configDir, files[0]) : null;
}

// 获取规模文本
function getScaleText(scale) {
  const map = {
    'small': '小微企业 (<50人)',
    'medium': '中小型企业 (50-200人)',
    'large': '大型企业 (>200人)',
    'unknown': '规模待确认'
  };
  return map[scale] || scale;
}

// 获取优先级文本
function getPriorityText(priority) {
  const map = { 1: '高优先级', 2: '中优先级', 3: '低优先级' };
  return map[priority] || priority;
}

// 获取严重程度
function getSeverity(priority) {
  const map = { 1: 'high', 2: 'medium', 3: 'low' };
  return map[priority] || 'medium';
}

// 生成模块 HTML
function generateModulesHtml(modules) {
  return modules.map(m => {
    const severity = getSeverity(m.priority);
    const priorityText = getPriorityText(m.priority);
    const features = (m.features || []).map(f => {
      const name = typeof f === 'object' ? f.name : f;
      return `<span class="feature-tag">${name}</span>`;
    }).join('');

    return `
        <li class="module-item ${severity}">
          <div class="module-header">
            <span class="module-name">${m.name}</span>
            <span class="priority ${severity}">${priorityText}</span>
          </div>
          <div class="feature-tags">
            ${features}
          </div>
        </li>`;
  }).join('');
}

// 生成痛点 HTML
function generatePainPointsHtml(modules) {
  return modules.map(m => `
      <div class="pain-point-item">
        <h4>${m.name}</h4>
        <p>${m.metadata?.recommendation || ''}</p>
      </div>`).join('');
}

// 生成数据来源 HTML
function generateSourcesHtml(sources) {
  return sources.map(s => `<span class="source-tag">${s}</span>`).join('');
}

// 替换模板变量
function renderTemplate(template, data) {
  return template
    .replace(/\{\{company_name\}\}/g, data.company_name)
    .replace(/\{\{industry\}\}/g, data.industry)
    .replace(/\{\{scale_text\}\}/g, data.scale_text)
    .replace(/\{\{source_count\}\}/g, data.source_count)
    .replace(/\{\{generate_time\}\}/g, data.generate_time)
    .replace(/\{\{pain_points_html\}\}/g, data.pain_points_html)
    .replace(/\{\{modules_html\}\}/g, data.modules_html)
    .replace(/\{\{sources_html\}\}/g, data.sources_html);
}

// 主要函数
function main() {
  const companyName = process.argv[2] || '东社造纸厂';
  console.log(`正在为 "${companyName}" 生成企业画像...`);

  const dataFile = findLatestData(companyName);
  const metaFile = findMetaConfig(companyName);

  if (!dataFile && !metaFile) {
    console.error(`未找到 "${companyName}" 的数据文件`);
    console.log('请先运行: node bin/cli.js search "' + companyName + '"');
    process.exit(1);
  }

  let companyData = {};
  let metaConfig = {};

  if (dataFile) {
    console.log('读取数据:', dataFile);
    companyData = JSON.parse(fs.readFileSync(dataFile, 'utf8'));
  }

  if (metaFile) {
    console.log('读取配置:', metaFile);
    metaConfig = JSON.parse(fs.readFileSync(metaFile, 'utf8'));
  }

  const templatePath = path.join(__dirname, '../templates/enterprise-profile.html');
  let template = fs.readFileSync(templatePath, 'utf8');

  const modules = metaConfig.modules || [];
  const sources = companyData.sources || [];

  const renderData = {
    company_name: metaConfig.company?.name || companyData.enterpriseName || companyName,
    industry: metaConfig.company?.industry || '造纸箱',
    scale_text: getScaleText(metaConfig.company?.scale),
    source_count: sources.length,
    generate_time: new Date().toLocaleString('zh-CN'),
    modules_html: generateModulesHtml(modules),
    pain_points_html: generatePainPointsHtml(modules),
    sources_html: generateSourcesHtml(sources)
  };

  const html = renderTemplate(template, renderData);

  const outputDir = path.join(__dirname, '../output/reports');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const outputFile = path.join(outputDir, `${companyName}_profile.html`);
  fs.writeFileSync(outputFile, html, 'utf8');

  console.log(`\n✅ 企业画像已生成: ${outputFile}`);
  console.log(`请在浏览器中打开查看: file://${outputFile.replace(/\\/g, '/')}`);
}

main();
