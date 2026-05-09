#!/usr/bin/env node
/**
 * 企业信息收集系统 - CLI入口
 */
const { Command } = require('commander');
const { runCollector } = require('./index');

const program = new Command();

program
    .name('enterprise-collector')
    .description('企业信息收集系统 - 从公开渠道收集企业信息')
    .version('0.1.0');

program
    .argument('<company_name>', '要收集信息的企业名称')
    .option('-o, --output <dir>', '输出目录', './output')
    .action(async (companyName, options) => {
        try {
            await runCollector(companyName, options);
        } catch (error) {
            console.error('❌ 收集失败:', error.message);
            process.exit(1);
        }
    });

program.parse();