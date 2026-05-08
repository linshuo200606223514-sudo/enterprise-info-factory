#!/usr/bin/env node

const { program } = require('commander');

program
  .name('enterprise-info')
  .description('企业信息工厂 - 从公开渠道收集企业信息')
  .version('1.0.0');

program
  .command('search <companyName>')
  .description('搜索企业信息')
  .option('-o, --output <dir>', '输出目录', './output')
  .option('-f, --format <format>', '输出格式 (json|html)', 'json')
  .action((companyName, options) => {
    console.log(`正在收集企业信息: ${companyName}`);
    console.log(`输出目录: ${options.output}`);
    console.log(`输出格式: ${options.format}`);

    // 动态导入主模块
    const { collectCompanyInfo } = require('../api/index.js');
    collectCompanyInfo(companyName, {
      outputDir: options.output,
      format: options.format
    });
  });

program.parse();
