/**
 * 数据聚合服务
 * 并行调用Python采集器，聚合结果
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const { analyzeCompany, saveMetaConfig } = require('../../analyzer');

/**
 * 调用Python采集器
 * @param {string} scriptName - 脚本名称（不含.py后缀）
 * @param {Array<string>} args - 命令行参数
 * @returns {Promise<Object>} - 返回解析后的JSON结果
 */
function runPythonScraper(scriptName, args = []) {
  return new Promise((resolve, reject) => {
    const scrapersDir = path.join(__dirname, '../../scrapers');
    const scriptPath = path.join(scrapersDir, `${scriptName}.py`);

    // 检查脚本是否存在
    if (!fs.existsSync(scriptPath)) {
      reject(new Error(`Python脚本不存在: ${scriptPath}`));
      return;
    }

    console.log(`[Aggregator] 调用Python采集器: ${scriptName}`);
    console.log(`[Aggregator] 脚本路径: ${scriptPath}`);
    console.log(`[Aggregator] 参数: ${args.join(' ')}`);

    const pythonProcess = spawn('python', [scriptPath, ...args], {
      cwd: scrapersDir,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let stdout = '';
    let stderr = '';

    pythonProcess.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        console.error(`[Aggregator] Python脚本错误 (code ${code}): ${stderr}`);
        reject(new Error(`Python脚本执行失败: ${stderr}`));
        return;
      }

      try {
        // 尝试解析JSON输出
        const trimmedStdout = stdout.trim();
        if (trimmedStdout) {
          const result = JSON.parse(trimmedStdout);
          resolve(result);
        } else {
          resolve({});
        }
      } catch (e) {
        // 如果不是JSON，直接返回原始输出
        console.log(`[Aggregator] 非JSON输出: ${stdout}`);
        resolve({ rawOutput: stdout });
      }
    });

    pythonProcess.on('error', (err) => {
      reject(new Error(`启动Python进程失败: ${err.message}`));
    });
  });
}

/**
 * 并行调用多个采集器收集企业信息
 * @param {string} enterpriseName - 企业名称
 * @param {Object} options - 配置选项
 * @param {string} options.outputDir - 输出目录，默认为项目output目录
 * @returns {Promise<Object>} - 聚合后的企业信息
 */
async function searchEnterprise(enterpriseName, options = {}) {
  const outputDir = options.outputDir || path.join(__dirname, '../../output');
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');

  console.log(`[Aggregator] 开始收集企业信息: ${enterpriseName}`);

  // 并行调用百度搜索、天眼查和行业网站采集器
  const scrapers = [
    { name: 'baidu_search', args: [enterpriseName] },
    { name: 'tianyancha', args: [enterpriseName] },
    { name: 'industry_sites', args: [enterpriseName] }
  ];

  const results = await Promise.allSettled(
    scrapers.map(scraper => runPythonScraper(scraper.name, scraper.args))
  );

  // 聚合结果
  const aggregatedResult = {
    enterpriseName,
    collectedAt: new Date().toISOString(),
    sources: [],
    data: {},
    errors: []
  };

  results.forEach((result, index) => {
    const scraperName = scrapers[index].name;

    if (result.status === 'fulfilled') {
      console.log(`[Aggregator] ${scraperName} 采集成功`);
      aggregatedResult.sources.push(scraperName);
      aggregatedResult.data[scraperName] = result.value;
    } else {
      console.error(`[Aggregator] ${scraperName} 采集失败: ${result.reason.message}`);
      aggregatedResult.errors.push({
        source: scraperName,
        error: result.reason.message
      });
    }
  });

  // 添加行业网站结果
  aggregatedResult.industry = results[2].value;

  // 调用 AI 痛点分析模块
  try {
    console.log('[Aggregator] 开始 AI 痛点分析...');
    const painPoints = await analyzeCompany(aggregatedResult);
    aggregatedResult.painPoints = painPoints;
    console.log('[Aggregator] AI 痛点分析完成');

    // 保存元模型配置
    const outputDir = path.join(__dirname, '../../output');
    await saveMetaConfig(painPoints.metaConfig, outputDir);
    console.log('[Aggregator] 元模型配置已保存');
  } catch (err) {
    console.error('[Aggregator] AI 痛点分析失败:', err.message);
  }

  // 保存结果到JSON文件
  const outputPath = path.join(outputDir, `${enterpriseName}_${timestamp}.json`);
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(aggregatedResult, null, 2));

  console.log(`[Aggregator] 数据已保存到: ${outputPath}`);
  console.log(`[Aggregator] 收集完成，成功 ${aggregatedResult.sources.length}/${scrapers.length} 个源`);

  return aggregatedResult;
}

/**
 * 串行执行采集器（用于需要顺序执行的场景）
 * @param {Array<{name: string, args: Array<string>}>} scrapers - 采集器列表
 * @returns {Promise<Array<Object>>} - 各采集器结果
 */
async function runScrapersSequentially(scrapers) {
  const results = [];

  for (const scraper of scrapers) {
    try {
      const result = await runPythonScraper(scraper.name, scraper.args);
      results.push({ success: true, data: result });
    } catch (err) {
      results.push({ success: false, error: err.message });
    }
  }

  return results;
}

module.exports = {
  runPythonScraper,
  searchEnterprise,
  runScrapersSequentially
};