#!/usr/bin/env node

const { program } = require('commander');

program
  .name('enterprise-info')
  .description('企业信息工厂 - 从公开渠道收集企业信息')
  .version('1.0.0');

program
  .option('-n, --name <companyName>', '企业名称')
  .option('-o, --output <dir>', '输出目录', './output')
  .option('-f, --format <format>', '输出格式 (json|html)', 'json')
  .action((options) => {
    if (!options.name) {
      console.error('错误: 请提供企业名称，使用 -n 或 --name');
      process.exit(1);
    }
    console.log(`正在收集企业信息: ${options.name}`);
    console.log(`输出目录: ${options.output}`);
    console.log(`输出格式: ${options.format}`);

    // 动态导入主模块
    const { collectCompanyInfo } = require('../api/index.js');
    collectCompanyInfo(options.name, {
      outputDir: options.output,
      format: options.format
    });
  });

program.parse();
