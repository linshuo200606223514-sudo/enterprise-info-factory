# 客户变更监控与预警实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现客户变更监控服务，检测法人变更和司法风险新增，自动推送企业微信预警

**Architecture:** 变更监控作为独立服务，定时扫描已监控客户列表，与缓存数据比对，检测到变更后记录到 alerts 表并推送企业微信消息

**Tech Stack:** Node.js (纯 JavaScript), node-cron

---

## 文件结构

```
api/services/
├── changeMonitor.js    # 新增：变更监控服务
├── creditScorer.js     # 现有：信用评分
└── wechatNotifier.js   # 新增：企业微信通知

server/jobs/
└── monitor.js          # 新增：定时任务入口

server/routes/
└── alerts.js           # 新增：预警记录查询 API

database/
└── init.sql           # 修改：新增 alerts 和 company_cache 表
```

---

## Task 1: 创建 wechatNotifier.js 企业微信通知服务

**Files:**
- Create: `api/services/wechatNotifier.js`

- [ ] **Step 1: 创建 wechatNotifier.js**

```javascript
/**
 * 企业微信通知服务
 */

const https = require('https');
const http = require('http');

/**
 * 发送企业微信消息
 * @param {Object} message - 消息内容
 * @returns {Promise<boolean>} 发送是否成功
 */
async function sendWechatMessage(message) {
  const webhookUrl = process.env.WECHAT_WEBHOOK_URL;

  if (!webhookUrl) {
    console.error('WECHAT_WEBHOOK_URL 环境变量未配置');
    return false;
  }

  return new Promise((resolve, reject) => {
    const url = new URL(webhookUrl);
    const options = {
      hostname: url.hostname,
      port: 443,
      path: url.pathname + url.search,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const result = JSON.parse(data);
          if (result.errcode === 0) {
            console.log('企业微信消息发送成功');
            resolve(true);
          } else {
            console.error('企业微信消息发送失败:', result.errmsg);
            resolve(false);
          }
        } catch (e) {
          reject(e);
        }
      });
    });

    req.on('error', (e) => {
      console.error('企业微信消息发送异常:', e.message);
      resolve(false);
    });

    req.write(JSON.stringify(message));
    req.end();
  });
}

/**
 * 构建风险预警消息
 * @param {Object} alert - 预警数据
 * @returns {Object} 企业微信消息格式
 */
function buildAlertMessage(alert) {
  const { company_name, change_type, old_value, new_value, old_score, new_score, old_grade, new_grade, created_at } = alert;

  const levelEmoji = {
    '紧急': '🔴',
    '高': '🟠'
  };

  const emoji = levelEmoji[alert.level] || '⚠️';

  let scoreChange = '';
  if (old_score && new_score) {
    scoreChange = `信用评分从 ${old_score} → ${new_score}，等级 ${old_grade} → ${new_grade}`;
  }

  return {
    msgtype: 'markdown',
    markdown: {
      content: `${emoji} **客户风险预警**\n\n**公司**：${company_name}\n**变更类型**：${change_type}\n${old_value ? `**原值**：${old_value}` : ''}\n${new_value ? `**新值**：${new_value}` : ''}\n${scoreChange ? `**影响**：${scoreChange}` : ''}\n**时间**：${new Date(created_at).toLocaleString('zh-CN')}`
    }
  };
}

/**
 * 发送测试消息
 * @returns {Promise<boolean>}
 */
async function sendTestMessage() {
  const message = {
    msgtype: 'markdown',
    markdown: {
      content: '🟢 **测试消息**\n\n这是一条来自 AI 企业信息工厂的测试消息，监控系统运行正常。\n**时间**：' + new Date().toLocaleString('zh-CN')
    }
  };

  return sendWechatMessage(message);
}

module.exports = {
  sendWechatMessage,
  buildAlertMessage,
  sendTestMessage
};
```

- [ ] **Step 2: 测试消息发送功能**

```bash
cd c:/Users/clown/.worktrees/listening-miniprogram/enterprise-info-factory && node -e "
const { buildAlertMessage, sendTestMessage } = require('./api/services/wechatNotifier');

// 测试消息构建
const testAlert = {
  company_name: '测试纸业公司',
  change_type: '法人变更',
  old_value: '张三',
  new_value: '李四',
  old_score: 82,
  new_score: 75,
  old_grade: 'A',
  new_grade: 'B',
  level: '高',
  created_at: new Date().toISOString()
};

const msg = buildAlertMessage(testAlert);
console.log('消息格式:', JSON.stringify(msg, null, 2));

// 注意：实际发送需要配置 WECHAT_WEBHOOK_URL 环境变量
// console.log('发送测试消息:', await sendTestMessage());
"
```

Expected: 输出正确的 markdown 消息格式

- [ ] **Step 3: Commit**

```bash
git add api/services/wechatNotifier.js
git commit -m "feat: add wechat notifier service"
```

---

## Task 2: 创建数据库表和 changeMonitor.js 监控服务

**Files:**
- Create: `api/services/changeMonitor.js`
- Modify: `database/init.sql`

- [ ] **Step 1: 添加数据库表**

在 `database/init.sql` 末尾添加：

```sql
-- 预警记录表
CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company_name TEXT NOT NULL,
  change_type TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  old_score INTEGER,
  new_score INTEGER,
  old_grade TEXT,
  new_grade TEXT,
  alert_sent INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_alerts_company ON alerts(company_name);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at);

-- 企业缓存表（存储最新数据用于变更比对）
CREATE TABLE IF NOT EXISTS company_cache (
  company_name TEXT PRIMARY KEY,
  data TEXT NOT NULL,
  credit_score INTEGER,
  credit_grade TEXT,
  updated_at TEXT DEFAULT (datetime('now'))
);
```

- [ ] **Step 2: 创建 changeMonitor.js**

```javascript
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
      // 判断预警级别
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

  const result = db.exec(`
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

  return result;
}

/**
 * 执行变更监控
 * @param {string} companyName
 * @returns {Array} 检测到的变更列表
 */
async function monitorCompany(companyName) {
  try {
    // 1. 获取缓存数据
    const cached = await getCachedData(companyName);

    // 2. 采集最新数据
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

    // 3. 合并数据
    const mergedData = mergeCompanyData(successResults);

    // 4. 如果没有缓存，直接缓存并返回
    if (!cached) {
      const newScore = generateCreditScore(mergedData);
      await updateCache(companyName, mergedData, newScore.credit_score, newScore.credit_grade);
      console.log(`[监控] ${companyName}: 新增客户，缓存完成`);
      return [];
    }

    // 5. 检测变更
    const changes = detectChanges(cached.data, mergedData);

    if (changes.length === 0) {
      console.log(`[监控] ${companyName}: 无变更`);
      return [];
    }

    console.log(`[监控] ${companyName}: 检测到 ${changes.length} 项变更`);

    // 6. 重新计算评分
    const newScore = generateCreditScore(mergedData);

    // 7. 处理每个变更
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

      // 保存预警记录
      await saveAlert(alert);

      // 发送微信通知
      const wechatMsg = buildAlertMessage(alert);
      const sent = await sendWechatMessage(wechatMsg);

      if (sent) {
        // 更新发送状态
        const db = require('../database').getDb();
        db.exec(`UPDATE alerts SET alert_sent = 1 WHERE company_name = ? AND change_type = ? AND created_at = datetime('now')`, [companyName, change.type]);
      }
    }

    // 8. 更新缓存
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
```

- [ ] **Step 3: 测试变更检测函数**

```bash
cd c:/Users/clown/.worktrees/listening-miniprogram/enterprise-info-factory && node -e "
const { detectChanges } = require('./api/services/changeMonitor');

// 测试1: 法人变更
const old1 = { legal_representative: '张三', judicial_risks: [] };
const new1 = { legal_representative: '李四', judicial_risks: [] };
console.log('法人变更:', detectChanges(old1, new1));

// 测试2: 司法风险新增
const old2 = { legal_representative: '王五', judicial_risks: [] };
const new2 = { legal_representative: '王五', judicial_risks: [{ type: '被执行人' }] };
console.log('司法风险新增:', detectChanges(old2, new2));

// 测试3: 失信人新增（紧急）
const old3 = { legal_representative: '赵六', judicial_risks: [{ type: '被执行人' }] };
const new3 = { legal_representative: '赵六', judicial_risks: [{ type: '被执行人' }, { type: '失信人' }] };
console.log('失信人新增:', detectChanges(old3, new3));

// 测试4: 无变更
const old4 = { legal_representative: '孙七', judicial_risks: [] };
const new4 = { legal_representative: '孙七', judicial_risks: [] };
console.log('无变更:', detectChanges(old4, new4));
"
```

Expected:
- 法人变更: 返回包含 type='法人变更' 的变更对象
- 司法风险新增: 返回包含 type='司法风险新增' 的变更对象
- 失信人新增: level='紧急'
- 无变更: 返回空数组

- [ ] **Step 4: Commit**

```bash
git add database/init.sql api/services/changeMonitor.js
git commit -m "feat: add change monitor service with alert tracking"
```

---

## Task 3: 创建 alerts API 路由

**Files:**
- Create: `server/routes/alerts.js`
- Modify: `server/server.js`

- [ ] **Step 1: 创建 alerts.js 路由**

```javascript
const express = require('express');
const router = express.Router();

/**
 * GET /api/alerts - 查询预警历史
 */
router.get('/', (req, res) => {
  try {
    const { page = 1, limit = 20 } = req.query;
    const offset = (parseInt(page) - 1) * parseInt(limit);

    const db = require('../database').getDb();

    // 查询总数
    const countResult = db.exec('SELECT COUNT(*) as total FROM alerts');
    const total = countResult[0].values[0][0];

    // 查询列表
    const rows = db.exec(`
      SELECT id, company_name, change_type, old_value, new_value,
             old_score, new_score, old_grade, new_grade, alert_sent, created_at
      FROM alerts
      ORDER BY created_at DESC
      LIMIT ? OFFSET ?
    `, [parseInt(limit), offset]);

    const alerts = rows[0].values.map(row => ({
      id: row[0],
      company_name: row[1],
      change_type: row[2],
      old_value: row[3],
      new_value: row[4],
      old_score: row[5],
      new_score: row[6],
      old_grade: row[7],
      new_grade: row[8],
      alert_sent: row[9] === 1,
      created_at: row[10]
    }));

    res.json({
      success: true,
      data: {
        alerts,
        total,
        page: parseInt(page),
        limit: parseInt(limit)
      }
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * GET /api/alerts/:companyName - 查询指定客户的预警历史
 */
router.get('/:companyName', (req, res) => {
  try {
    const { companyName } = req.params;
    const db = require('../database').getDb();

    const rows = db.exec(`
      SELECT id, company_name, change_type, old_value, new_value,
             old_score, new_score, old_grade, new_grade, alert_sent, created_at
      FROM alerts
      WHERE company_name = ?
      ORDER BY created_at DESC
    `, [companyName]);

    const alerts = rows[0].values.map(row => ({
      id: row[0],
      company_name: row[1],
      change_type: row[2],
      old_value: row[3],
      new_value: row[4],
      old_score: row[5],
      new_score: row[6],
      old_grade: row[7],
      new_grade: row[8],
      alert_sent: row[9] === 1,
      created_at: row[10]
    }));

    res.json({
      success: true,
      data: {
        alerts,
        total: alerts.length
      }
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * POST /api/alerts/test - 测试预警推送
 */
router.post('/test', async (req, res) => {
  try {
    const { sendTestMessage } = require('../../api/services/wechatNotifier');
    const sent = await sendTestMessage();

    if (sent) {
      res.json({ success: true, message: '测试预警推送成功' });
    } else {
      res.status(500).json({ success: false, error: '测试预警推送失败，请检查 WECHAT_WEBHOOK_URL 配置' });
    }
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;
```

- [ ] **Step 2: 在 server.js 中注册路由**

在 `server/server.js` 中添加：

```javascript
// 在其他路由引入后，添加
const alertsRouter = require('./routes/alerts');
app.use('/api/alerts', alertsRouter);
```

- [ ] **Step 3: 测试 alerts API**

```bash
cd c:/Users/clown/.worktrees/listening-miniprogram/enterprise-info-factory && node -e "
// 测试 alerts API 路由存在性
const router = require('./server/routes/alerts');
console.log('alerts router:', Object.keys(router));
"
```

- [ ] **Step 4: Commit**

```bash
git add server/routes/alerts.js server/server.js
git commit -m "feat: add alerts API routes"
```

---

## Task 4: 创建定时任务入口

**Files:**
- Create: `server/jobs/monitor.js`
- Modify: `server/server.js`

- [ ] **Step 1: 创建 monitor.js 定时任务入口**

```javascript
/**
 * 定时任务入口
 */

const cron = require('node-cron');
const { runDailyMonitor } = require('../api/services/changeMonitor');

let isRunning = false;

/**
 * 启动每日监控定时任务
 * 执行时间：每日 08:00
 */
function startDailyMonitor() {
  console.log('[定时任务] 每日监控已启动，执行时间：每天 08:00');

  cron.schedule('0 8 * * *', async () => {
    if (isRunning) {
      console.log('[定时任务] 上一次任务仍在执行中，跳过本次');
      return;
    }

    isRunning = true;
    try {
      await runDailyMonitor();
    } catch (error) {
      console.error('[定时任务] 执行异常:', error.message);
    } finally {
      isRunning = false;
    }
  });
}

/**
 * 手动触发一次监控任务
 */
async function triggerMonitor() {
  if (isRunning) {
    console.log('[定时任务] 上一次任务仍在执行中');
    return { running: true };
  }

  isRunning = true;
  try {
    const result = await runDailyMonitor();
    return { running: false, ...result };
  } catch (error) {
    console.error('[定时任务] 执行异常:', error.message);
    return { running: false, error: error.message };
  } finally {
    isRunning = false;
  }
}

module.exports = {
  startDailyMonitor,
  triggerMonitor
};
```

- [ ] **Step 2: 在 server.js 中启动定时任务**

在 `server/server.js` 适当位置添加：

```javascript
// 在服务器启动后
const { startDailyMonitor } = require('./jobs/monitor');
startDailyMonitor();
```

- [ ] **Step 3: 添加手动触发端点（可选，便于调试）**

在 `server/server.js` 中添加：

```javascript
// 手动触发监控
app.post('/api/monitor/trigger', async (req, res) => {
  const { triggerMonitor } = require('./jobs/monitor');
  try {
    const result = await triggerMonitor();
    res.json({ success: true, data: result });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});
```

- [ ] **Step 4: Commit**

```bash
git add server/jobs/monitor.js server/server.js
git commit -m "feat: add scheduled monitor job"
```

---

## Task 5: 安装 node-cron 依赖

**Files:**
- Modify: `package.json`

- [ ] **Step 1: 安装依赖**

```bash
cd c:/Users/clown/.worktrees/listening-miniprogram/enterprise-info-factory && npm install node-cron
```

- [ ] **Step 2: Commit**

```bash
git add package.json package-lock.json
git commit -m "chore: add node-cron dependency"
```

---

## Task 6: 验收测试

- [ ] **Step 1: 测试变更检测**

```bash
node -e "
const { detectChanges } = require('./api/services/changeMonitor');

// 法人变更
const old1 = { legal_representative: '张三', judicial_risks: [] };
const new1 = { legal_representative: '李四', judicial_risks: [] };
console.log('法人变更:', detectChanges(old1, new1));

// 司法风险新增
const old2 = { legal_representative: '王五', judicial_risks: [] };
const new2 = { legal_representative: '王五', judicial_risks: [{ type: '被执行人' }] };
console.log('司法风险新增:', detectChanges(old2, new2));

// 失信人新增（紧急）
const old3 = { legal_representative: '赵六', judicial_risks: [{ type: '被执行人' }] };
const new3 = { legal_representative: '赵六', judicial_risks: [{ type: '被执行人' }, { type: '失信人' }] };
console.log('失信人新增:', detectChanges(old3, new3));
"
```

- [ ] **Step 2: 测试微信消息构建**

```bash
node -e "
const { buildAlertMessage } = require('./api/services/wechatNotifier');
const alert = {
  company_name: '测试纸业公司',
  change_type: '法人变更',
  old_value: '张三',
  new_value: '李四',
  old_score: 82,
  new_score: 75,
  old_grade: 'A',
  new_grade: 'B',
  level: '高',
  created_at: new Date().toISOString()
};
console.log(JSON.stringify(buildAlertMessage(alert), null, 2));
"
```

- [ ] **Step 3: 验证 alerts API**

```bash
curl http://localhost:3000/api/alerts
```

- [ ] **Step 4: 自检清单**

1. **Spec 覆盖检查：**
   - [ ] wechatNotifier.js 实现完整
   - [ ] changeMonitor.js 实现完整
   - [ ] detectChanges 函数正确检测法人变更和司法风险
   - [ ] alerts API 实现完整
   - [ ] 定时任务正确配置

2. **占位符检查：** 无 TBD/TODO

3. **数据正确性：**
   - [ ] 变更检测逻辑正确
   - [ ] 预警级别判定正确（失信/老赖=紧急，其他=高）
