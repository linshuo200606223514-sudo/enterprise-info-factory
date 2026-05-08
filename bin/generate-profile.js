#!/usr/bin/env node
/**
 * 生成企业画像 HTML 报告
 * 用法: node bin/generate-profile.js <企业名称>
 */

const fs = require('fs');
const path = require('path');

// 读取最新数据文件
function findLatestData(companyName) {
  // 优先从 output/ 目录查找
  const outputDir = path.join(__dirname, '../output');
  if (!fs.existsSync(outputDir)) return null;

  const files = fs.readdirSync(outputDir)
    .filter(f => f.startsWith(companyName) && f.endsWith('.json') && f.includes('_2026'))
    .sort()
    .reverse();

  if (files.length > 0) {
    return path.join(outputDir, files[0]);
  }

  // 备选：从 output/data/ 目录查找
  const dataDir = path.join(__dirname, '../output/data');
  if (!fs.existsSync(dataDir)) return null;

  const dataFiles = fs.readdirSync(dataDir)
    .filter(f => f.startsWith(companyName) && f.endsWith('.json'))
    .sort()
    .reverse();

  return dataFiles.length > 0 ? path.join(dataDir, dataFiles[0]) : null;
}

// 读取元模型配置
function findMetaConfig(companyName) {
  // 优先从 output/ 目录查找
  const outputDir = path.join(__dirname, '../output');
  const metaInOutput = path.join(outputDir, `${companyName}_meta_config.json`);
  if (fs.existsSync(metaInOutput)) {
    return metaInOutput;
  }

  // 备选：从 output/meta-config/ 目录查找
  const configDir = path.join(__dirname, '../output/meta-config');
  if (!fs.existsSync(configDir)) return null;

  const files = fs.readdirSync(configDir)
    .filter(f => f.startsWith(companyName) && f.endsWith('.json'))
    .sort()
    .reverse();

  return files.length > 0 ? path.join(configDir, files[0]) : null;
}

// 替换模板变量
function renderTemplate(template, data) {
  let result = template;

  // 简单模板替换
  result = result.replace(/\{\{(\w+)\}\}/g, (match, key) => {
    return data[key] !== undefined ? data[key] : match;
  });

  // 处理 {{#each}} 循环
  result = result.replace(/\{\{#each (\w+)\}\}([\s\S]*?)\{\{\/each\}\}/g, (match, key, inner) => {
    const arr = data[key];
    if (!Array.isArray(arr)) return '';
    return arr.map(item => {
      let innerResult = inner;
      // 处理 {{this}}
      innerResult = innerResult.replace(/\{\{this\}\}/g, item);
      // 处理 {{category}}, {{recommendation}} 等属性
      innerResult = innerResult.replace(/\{\{(\w+)\}\}/g, (m, k) => {
        return item[k] !== undefined ? item[k] : m;
      });
      return innerResult;
    }).join('');
  });

  return result;
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

// 主要函数
function main() {
  const companyName = process.argv[2] || '东社造纸厂';
  console.log(`正在为 "${companyName}" 生成企业画像...`);

  // 读取数据
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

  // 读取模板
  const templatePath = path.join(__dirname, '../templates/enterprise-profile.html');
  let template = fs.readFileSync(templatePath, 'utf8');

  // 构建渲染数据
  const renderData = {
    company_name: metaConfig.company?.name || companyData.enterpriseName || companyName,
    industry: metaConfig.company?.industry || '造纸箱',
    scale: metaConfig.company?.scale || 'unknown',
    scale_text: getScaleText(metaConfig.company?.scale),
    source_count: companyData.sources?.length || 0,
    generate_time: new Date().toLocaleString('zh-CN'),
    sources: companyData.sources || ['未知'],
    modules: (metaConfig.modules || []).map(m => ({
      name: m.name,
      severity: getSeverity(m.priority),
      priority: m.priority,
      priority_text: getPriorityText(m.priority),
      features: (m.features || []).map(f => f.name || f)
    })),
    pain_points: (metaConfig.modules || []).map(m => ({
      category: m.name,
      recommendation: m.metadata?.recommendation || ''
    }))
  };

  // 渲染模板
  const html = renderTemplate(template, renderData);

  // 保存 HTML
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
