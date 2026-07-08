# 人工介入流程实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 爬虫遇到反爬机制时自动创建人工待办，真实人员手动补充数据后继续流程

**Architecture:** 当爬虫返回 `requires_login: true` 或明确反爬信号时，aggregator 层自动创建 `manual_tasks` 记录。人工完成录入后，系统继续正常流程。人工待办有独立的 REST API 和状态管理。

**Tech Stack:** Express.js, sql.js, node-cron

---

## Task 1: 添加 manual_tasks 表

**Files:**
- Modify: `server/db/init.js:77` (在 SCHEMA_SQL 末尾添加新表)

- [ ] **Step 1: 添加 manual_tasks 表定义**

在 `SCHEMA_SQL` 末尾（`alerts` 表之后）添加：

```javascript
CREATE TABLE IF NOT EXISTS manual_tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company_name TEXT NOT NULL,
  source TEXT NOT NULL,
  reason TEXT NOT NULL,
  raw_data TEXT,
  required_fields TEXT,
  status TEXT DEFAULT 'pending',
  assigned_to TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME
);
```

- [ ] **Step 2: 运行 init.js 创建新表**

Run: `node server/db/init.js`
Expected: 输出 "数据库初始化完成"

- [ ] **Step 3: 验证表已创建**

Run: `node -e "const {ensureDb}=require('./server/db'); ensureDb().then(()=>{ const db=require('./server/db').getDb(); console.log(db.all(\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\").map(r=>r.name).join(', ')); process.exit(0); })"`
Expected: 包含 `manual_tasks`

- [ ] **Step 4: 提交**

```bash
git add server/db/init.js
git commit -m "feat: 添加 manual_tasks 表用于人工介入流程"
```

---

## Task 2: 创建 manualIntervention 服务

**Files:**
- Create: `server/services/manualIntervention.js`

- [ ] **Step 1: 创建服务文件**

Create `server/services/manualIntervention.js`:

```javascript
const { getDb } = require('../db');

class ManualInterventionService {
  /**
   * 创建人工待办
   * @param {Object} params
   * @param {string} params.companyName - 企业名称
   * @param {string} params.source - 数据源（qichacha/tianyancha/aiqicha/qixin）
   * @param {string} params.reason - 原因（如 "requires_login", "captcha", "blocked"）
   * @param {string} params.rawData - 爬虫返回的原始数据（JSON字符串）
   * @param {Array} params.requiredFields - 需要人工补充的字段列表
   * @returns {Object} 创建的待办记录
   */
  createTask({ companyName, source, reason, rawData = null, requiredFields = [] }) {
    const db = getDb();
    db.run(
      `INSERT INTO manual_tasks (company_name, source, reason, raw_data, required_fields, status)
       VALUES (?, ?, ?, ?, ?, 'pending')`,
      [companyName, source, reason, rawData ? JSON.stringify(rawData) : null, JSON.stringify(requiredFields)]
    );
    const result = db.get('SELECT last_insert_rowid() as id');
    return { id: result.id, company_name: companyName, source, reason, status: 'pending' };
  }

  /**
   * 获取所有待处理人工任务
   * @param {Object} options
   * @param {string} options.status - pending/in_progress/completed
   * @param {string} options.assignedTo - 按负责人筛选
   * @returns {Array}
   */
  getTasks({ status = null, assignedTo = null } = {}) {
    const db = getDb();
    let sql = 'SELECT * FROM manual_tasks WHERE 1=1';
    const params = [];
    if (status) {
      sql += ' AND status = ?';
      params.push(status);
    }
    if (assignedTo) {
      sql += ' AND assigned_to = ?';
      params.push(assignedTo);
    }
    sql += ' ORDER BY created_at DESC';
    return db.all(sql, params);
  }

  /**
   * 获取单个任务详情
   * @param {number} id
   * @returns {Object|null}
   */
  getTaskById(id) {
    const db = getDb();
    const task = db.get('SELECT * FROM manual_tasks WHERE id = ?', [id]);
    if (task && task.raw_data) {
      try { task.raw_data = JSON.parse(task.raw_data); } catch (e) {}
    }
    if (task && task.required_fields) {
      try { task.required_fields = JSON.parse(task.required_fields); } catch (e) {}
    }
    return task;
  }

  /**
   * 完成任务并更新企业数据
   * @param {number} id
   * @param {Object} data - 人工录入的数据
   * @returns {Object}
   */
  completeTask(id, data) {
    const db = getDb();
    db.run(
      `UPDATE manual_tasks SET status = 'completed', updated_at = datetime('now'), completed_at = datetime('now') WHERE id = ?`,
      [id]
    );
    return this.getTaskById(id);
  }

  /**
   * 更新任务状态
   * @param {number} id
   * @param {string} status - pending/in_progress/completed
   * @param {string} assignedTo - 负责人
   */
  updateTaskStatus(id, status, assignedTo = null) {
    const db = getDb();
    if (assignedTo) {
      db.run(
        `UPDATE manual_tasks SET status = ?, assigned_to = ?, updated_at = datetime('now') WHERE id = ?`,
        [status, assignedTo, id]
      );
    } else {
      db.run(
        `UPDATE manual_tasks SET status = ?, updated_at = datetime('now') WHERE id = ?`,
        [status, id]
      );
    }
  }

  /**
   * 删除任务
   * @param {number} id
   */
  deleteTask(id) {
    const db = getDb();
    db.run('DELETE FROM manual_tasks WHERE id = ?', [id]);
    return { success: true };
  }

  /**
   * 获取任务统计
   * @returns {Object}
   */
  getStats() {
    const db = getDb();
    const pending = db.get("SELECT COUNT(*) as count FROM manual_tasks WHERE status = 'pending'");
    const inProgress = db.get("SELECT COUNT(*) as count FROM manual_tasks WHERE status = 'in_progress'");
    const completed = db.get("SELECT COUNT(*) as count FROM manual_tasks WHERE status = 'completed'");
    return {
      pending: pending.count,
      in_progress: inProgress.count,
      completed: completed.count,
      total: pending.count + inProgress.count + completed.count
    };
  }
}

module.exports = new ManualInterventionService();
```

- [ ] **Step 2: 测试服务是否正常加载**

Run: `node -e "const s=require('./server/services/manualIntervention'); console.log('service loaded:', !!s.createTask)"`
Expected: `service loaded: true`

- [ ] **Step 3: 提交**

```bash
git add server/services/manualIntervention.js
git commit -m "feat: 添加人工介入服务 ManualInterventionService"
```

---

## Task 3: 创建人工待办路由

**Files:**
- Create: `server/routes/manualTasks.js`

- [ ] **Step 1: 创建路由文件**

Create `server/routes/manualTasks.js`:

```javascript
const express = require('express');
const router = express.Router();
const manualIntervention = require('../services/manualIntervention');

// GET /api/manual-tasks - 获取所有任务
router.get('/', (req, res) => {
  try {
    const { status, assigned_to } = req.query;
    const tasks = manualIntervention.getTasks({ status, assignedTo: assigned_to });
    res.json({ success: true, data: tasks });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// GET /api/manual-tasks/stats - 获取统计
router.get('/stats', (req, res) => {
  try {
    const stats = manualIntervention.getStats();
    res.json({ success: true, data: stats });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// GET /api/manual-tasks/:id - 获取单个任务
router.get('/:id', (req, res) => {
  try {
    const task = manualIntervention.getTaskById(req.params.id);
    if (!task) {
      return res.status(404).json({ success: false, error: '任务不存在' });
    }
    res.json({ success: true, data: task });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// PATCH /api/manual-tasks/:id/status - 更新任务状态
router.patch('/:id/status', (req, res) => {
  try {
    const { status, assigned_to } = req.body;
    if (!['pending', 'in_progress', 'completed'].includes(status)) {
      return res.status(400).json({ success: false, error: '无效的状态' });
    }
    manualIntervention.updateTaskStatus(req.params.id, status, assigned_to);
    res.json({ success: true, data: manualIntervention.getTaskById(req.params.id) });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// POST /api/manual-tasks/:id/complete - 完成任务并录入数据
router.post('/:id/complete', (req, res) => {
  try {
    const { data } = req.body;
    if (!data) {
      return res.status(400).json({ success: false, error: '缺少 data 参数' });
    }
    const task = manualIntervention.completeTask(req.params.id, data);
    res.json({ success: true, data: task, message: '任务已完成' });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// DELETE /api/manual-tasks/:id - 删除任务
router.delete('/:id', (req, res) => {
  try {
    manualIntervention.deleteTask(req.params.id);
    res.json({ success: true, message: '任务已删除' });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;
```

- [ ] **Step 2: 在 server/index.js 中注册路由**

找到 `server/index.js`，在 `alertsRoutes` 之后添加：

```javascript
const manualTasksRoutes = require('./routes/manualTasks');
```

在 `app.use('/api/alerts', alertsRoutes);` 之后添加：

```javascript
app.use('/api/manual-tasks', manualTasksRoutes);
```

- [ ] **Step 3: 测试路由**

Run: `node server/index.js & sleep 2 && curl -s http://localhost:3000/api/manual-tasks/stats`
Expected: `{"success":true,"data":{"pending":0,"in_progress":0,"completed":0,"total":0}}`

- [ ] **Step 4: 提交**

```bash
git add server/routes/manualTasks.js server/index.js
git commit -m "feat: 添加人工待办 REST API"
```

---

## Task 4: 修改 aggregator 处理反爬

**Files:**
- Modify: `api/services/aggregator.js` (修改 runPythonScraper 函数)

- [ ] **Step 1: 修改 runPythonScraper 添加人工介入逻辑**

找到 `runPythonScraper` 函数，在 `pythonProcess.on('close', ...)` 的回调中，找到 JSON 解析后的处理逻辑，在 `resolve(result)` 之前添加：

```javascript
// 检查是否需要人工介入
if (result.requires_login || result.error) {
  const reason = result.requires_login ? 'requires_login' : result.error;
  console.log(`[Aggregator] ${scriptName} 需要人工介入: ${reason}`);

  // 异步创建人工待办（不阻塞返回）
  try {
    const { createTask } = require('../../server/services/manualIntervention');
    createTask({
      companyName: args[0] || '',
      source: scriptName,
      reason: reason,
      rawData: result
    });
    console.log(`[Aggregator] 已创建人工待办: ${args[0]} - ${scriptName}`);
  } catch (e) {
    console.error('[Aggregator] 创建人工待办失败:', e.message);
  }
}
```

找到 `runPythonScraper` 函数开头的 `const { spawn } = require('child_process');`，在这行下面添加：

```javascript
let manualIntervention = null;
// 延迟加载避免循环依赖
function getManualIntervention() {
  if (!manualIntervention) {
    try {
      manualIntervention = require('../../server/services/manualIntervention');
    } catch (e) {
      console.warn('[Aggregator] 无法加载人工介入服务:', e.message);
    }
  }
  return manualIntervention;
}
```

在文件顶部（`const path = require('path');` 之后）添加：

```javascript
// 延迟加载避免循环依赖
let _manualIntervention = null;
function getManualIntervention() {
  if (!_manualIntervention) {
    try {
      _manualIntervention = require('../server/services/manualIntervention');
    } catch (e) {
      // ignore
    }
  }
  return _manualIntervention;
}
```

- [ ] **Step 2: 测试反爬场景**

Run: `node -e "
const { runPythonScraper } = require('./api/services/aggregator');
runPythonScraper('qichacha', ['测试公司']).then(r => {
  console.log('requires_login:', r.requires_login);
  process.exit(0);
});
" 2>&1 | head -20`

- [ ] **Step 3: 提交**

```bash
git add api/services/aggregator.js
git commit -m "feat: aggregator 遇到反爬时自动创建人工待办"
```

---

## Task 5: 测试完整流程

- [ ] **Step 1: 启动服务器**

Run: `node server/index.js & sleep 2`

- [ ] **Step 2: 触发爬虫产生人工待办**

Run: `curl -s "http://localhost:3000/api/collect/%E6%B5%8B%E8%AF%95%E5%85%AC%E5%8F%B8/all"`

- [ ] **Step 3: 查询人工待办**

Run: `curl -s http://localhost:3000/api/manual-tasks`
Expected: 看到 pending 状态的任务

- [ ] **Step 4: 完成一个人工任务**

Run: `curl -s -X POST http://localhost:3000/api/manual-tasks/1/complete -H "Content-Type: application/json" -d '{"data":{"company_name":"测试公司","legal_representative":"张三"}}'`

- [ ] **Step 5: 验证统计**

Run: `curl -s http://localhost:3000/api/manual-tasks/stats`
Expected: completed 计数增加

---

## Task 6: 更新前端入口（可选）

**Files:**
- Check: `frontend/index.html` 是否需要添加人工待办入口

根据实际需要决定是否修改前端。