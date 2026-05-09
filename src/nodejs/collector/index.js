/**
 * 企业信息收集系统 - Node.js 编排层
 */
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

function loadConfig() {
    const configPath = path.join(__dirname, '../../config/settings.json');
    const configContent = fs.readFileSync(configPath, 'utf-8');
    return JSON.parse(configContent);
}

async function runCollector(companyName, options = {}) {
    const config = loadConfig();
    const industryKeyword = options.industry || "造纸箱行业 ERP 数字化转型";

    console.log(`🔍 开始收集企业信息: ${companyName}`);
    console.log(`📡 数据源: Tavily搜索, 天眼查, 行业研究`);
    console.log(`🤖 AI分析: LLM驱动 + 行业背景融合`);

    // 第一步：行业研究（获取行业背景）
    console.log('\n📌 步骤0: 行业研究...');
    const industryContextRaw = await runPythonScript('src/python/search/industry_researcher.py', {
        keyword: industryKeyword,
        company: companyName
    });
    const industryContext = JSON.parse(industryContextRaw);
    console.log(`   📊 行业头部: ${industryContext.top_players?.length || 0} 个`);
    console.log(`   📰 行业动态: ${industryContext.news?.length || 0} 条`);

    // 第二步：多数据源搜索（优先Tavily）
    console.log('\n📌 步骤1: 执行多数据源搜索...');
    const searchResultsRaw = await runPythonScript('src/python/search/multi_search.py', {
        keyword: companyName,
        max_results: config.search.baidu.max_results
    });
    let searchResults = [];
    try {
        searchResults = JSON.parse(searchResultsRaw);
    } catch (e) {
        console.log('   ⚠️ 搜索结果解析失败');
    }
    console.log(`   📊 获得 ${searchResults.length} 条搜索结果`);

    // 第三步：天眼查API
    console.log('\n📌 步骤2: 查询天眼查工商信息...');
    const tianyanchaDataRaw = await runPythonScript('src/python/search/tianyancha_api.py', {
        company_name: companyName
    });
    const tianyanchaData = JSON.parse(tianyanchaDataRaw);

    // 第四步：AI实体提取（带行业背景）
    console.log('\n📌 步骤3: AI分析提取结构化信息...');
    const llmAnalysisRaw = await runPythonScript('src/python/ai/entity_extractor.py', {
        search_results: JSON.stringify(searchResults),
        tianyancha_data: JSON.stringify(tianyanchaData),
        industry_context: JSON.stringify(industryContext)
    });
    const llmAnalysis = JSON.parse(llmAnalysisRaw);

    console.log(`   📊 置信度: ${llmAnalysis.confidence_score || 'N/A'}`);
    if (llmAnalysis.competitive_advantages?.length) {
        console.log(`   💪 竞争优势: ${llmAnalysis.competitive_advantages.slice(0, 2).join(', ')}`);
    }
    if (llmAnalysis.recommendations?.length) {
        console.log(`   📋 建议: ${llmAnalysis.recommendations[0]}`);
    }

    // 第五步：输出结果
    console.log('\n📌 步骤4: 生成输出文件...');
    const outputData = {
        company_name: llmAnalysis.company_name || companyName,
        collected_at: new Date().toISOString(),
        sources: ['tavily', 'baidu', 'tianyancha', 'industry_research'],
        search_results: searchResults,
        industry_context: industryContext,
        raw_data: {
            tianyancha: tianyanchaData
        },
        llm_analysis: llmAnalysis
    };

    // JSON导出
    if (config.output.json) {
        const jsonPath = await runPythonScript('src/python/output/json_exporter.py', {
            data: JSON.stringify(outputData),
            company_name: companyName
        });
        console.log(`✅ JSON已保存: ${jsonPath}`);
    }

    // Markdown报告
    if (config.output.markdown) {
        const mdPath = await runPythonScript('src/python/output/markdown_reporter.py', {
            data: JSON.stringify(outputData)
        });
        console.log(`✅ 报告已生成: ${mdPath}`);
    }

    console.log('\n✨ 收集完成！');
    return outputData;
}

function runPythonScript(scriptPath, args) {
    return new Promise((resolve, reject) => {
        const argList = Object.entries(args).map(([k, v]) => `${k}=${v}`);
        const env = { ...process.env, PYTHONIOENCODING: 'utf-8' };
        const proc = spawn('python', [scriptPath, ...argList], { env });

        let stdout = '';
        let stderr = '';
        proc.stdout.on('data', (data) => { stdout += data.toString(); });
        proc.stderr.on('data', (data) => { stderr += data.toString(); });

        proc.on('close', (code) => {
            if (code === 0) resolve(stdout.trim());
            else {
                console.error('Python stderr:', stderr.substring(0, 500));
                reject(new Error(`Python script failed with code ${code}`));
            }
        });
    });
}

module.exports = { runCollector };