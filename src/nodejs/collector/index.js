/**
 * 企业信息收集系统 - Node.js 编排层
 */
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// 加载配置
function loadConfig() {
    const configPath = path.join(__dirname, '../../config/settings.json');
    const configContent = fs.readFileSync(configPath, 'utf-8');
    return JSON.parse(configContent);
}

// 执行Python收集器
async function runCollector(companyName, options = {}) {
    const config = loadConfig();

    console.log(`🔍 开始收集企业信息: ${companyName}`);
    console.log(`📡 数据源: 百度搜索, 天眼查`);

    // 第一步：百度搜索
    console.log('\n🇬️ 步骤1: 执行百度搜索...');
    const searchResults = await runPythonScript('src/python/search/baidu_search.py', {
        keyword: companyName,
        max_results: config.search.baidu.max_results
    });

    // 第二步：天眼查API
    console.log('\n🇬️ 步骤2: 查询天眼查工商信息...');
    const tianyanchaData = await runPythonScript('src/python/search/tianyancha_api.py', {
        company_name: companyName
    });

    // 第三步：AI实体提取
    console.log('\n🇬️ 步骤3: AI分析提取结构化信息...');
    const structuredData = await runPythonScript('src/python/ai/entity_extractor.py', {
        search_results: JSON.stringify(searchResults),
        tianyancha_data: JSON.stringify(tianyanchaData)
    });

    // 第四步：输出结果
    console.log('\n🇬️ 步骤4: 生成输出文件...');
    const outputData = {
        company_name: companyName,
        sources: ['baidu', 'tianyancha'],
        raw_data: { search_results: searchResults, tianyancha: tianyanchaData },
        structured: structuredData
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

// 运行Python脚本的辅助函数
function runPythonScript(scriptPath, args) {
    return new Promise((resolve, reject) => {
        const argList = Object.entries(args).map(([k, v]) => `${k}=${v}`);
        const proc = spawn('python', [scriptPath, ...argList], { shell: true });

        let stdout = '';
        proc.stdout.on('data', (data) => { stdout += data.toString(); });
        proc.stderr.on('data', (data) => { console.error(data.toString()); });

        proc.on('close', (code) => {
            if (code === 0) resolve(stdout.trim());
            else reject(new Error(`Python script failed with code ${code}`));
        });
    });
}

module.exports = { runCollector };