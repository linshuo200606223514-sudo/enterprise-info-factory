/**
 * 行业研究报告生成模块
 */
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

function runPythonScript(scriptPath, args) {
    return new Promise((resolve, reject) => {
        const argList = Object.entries(args).map(([k, v]) => `${k}=${v}`);
        const env = { ...process.env, PYTHONIOENCODING: 'utf-8' };
        const proc = spawn('python', [scriptPath, ...argList], { env });

        let stdoutChunks = [];
        let stderrChunks = [];
        proc.stdout.on('data', (data) => { stdoutChunks.push(data); });
        proc.stderr.on('data', (data) => { stderrChunks.push(data); });

        proc.on('close', (code) => {
            if (code === 0) {
                const stdout = Buffer.concat(stdoutChunks).toString('utf-8');
                resolve(stdout.trim());
            } else {
                const stderr = Buffer.concat(stderrChunks).toString('utf-8');
                console.error('Python stderr:', stderr.substring(0, 500));
                reject(new Error(`Python script failed with code ${code}`));
            }
        });
    });
}

async function runIndustryReport(keyword, options = {}) {
    console.log(`🔍 开始生成行业研究报告: ${keyword}`);
    console.log(`📡 数据源: Tavily多路并行搜索`);

    // 第一步：生成行业研究报告数据
    console.log('\n📌 步骤1: 执行5路并行搜索（主搜索+新闻+竞品+趋势+社区）...');
    const reportDataRaw = await runPythonScript('src/python/industry_report.py', {
        keyword: keyword
    });
    const reportData = JSON.parse(reportDataRaw);

    console.log(`   📊 头部玩家: ${reportData.top_players?.length || 0} 个（含核心功能+定价）`);
    console.log(`   📰 最新动态: ${reportData.latest_news?.length || 0} 条`);
    console.log(`   ⚔️ 竞品分析: ${reportData.competitors?.length || 0} 条`);
    console.log(`   💬 社区评价: ${reportData.community?.length || 0} 条`);
    console.log(`   📈 行业趋势: ${reportData.trends?.length || 0} 条`);

    // 第二步：生成Markdown报告
    console.log('\n📌 步骤2: 生成Markdown报告...');
    const mdPath = await runPythonScript('src/python/industry_markdown_reporter.py', {
        data: JSON.stringify(reportData)
    });
    console.log(`✅ Markdown报告已生成: ${mdPath}`);

    // 第三步：保存JSON数据
    console.log('\n📌 步骤3: 保存JSON数据...');
    const jsonPath = await runPythonScript('src/python/industry_report.py', {
        keyword: keyword
    });
    // industry_report.py 的 main 输出 JSON 到 stdout，我们重新调用一次保存

    // 直接保存
    const outputDir = options.output || './reports';
    const safeKeyword = keyword.replace(/[^a-zA-Z0-9一-龥]/g, '_').slice(0, 20);
    const jsonFilename = `${safeKeyword}_行业报告_${new Date().toISOString().slice(0,16).replace(/:/g, '-')}.json`;
    const jsonFilepath = path.join(outputDir, jsonFilename);

    // 重新生成一次获取完整JSON
    const fullReportRaw = await runPythonScript('src/python/industry_report.py', {
        keyword: keyword
    });
    const fullReport = JSON.parse(fullReportRaw);

    fs.writeFileSync(jsonFilepath, JSON.stringify(fullReport, null, 2), 'utf-8');
    console.log(`✅ JSON数据已保存: ${jsonFilepath}`);

    console.log('\n✨ 行业报告生成完成！');
    console.log('\n📋 报告摘要:');
    const insights = fullReport.key_insights || {};
    const activityMap = { high: '🔥 活跃', medium: '📈 中等', low: '📉 平静' };
    console.log(`   - 市场活跃度: ${activityMap[insights.market_activity] || insights.market_activity}`);
    console.log(`   - 玩家数量: ${insights.player_count || 0} 个`);
    console.log(`   - 近期动态: ${insights.news_count || 0} 条`);
    console.log(`   - 趋势讨论: ${insights.trend_count || 0} 条`);

    return fullReport;
}

module.exports = { runIndustryReport };