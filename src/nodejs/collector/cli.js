/**
 * 企业信息收集系统 - Node.js CLI入口
 */
const { Command } = require('commander');
const { runCollector } = require('./index');
const { runIndustryReport } = require('./industry');

const program = new Command();

program
    .name('enterprise-collector')
    .description('企业信息收集系统 - 行业研究和企业信息收集工具')
    .version('0.2.0');

// 行业研究报告命令
program
    .command('industry <keyword>')
    .description('生成行业研究报告（不聚焦具体企业）')
    .option('-o, --output <dir>', '输出目录', './reports')
    .action(async (keyword, options) => {
        try {
            await runIndustryReport(keyword, options);
        } catch (error) {
            console.error('❌ 生成失败:', error.message);
            process.exit(1);
        }
    });

// 企业信息收集命令（保留原有功能）
program
    .command('collect <company_name>')
    .description('收集企业信息（聚焦具体企业）')
    .option('-o, --output <dir>', '输出目录', './output')
    .option('-i, --industry <keyword>', '行业关键词', '造纸箱行业')
    .action(async (companyName, options) => {
        try {
            await runCollector(companyName, options);
        } catch (error) {
            console.error('❌ 收集失败:', error.message);
            process.exit(1);
        }
    });

program.parse();