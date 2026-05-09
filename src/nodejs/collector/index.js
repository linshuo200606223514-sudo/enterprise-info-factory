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

    console.log(`🔍 开始收集企业信息: ${companyName}`);
    console.log(`📡 数据源: 百度搜索, 天眼查`);
    console.log(`🤖 AI分析: LLM驱动`);

    console.log('\n📌 步骤1: 执行百度搜索...');
    const searchResultsRaw = await runPythonScript('src/python/search/baidu_search.py', {
        keyword: companyName,
        max_results: config.search.baidu.max_results
    });
    const searchResults = JSON.parse(searchResultsRaw);

    console.log('\n📌 步骤2: 查询天眼查工商信息...');
    const tianyanchaDataRaw = await runPythonScript('src/python/search/tianyancha_api.py', {
        company_name: companyName
    });
    const tianyanchaData = JSON.parse(tianyanchaDataRaw);

    console.log('\n📌 步骤3: AI分析提取结构化信息...');
    const llmAnalysisRaw = await runPythonScript('src/python/ai/entity_extractor.py', {
        search_results: JSON.stringify(searchResults),
        tianyancha_data: JSON.stringify(tianyanchaData)
    });
    const llmAnalysis = JSON.parse(llmAnalysisRaw);

    console.log(`   📊 置信度: ${llmAnalysis.confidence_score || 'N/A'}`);

    console.log('\n📌 步骤4: 生成输出文件...');
    const outputData = {
        company_name: llmAnalysis.company_name || companyName,
        collected_at: new Date().toISOString(),
        sources: ['baidu', 'tianyancha'],
        raw_data: {
            search_results: searchResults,
            tianyancha: tianyanchaData
        },
        llm_analysis: llmAnalysis
    };

    if (config.output.json) {
        const jsonPath = await runPythonScript('src/python/output/json_exporter.py', {
            data: JSON.stringify(outputData),
            company_name: companyName
        });
        console.log(`✅ JSON已保存: ${jsonPath}`);
    }

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