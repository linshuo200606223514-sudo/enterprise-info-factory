/**
 * 客户变更监控服务
 */

const { runPythonScraper } = require('./aggregator');
const { mergeCompanyData } = require('./dataMerger');
const { generateCreditScore } = require('./creditScorer');
const { buildAlertMessage, sendWechatMessage } = require('./wechatNotifier');

/**
 * 检测数据变更
 * @param {Object} oldData - 旧数据
 * @param {Object} newData - 新数据
 * @returns {Array} 变更列表
 */
function detectChanges(oldData, newData) {
  const changes = [];

  // 法人变更
  if (oldData.legal_representative !== newData.legal_representative) {
    changes.push({
      type: '法人变更',
      field: 'legal_representative',
      old_value: oldData.legal_representative,
      new_value: newData.legal_representative
    });
  }

  // 司法风险新增
  const oldRiskTypes = new Set((oldData.judicial_risks || []).map(r => r.type));
  const newRiskTypes = (newData.judicial_risks || []).map(r => r.type);

  for (const riskType of newRiskTypes) {
    if (!oldRiskTypes.has(riskType)) {
      let level = '高';
      if (riskType === '失信人' || riskType === '老赖') {
        level = '紧急';
      }
      changes.push({
        type: '司法风险新增',
        field: 'judicial_risks',
        risk_type: riskType,
        old_value: null,
        new_value: riskType,
        level: level
      });
    }
  }

  return changes;
}

/**
 * 获取所有已监控客户
 * @returns {Array} 客户名称列表
 */
async function getMonitoredCompanies() {
  const db = require('../database').getDb();

  const rows = db.exec(`
    SELECT company_name FROM company_cache
    UNION
    SELECT name as company_name FROM enterprises
  `);

  if (!rows || rows.length === 0) return [];

  const companies = new Set();
  for (const row of rows[0].values) {
    companies.add(row[0]);
  }
  return Array.from(companies);
}

/**
 * 获取客户缓存数据
 * @param {string} companyName
 * @returns {Object|null}
 */
async function getCachedData(companyName) {
  const db = require('../database').getDb();

  const rows = db.exec(`
    SELECT data, credit_score, credit_grade FROM company_cache
    WHERE company_name = ?
  `, [companyName]);

  if (!rows || rows.length === 0 || rows[0].values.length === 0) {
    return null;
  }

  const [data, credit_score, credit_grade] = rows[0].values[0];
  return {
    data: JSON.parse(data),
    credit_score,
    credit_grade
  };
}

/**
 * 更新客户缓存
 * @param {string} companyName
 * @param {Object} data
 * @param {number} creditScore
 * @param {string} creditGrade
 */
async function updateCache(companyName, data, creditScore, creditGrade) {
  const db = require('../database').getDb();

  db.exec(`
    INSERT OR REPLACE INTO company_cache (company_name, data, credit_score, credit_grade, updated_at)
    VALUES (?, ?, ?, ?, datetime('now'))
  `, [companyName, JSON.stringify(data), creditScore, creditGrade]);
}

/**
 * 保存预警记录
 * @param {Object} alert
 * @returns {number} 预警ID
 */
async function saveAlert(alert) {
  const db = require('../database').getDb();

  db.exec(`
    INSERT INTO alerts (company_name, change_type, old_value, new_value, old_score, new_score, old_grade, new_grade, alert_sent, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
  `, [
    alert.company_name,
    alert.change_type,
    alert.old_value,
    alert.new_value,
    alert.old_score,
    alert.new_score,
    alert.old_grade,
    alert.new_grade,
    alert.alert_sent ? 1 : 0
  ]);

  return db.exec('SELECT last_insert_rowid()')[0].values[0][0];
}

/**
 * 执行变更监控
 * @param {string} companyName
 * @returns {Array} 检测到的变更列表
 */
async function monitorCompany(companyName) {
  try {
    const cached = await getCachedData(companyName);

    const scrapers = [
      { name: 'qichacha', args: [companyName] },
      { name: 'aiqicha', args: [companyName] },
      { name: 'qixin', args: [companyName] },
      { name: 'tianyancha', args: [companyName] }
    ];

    const results = await Promise.allSettled(
      scrapers.map(scraper => runPythonScraper(scraper.name, scraper.args))
    );

    const successResults = results
      .filter(r => r.status === 'fulfilled' && r.value && !r.value.error)
      .map(r => r.value);

    if (successResults.length === 0) {
      console.log(`[监控] ${companyName}: 所有数据源采集失败`);
      return [];
    }

    const mergedData = mergeCompanyData(successResults);

    if (!cached) {
      const newScore = generateCreditScore(mergedData);
      await updateCache(companyName, mergedData, newScore.credit_score, newScore.credit_grade);
      console.log(`[监控] ${companyName}: 新增客户，缓存完成`);
      return [];
    }

    const changes = detectChanges(cached.data, mergedData);

    if (changes.length === 0) {
      console.log(`[监控] ${companyName}: 无变更`);
      return [];
    }

    console.log(`[监控] ${companyName}: 检测到 ${changes.length} 项变更`);

    const newScore = generateCreditScore(mergedData);

    for (const change of changes) {
      const alert = {
        company_name: companyName,
        change_type: change.type,
        old_value: change.old_value,
        new_value: change.new_value,
        old_score: cached.credit_score,
        new_score: newScore.credit_score,
        old_grade: cached.credit_grade,
        new_grade: newScore.credit_grade,
        alert_sent: 0,
        level: change.level || '高'
      };

      await saveAlert(alert);

      const wechatMsg = buildAlertMessage(alert);
      await sendWechatMessage(wechatMsg);
    }

    await updateCache(companyName, mergedData, newScore.credit_score, newScore.credit_grade);

    return changes;
  } catch (error) {
    console.error(`[监控] ${companyName} 执行异常:`, error.message);
    return [];
  }
}

/**
 * 执行每日监控任务
 */
async function runDailyMonitor() {
  console.log('[监控] 开始执行每日监控任务...');

  const companies = await getMonitoredCompanies();
  console.log(`[监控] 共 ${companies.length} 个客户待监控`);

  let changedCount = 0;

  for (const companyName of companies) {
    const changes = await monitorCompany(companyName);
    if (changes.length > 0) {
      changedCount++;
    }
  }

  console.log(`[监控] 任务完成，${changedCount} 个客户发生变更`);
  return { total: companies.length, changed: changedCount };
}

module.exports = {
  detectChanges,
  monitorCompany,
  runDailyMonitor,
  getMonitoredCompanies,
  getCachedData,
  updateCache,
  saveAlert
};