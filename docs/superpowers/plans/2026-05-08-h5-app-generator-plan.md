# H5 App Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 meta_config.json 元模型配置转换为真实可运行的 H5 管理页面，支持订单/库存/账款增删改查，数据通过 Node.js 后端持久化

**Architecture:** Node.js Express 后端 + SQLite 开发数据库 + 前端纯静态 H5 页面，前后端通过 REST API 通信，数据库层支持 SQLite/MySQL 适配器插拔

**Tech Stack:** Express 4.x, better-sqlite3, mysql2, vanilla JS (无框架依赖)

---

## 文件结构

```
enterprise-info-factory/
├── server/
│   ├── index.js                    # Express 入口
│   ├── routes/
│   │   └── enterprise.js           # 企业 CRUD + 业务数据路由
│   ├── db/
│   │   ├── index.js                # 数据库工厂，db.getClient()
│   │   ├── sqlite.js               # SQLite 适配器
│   │   ├── mysql.js                # MySQL 适配器
│   │   └── init.js                 # 数据库初始化脚本
│   ├── middleware/
│   │   └── cors.js                 # CORS 中间件
│   └── services/
│       └── enterpriseService.js     # 企业业务逻辑
├── frontend/
│   ├── index.html                  # 企业列表/仪表板
│   ├── pages/
│   │   ├── orders.html              # 订单管理
│   │   ├── inventory.html           # 库存管理
│   │   └── accounts.html            # 账款管理
│   └── assets/
│       ├── css/
│       │   └── main.css             # 统一样式
│       └── js/
│           ├── api.js              # API 调用封装
│           └── app.js              # 主应用逻辑
├── generator/
│   └── index.js                    # 读取 meta_config，生成页面
└── bin/
    └── import-enterprise.js         # 导入已有企业数据
```

---

## Task 1: 项目初始化和依赖安装

**Files:**
- Modify: `package.json`
- Create: `.env.example`

- [ ] **Step 1: 创建 .env.example**

```bash
PORT=3000
DATABASE_URL=sqlite:./data/enterprise.db
NODE_ENV=development
CORS_ORIGIN=http://localhost:3001
```

- [ ] **Step 2: 更新 package.json 添加依赖**

```json
{
  "scripts": {
    "start": "node server/index.js",
    "dev": "node server/index.js",
    "init-db": "node server/db/init.js",
    "import": "node bin/import-enterprise.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "better-sqlite3": "^9.4.0",
    "mysql2": "^3.6.0",
    "cors": "^2.8.5",
    "dotenv": "^16.3.1"
  }
}
```

- [ ] **Step 3: 安装依赖**

Run: `npm install`
Expected: added 5 packages

- [ ] **Step 4: 创建目录结构**

Run: `mkdir -p server/routes server/db server/middleware server/services frontend/pages frontend/assets/css frontend/assets/js generator data`

- [ ] **Step 5: Commit**

```bash
git add package.json .env.example
git commit -m "feat: add server dependencies and directory structure"
```

---

## Task 2: 数据库适配器层

**Files:**
- Create: `server/db/index.js`
- Create: `server/db/sqlite.js`
- Create: `server/db/mysql.js`

- [ ] **Step 1: 编写 SQLite 适配器**

```javascript
// server/db/sqlite.js
const Database = require('better-sqlite3');
const path = require('path');

class SqliteAdapter {
  constructor(dbPath) {
    this.db = new Database(dbPath);
    this.db.pragma('journal_mode = WAL');
  }

  run(sql, params = []) {
    return this.db.prepare(sql).run(...params);
  }

  get(sql, params = []) {
    return this.db.prepare(sql).get(...params);
  }

  all(sql, params = []) {
    return this.db.prepare(sql).all(...params);
  }

  close() {
    this.db.close();
  }
}

module.exports = SqliteAdapter;
```

- [ ] **Step 2: 编写 MySQL 适配器**

```javascript
// server/db/mysql.js
const mysql = require('mysql2/promise');

class MysqlAdapter {
  constructor(url) {
    // url: mysql://user:pass@host:port/database
    const u = new URL(url);
    this.pool = mysql.createPool({
      host: u.hostname,
      port: u.port || 3306,
      user: u.username,
      password: u.password,
      database: u.pathname.slice(1),
      waitForConnections: true,
      connectionLimit: 10
    });
  }

  async run(sql, params = []) {
    const [result] = await this.pool.execute(sql, params);
    return result;
  }

  async get(sql, params = []) {
    const [rows] = await this.pool.execute(sql, params);
    return rows[0] || null;
  }

  async all(sql, params = []) {
    const [rows] = await this.pool.execute(sql, params);
    return rows;
  }

  async close() {
    await this.pool.end();
  }
}

module.exports = MysqlAdapter;
```

- [ ] **Step 3: 编写数据库工厂**

```javascript
// server/db/index.js
const path = require('path');
const SqliteAdapter = require('./sqlite');
const MysqlAdapter = require('./mysql');

let dbInstance = null;

function createDbClient(databaseUrl) {
  if (databaseUrl.startsWith('mysql://')) {
    return new MysqlAdapter(databaseUrl);
  }
  // 默认 SQLite
  const dbPath = databaseUrl.replace('sqlite:', '') || './data/enterprise.db';
  const absolutePath = path.isAbsolute(dbPath) ? dbPath : path.join(__dirname, '../../', dbPath);
  return new SqliteAdapter(absolutePath);
}

function getDb() {
  if (!dbInstance) {
    const dbUrl = process.env.DATABASE_URL || 'sqlite:./data/enterprise.db';
    dbInstance = createDbClient(dbUrl);
  }
  return dbInstance;
}

function closeDb() {
  if (dbInstance) {
    dbInstance.close();
    dbInstance = null;
  }
}

module.exports = { getDb, closeDb };
```

- [ ] **Step 4: Commit**

```bash
git add server/db/index.js server/db/sqlite.js server/db/mysql.js
git commit -m "feat: add database adapter layer with SQLite and MySQL support"
```

---

## Task 3: 数据库初始化脚本

**Files:**
- Create: `server/db/init.js`
- Create: `data/.gitkeep`

- [ ] **Step 1: 编写数据库初始化脚本**

```javascript
// server/db/init.js
const path = require('path');
const fs = require('fs');
const { getDb, closeDb } = require('./index');

const SCHEMA_SQL = `
CREATE TABLE IF NOT EXISTS enterprises (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  industry TEXT,
  scale TEXT,
  meta_config TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  enterprise_id INTEGER NOT NULL,
  order_no TEXT NOT NULL,
  customer_name TEXT,
  product_name TEXT,
  quantity INTEGER DEFAULT 0,
  price REAL DEFAULT 0,
  status TEXT DEFAULT 'pending',
  delivery_date TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (enterprise_id) REFERENCES enterprises(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS inventory (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  enterprise_id INTEGER NOT NULL,
  item_name TEXT NOT NULL,
  category TEXT,
  quantity INTEGER DEFAULT 0,
  unit TEXT,
  min_stock INTEGER DEFAULT 0,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (enterprise_id) REFERENCES enterprises(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  enterprise_id INTEGER NOT NULL,
  type TEXT NOT NULL,
  customer_name TEXT,
  amount REAL DEFAULT 0,
  due_date TEXT,
  status TEXT DEFAULT 'unpaid',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (enterprise_id) REFERENCES enterprises(id) ON DELETE CASCADE
);
`;

function initDatabase() {
  const db = getDb();

  // 确保 data 目录存在
  const dataDir = path.join(__dirname, '../../data');
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }

  // 执行建表
  db.run(SCHEMA_SQL);

  console.log('数据库初始化完成');
  closeDb();
}

initDatabase();
```

- [ ] **Step 2: 创建 data/.gitkeep**

```bash
# data 目录用于存放 SQLite 数据库文件，保持目录存在
```

- [ ] **Step 3: 测试初始化**

Run: `node server/db/init.js`
Expected: 输出 "数据库初始化完成"

- [ ] **Step 4: 验证数据库文件**

Run: `ls -la data/`
Expected: 看到 `enterprise.db` 文件

- [ ] **Step 5: Commit**

```bash
git add server/db/init.js data/.gitkeep
git commit -m "feat: add database initialization script"
```

---

## Task 4: Express 服务器入口

**Files:**
- Create: `server/index.js`
- Create: `server/middleware/cors.js`

- [ ] **Step 1: 编写 CORS 中间件**

```javascript
// server/middleware/cors.js
const cors = require('cors');

function setupCors(app) {
  const origin = process.env.CORS_ORIGIN || 'http://localhost:3001';
  app.use(cors({
    origin,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
  }));
}

module.exports = { setupCors };
```

- [ ] **Step 2: 编写服务器入口**

```javascript
// server/index.js
require('dotenv').config();
const express = require('express');
const path = require('path');
const { setupCors } = require('./middleware/cors');
const enterpriseRoutes = require('./routes/enterprise');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());
setupCors(app);

// 静态文件服务（前端）
app.use(express.static(path.join(__dirname, '../frontend')));

// API 路由
app.use('/api', enterpriseRoutes);

// 健康检查
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// 启动服务器
app.listen(PORT, () => {
  console.log(`服务器运行在 http://localhost:${PORT}`);
  console.log(`环境: ${process.env.NODE_ENV || 'development'}`);
  console.log(`数据库: ${process.env.DATABASE_URL || 'sqlite:./data/enterprise.db'}`);
});

module.exports = app;
```

- [ ] **Step 3: 测试服务器启动**

Run: `node server/index.js`
Expected: 输出 "服务器运行在 http://localhost:3000"

- [ ] **Step 4: 测试健康检查**

Run: `curl http://localhost:3000/api/health`
Expected: `{"status":"ok","timestamp":"..."}`

- [ ] **Step 5: Commit**

```bash
git add server/index.js server/middleware/cors.js
git commit -m "feat: add Express server entry point with CORS"
```

---

## Task 5: 企业 CRUD 路由和服务

**Files:**
- Create: `server/routes/enterprise.js`
- Create: `server/services/enterpriseService.js`

- [ ] **Step 1: 编写企业服务**

```javascript
// server/services/enterpriseService.js
const { getDb } = require('../db');

class EnterpriseService {
  // 企业列表
  getAllEnterprises() {
    const db = getDb();
    return db.all('SELECT * FROM enterprises ORDER BY created_at DESC');
  }

  // 获取企业详情
  getEnterpriseById(id) {
    const db = getDb();
    return db.get('SELECT * FROM enterprises WHERE id = ?', [id]);
  }

  // 创建企业
  createEnterprise(data) {
    const db = getDb();
    const { name, industry, scale, meta_config } = data;
    const result = db.run(
      'INSERT INTO enterprises (name, industry, scale, meta_config) VALUES (?, ?, ?, ?)',
      [name, industry, scale, meta_config ? JSON.stringify(meta_config) : null]
    );
    return { id: result.lastInsertRowid, name, industry, scale };
  }

  // 更新企业
  updateEnterprise(id, data) {
    const db = getDb();
    const { name, industry, scale, meta_config } = data;
    db.run(
      'UPDATE enterprises SET name = ?, industry = ?, scale = ?, meta_config = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
      [name, industry, scale, meta_config ? JSON.stringify(meta_config) : null, id]
    );
    return this.getEnterpriseById(id);
  }

  // 删除企业
  deleteEnterprise(id) {
    const db = getDb();
    db.run('DELETE FROM enterprises WHERE id = ?', [id]);
    return { success: true };
  }
}

module.exports = new EnterpriseService();
```

- [ ] **Step 2: 编写企业路由**

```javascript
// server/routes/enterprise.js
const express = require('express');
const router = express.Router();
const enterpriseService = require('../services/enterpriseService');

// 响应格式化
function apiResponse(res, data, message = '操作成功', statusCode = 200) {
  res.status(statusCode).json({ success: true, data, message });
}

function apiError(res, error, statusCode = 400) {
  res.status(statusCode).json({ success: false, error: String(error) });
}

// 企业 CRUD
router.get('/enterprises', (req, res) => {
  try {
    const enterprises = enterpriseService.getAllEnterprises();
    apiResponse(res, enterprises);
  } catch (e) {
    apiError(res, e);
  }
});

router.get('/enterprises/:id', (req, res) => {
  try {
    const enterprise = enterpriseService.getEnterpriseById(req.params.id);
    if (!enterprise) {
      return apiError(res, '企业不存在', 404);
    }
    // 解析 meta_config JSON 字符串
    if (enterprise.meta_config && typeof enterprise.meta_config === 'string') {
      enterprise.meta_config = JSON.parse(enterprise.meta_config);
    }
    apiResponse(res, enterprise);
  } catch (e) {
    apiError(res, e);
  }
});

router.post('/enterprises', (req, res) => {
  try {
    const { name, industry, scale, meta_config } = req.body;
    if (!name) {
      return apiError(res, '企业名称不能为空', 400);
    }
    const enterprise = enterpriseService.createEnterprise({ name, industry, scale, meta_config });
    apiResponse(res, enterprise, '创建成功', 201);
  } catch (e) {
    apiError(res, e);
  }
});

router.put('/enterprises/:id', (req, res) => {
  try {
    const { name, industry, scale, meta_config } = req.body;
    const enterprise = enterpriseService.updateEnterprise(req.params.id, { name, industry, scale, meta_config });
    apiResponse(res, enterprise, '更新成功');
  } catch (e) {
    apiError(res, e);
  }
});

router.delete('/enterprises/:id', (req, res) => {
  try {
    enterpriseService.deleteEnterprise(req.params.id);
    apiResponse(res, null, '删除成功');
  } catch (e) {
    apiError(res, e);
  }
});

module.exports = router;
```

- [ ] **Step 3: 测试企业 API**

Run: `curl http://localhost:3000/api/enterprises`
Expected: `{"success":true,"data":[],"message":"操作成功"}`

- [ ] **Step 4: 测试创建企业**

Run: `curl -X POST http://localhost:3000/api/enterprises -H "Content-Type: application/json" -d '{"name":"测试企业","industry":"造纸","scale":"small"}'`
Expected: `{"success":true,"data":{"id":1,"name":"测试企业",...},"message":"创建成功"}`

- [ ] **Step 5: Commit**

```bash
git add server/routes/enterprise.js server/services/enterpriseService.js
git commit -m "feat: add enterprise CRUD routes and service"
```

---

## Task 6: 业务数据 CRUD 路由（订单、库存、账款）

**Files:**
- Modify: `server/routes/enterprise.js`
- Modify: `server/services/enterpriseService.js`

- [ ] **Step 1: 在 enterpriseService 中添加订单方法**

在 `enterpriseService.js` 添加：

```javascript
  // 订单 CRUD
  getOrders(enterpriseId) {
    const db = getDb();
    return db.all('SELECT * FROM orders WHERE enterprise_id = ? ORDER BY created_at DESC', [enterpriseId]);
  }

  createOrder(enterpriseId, data) {
    const db = getDb();
    const { order_no, customer_name, product_name, quantity, price, status, delivery_date } = data;
    const result = db.run(
      'INSERT INTO orders (enterprise_id, order_no, customer_name, product_name, quantity, price, status, delivery_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
      [enterpriseId, order_no, customer_name, product_name, quantity || 0, price || 0, status || 'pending', delivery_date]
    );
    return { id: result.lastInsertRowid, enterprise_id: enterpriseId, order_no, customer_name, product_name, quantity, price, status, delivery_date };
  }

  updateOrder(enterpriseId, orderId, data) {
    const db = getDb();
    const { order_no, customer_name, product_name, quantity, price, status, delivery_date } = data;
    db.run(
      'UPDATE orders SET order_no = ?, customer_name = ?, product_name = ?, quantity = ?, price = ?, status = ?, delivery_date = ? WHERE id = ? AND enterprise_id = ?',
      [order_no, customer_name, product_name, quantity, price, status, delivery_date, orderId, enterpriseId]
    );
    return db.get('SELECT * FROM orders WHERE id = ?', [orderId]);
  }

  deleteOrder(enterpriseId, orderId) {
    const db = getDb();
    db.run('DELETE FROM orders WHERE id = ? AND enterprise_id = ?', [orderId, enterpriseId]);
    return { success: true };
  }
```

- [ ] **Step 2: 在 enterpriseService 中添加库存和账款方法**

继续在 `enterpriseService.js` 添加：

```javascript
  // 库存 CRUD
  getInventory(enterpriseId) {
    const db = getDb();
    return db.all('SELECT * FROM inventory WHERE enterprise_id = ? ORDER BY updated_at DESC', [enterpriseId]);
  }

  createInventoryItem(enterpriseId, data) {
    const db = getDb();
    const { item_name, category, quantity, unit, min_stock } = data;
    const result = db.run(
      'INSERT INTO inventory (enterprise_id, item_name, category, quantity, unit, min_stock) VALUES (?, ?, ?, ?, ?, ?)',
      [enterpriseId, item_name, category, quantity || 0, unit, min_stock || 0]
    );
    return { id: result.lastInsertRowid, enterprise_id: enterpriseId, item_name, category, quantity, unit, min_stock };
  }

  updateInventoryItem(enterpriseId, itemId, data) {
    const db = getDb();
    const { item_name, category, quantity, unit, min_stock } = data;
    db.run(
      'UPDATE inventory SET item_name = ?, category = ?, quantity = ?, unit = ?, min_stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND enterprise_id = ?',
      [item_name, category, quantity, unit, min_stock, itemId, enterpriseId]
    );
    return db.get('SELECT * FROM inventory WHERE id = ?', [itemId]);
  }

  deleteInventoryItem(enterpriseId, itemId) {
    const db = getDb();
    db.run('DELETE FROM inventory WHERE id = ? AND enterprise_id = ?', [itemId, enterpriseId]);
    return { success: true };
  }

  // 账款 CRUD
  getAccounts(enterpriseId) {
    const db = getDb();
    return db.all('SELECT * FROM accounts WHERE enterprise_id = ? ORDER BY created_at DESC', [enterpriseId]);
  }

  createAccount(enterpriseId, data) {
    const db = getDb();
    const { type, customer_name, amount, due_date, status } = data;
    const result = db.run(
      'INSERT INTO accounts (enterprise_id, type, customer_name, amount, due_date, status) VALUES (?, ?, ?, ?, ?, ?)',
      [enterpriseId, type, customer_name, amount || 0, due_date, status || 'unpaid']
    );
    return { id: result.lastInsertRowid, enterprise_id: enterpriseId, type, customer_name, amount, due_date, status };
  }

  updateAccount(enterpriseId, accountId, data) {
    const db = getDb();
    const { type, customer_name, amount, due_date, status } = data;
    db.run(
      'UPDATE accounts SET type = ?, customer_name = ?, amount = ?, due_date = ?, status = ? WHERE id = ? AND enterprise_id = ?',
      [type, customer_name, amount, due_date, status, accountId, enterpriseId]
    );
    return db.get('SELECT * FROM accounts WHERE id = ?', [accountId]);
  }

  deleteAccount(enterpriseId, accountId) {
    const db = getDb();
    db.run('DELETE FROM accounts WHERE id = ? AND enterprise_id = ?', [accountId, enterpriseId]);
    return { success: true };
  }
```

- [ ] **Step 3: 在路由文件中添加业务数据路由**

在 `enterprise.js` 路由文件中添加（module.exports 之前）：

```javascript
// 订单路由
router.get('/enterprises/:id/orders', (req, res) => {
  try {
    const orders = enterpriseService.getOrders(req.params.id);
    apiResponse(res, orders);
  } catch (e) {
    apiError(res, e);
  }
});

router.post('/enterprises/:id/orders', (req, res) => {
  try {
    const order = enterpriseService.createOrder(req.params.id, req.body);
    apiResponse(res, order, '订单创建成功', 201);
  } catch (e) {
    apiError(res, e);
  }
});

router.put('/enterprises/:id/orders/:orderId', (req, res) => {
  try {
    const order = enterpriseService.updateOrder(req.params.id, req.params.orderId, req.body);
    apiResponse(res, order, '订单更新成功');
  } catch (e) {
    apiError(res, e);
  }
});

router.delete('/enterprises/:id/orders/:orderId', (req, res) => {
  try {
    enterpriseService.deleteOrder(req.params.id, req.params.orderId);
    apiResponse(res, null, '订单删除成功');
  } catch (e) {
    apiError(res, e);
  }
});

// 库存路由
router.get('/enterprises/:id/inventory', (req, res) => {
  try {
    const items = enterpriseService.getInventory(req.params.id);
    apiResponse(res, items);
  } catch (e) {
    apiError(res, e);
  }
});

router.post('/enterprises/:id/inventory', (req, res) => {
  try {
    const item = enterpriseService.createInventoryItem(req.params.id, req.body);
    apiResponse(res, item, '库存记录创建成功', 201);
  } catch (e) {
    apiError(res, e);
  }
});

router.put('/enterprises/:id/inventory/:itemId', (req, res) => {
  try {
    const item = enterpriseService.updateInventoryItem(req.params.id, req.params.itemId, req.body);
    apiResponse(res, item, '库存记录更新成功');
  } catch (e) {
    apiError(res, e);
  }
});

router.delete('/enterprises/:id/inventory/:itemId', (req, res) => {
  try {
    enterpriseService.deleteInventoryItem(req.params.id, req.params.itemId);
    apiResponse(res, null, '库存记录删除成功');
  } catch (e) {
    apiError(res, e);
  }
});

// 账款路由
router.get('/enterprises/:id/accounts', (req, res) => {
  try {
    const accounts = enterpriseService.getAccounts(req.params.id);
    apiResponse(res, accounts);
  } catch (e) {
    apiError(res, e);
  }
});

router.post('/enterprises/:id/accounts', (req, res) => {
  try {
    const account = enterpriseService.createAccount(req.params.id, req.body);
    apiResponse(res, account, '账款记录创建成功', 201);
  } catch (e) {
    apiError(res, e);
  }
});

router.put('/enterprises/:id/accounts/:accountId', (req, res) => {
  try {
    const account = enterpriseService.updateAccount(req.params.id, req.params.accountId, req.body);
    apiResponse(res, account, '账款记录更新成功');
  } catch (e) {
    apiError(res, e);
  }
});

router.delete('/enterprises/:id/accounts/:accountId', (req, res) => {
  try {
    enterpriseService.deleteAccount(req.params.id, req.params.accountId);
    apiResponse(res, null, '账款记录删除成功');
  } catch (e) {
    apiError(res, e);
  }
});
```

- [ ] **Step 4: 测试订单 API**

Run: `curl http://localhost:3000/api/enterprises/1/orders`
Expected: `{"success":true,"data":[],"message":"操作成功"}`

Run: `curl -X POST http://localhost:3000/api/enterprises/1/orders -H "Content-Type: application/json" -d '{"order_no":"ORD001","customer_name":"客户A","product_name":"纸箱A","quantity":100,"price":500}'`
Expected: 创建订单成功

- [ ] **Step 5: Commit**

```bash
git add server/routes/enterprise.js server/services/enterpriseService.js
git commit -m "feat: add orders, inventory, and accounts CRUD endpoints"
```

---

## Task 7: 前端 API 调用封装

**Files:**
- Create: `frontend/assets/js/api.js`

- [ ] **Step 1: 编写 API 调用封装**

```javascript
// frontend/assets/js/api.js
const API_BASE = '/api';

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const config = {
    headers: { 'Content-Type': 'application/json' },
    ...options
  };
  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }
  const res = await fetch(url, config);
  const json = await res.json();
  if (!json.success) {
    throw new Error(json.error || '请求失败');
  }
  return json.data;
}

// 企业 API
const enterpriseApi = {
  list: () => request('/enterprises'),
  get: (id) => request(`/enterprises/${id}`),
  create: (data) => request('/enterprises', { method: 'POST', body: data }),
  update: (id, data) => request(`/enterprises/${id}`, { method: 'PUT', body: data }),
  delete: (id) => request(`/enterprises/${id}`, { method: 'DELETE' }),
  getOrders: (id) => request(`/enterprises/${id}/orders`),
  createOrder: (id, data) => request(`/enterprises/${id}/orders`, { method: 'POST', body: data }),
  updateOrder: (id, orderId, data) => request(`/enterprises/${id}/orders/${orderId}`, { method: 'PUT', body: data }),
  deleteOrder: (id, orderId) => request(`/enterprises/${id}/orders/${orderId}`, { method: 'DELETE' }),
  getInventory: (id) => request(`/enterprises/${id}/inventory`),
  createInventory: (id, data) => request(`/enterprises/${id}/inventory`, { method: 'POST', body: data }),
  updateInventory: (id, itemId, data) => request(`/enterprises/${id}/inventory/${itemId}`, { method: 'PUT', body: data }),
  deleteInventory: (id, itemId) => request(`/enterprises/${id}/inventory/${itemId}`, { method: 'DELETE' }),
  getAccounts: (id) => request(`/enterprises/${id}/accounts`),
  createAccount: (id, data) => request(`/enterprises/${id}/accounts`, { method: 'POST', body: data }),
  updateAccount: (id, accountId, data) => request(`/enterprises/${id}/accounts/${accountId}`, { method: 'PUT', body: data }),
  deleteAccount: (id, accountId) => request(`/enterprises/${id}/accounts/${accountId}`, { method: 'DELETE' })
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/assets/js/api.js
git commit -m "feat: add frontend API client"
```

---

## Task 8: 前端统一样式

**Files:**
- Create: `frontend/assets/css/main.css`

- [ ] **Step 1: 编写统一样式**

```css
/* frontend/assets/css/main.css */
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #f5f5f5;
  color: #333;
  line-height: 1.6;
}

.container { max-width: 1200px; margin: 0 auto; padding: 20px; }

/* 卡片 */
.card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.card h2 {
  font-size: 18px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #667eea;
}

/* 按钮 */
.btn {
  display: inline-block;
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
}

.btn-primary { background: #667eea; color: white; }
.btn-primary:hover { background: #5568d3; }
.btn-danger { background: #e74c3c; color: white; }
.btn-danger:hover { background: #c0392b; }
.btn-success { background: #27ae60; color: white; }
.btn-success:hover { background: #219a52; }

/* 表格 */
.table {
  width: 100%;
  border-collapse: collapse;
}

.table th, .table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #666;
  font-size: 13px;
  text-transform: uppercase;
}

.table tr:hover { background: #f8f9fa; }

/* 表单 */
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 6px; font-weight: 500; font-size: 14px; }
.form-group input, .form-group select, .form-group textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}
.form-group input:focus, .form-group select:focus, .form-group textarea:focus {
  outline: none;
  border-color: #667eea;
}

/* 模态框 */
.modal {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal.active { display: flex; }

.modal-content {
  background: white;
  border-radius: 12px;
  padding: 24px;
  width: 90%;
  max-width: 500px;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.modal-header h3 { font-size: 18px; }
.modal-close { cursor: pointer; font-size: 24px; color: #999; }
.modal-close:hover { color: #333; }

/* 状态标签 */
.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}
.badge-success { background: #e8f5e9; color: #27ae60; }
.badge-warning { background: #fff8e1; color: #f39c12; }
.badge-danger { background: #ffebee; color: #e74c3c; }
.badge-default { background: #f5f5f5; color: #666; }

/* 头部导航 */
.header {
  background: white;
  padding: 16px 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  margin-bottom: 24px;
}

.header h1 { font-size: 20px; color: #333; }

/* 网格布局 */
.grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }

/* 统计卡片 */
.stat-card {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  padding: 20px;
  border-radius: 12px;
  text-align: center;
}

.stat-card .number { font-size: 32px; font-weight: bold; }
.stat-card .label { font-size: 14px; opacity: 0.9; }

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #999;
}

.empty-state p { margin-bottom: 16px; }
```

- [ ] **Step 2: Commit**

```bash
git add frontend/assets/css/main.css
git commit -m "feat: add frontend styles"
```

---

## Task 9: 前端仪表板页面

**Files:**
- Create: `frontend/index.html`

- [ ] **Step 1: 编写仪表板页面**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>企业管理后台</title>
  <link rel="stylesheet" href="assets/css/main.css">
</head>
<body>
  <div class="header">
    <div class="container">
      <h1>企业管理系统</h1>
    </div>
  </div>

  <div class="container">
    <!-- 企业列表 -->
    <div class="card">
      <h2>企业管理</h2>
      <div style="margin-bottom: 16px;">
        <button class="btn btn-primary" onclick="showCreateModal()">+ 添加企业</button>
      </div>
      <div id="enterprise-list">
        <div class="empty-state">
          <p>暂无企业数据</p>
          <button class="btn btn-primary" onclick="showCreateModal()">添加第一个企业</button>
        </div>
      </div>
    </div>
  </div>

  <!-- 创建/编辑企业模态框 -->
  <div class="modal" id="enterprise-modal">
    <div class="modal-content">
      <div class="modal-header">
        <h3 id="modal-title">添加企业</h3>
        <span class="modal-close" onclick="closeModal()">&times;</span>
      </div>
      <form id="enterprise-form">
        <input type="hidden" id="enterprise-id">
        <div class="form-group">
          <label>企业名称</label>
          <input type="text" id="enterprise-name" required>
        </div>
        <div class="form-group">
          <label>所属行业</label>
          <input type="text" id="enterprise-industry" placeholder="如：造纸箱">
        </div>
        <div class="form-group">
          <label>企业规模</label>
          <select id="enterprise-scale">
            <option value="unknown">待确认</option>
            <option value="small">小微企业 (&lt;50人)</option>
            <option value="medium">中小型企业 (50-200人)</option>
            <option value="large">大型企业 (&gt;200人)</option>
          </select>
        </div>
        <div style="text-align: right;">
          <button type="button" class="btn" onclick="closeModal()">取消</button>
          <button type="submit" class="btn btn-primary">保存</button>
        </div>
      </form>
    </div>
  </div>

  <!-- 企业详情模态框 -->
  <div class="modal" id="detail-modal">
    <div class="modal-content" style="max-width: 900px;">
      <div class="modal-header">
        <h3 id="detail-title">企业详情</h3>
        <span class="modal-close" onclick="closeDetailModal()">&times;</span>
      </div>
      <div id="detail-content"></div>
    </div>
  </div>

  <script src="assets/js/api.js"></script>
  <script>
    let currentEnterpriseId = null;

    async function loadEnterprises() {
      try {
        const enterprises = await enterpriseApi.list();
        renderEnterpriseList(enterprises);
      } catch (e) {
        console.error('加载企业列表失败:', e);
      }
    }

    function renderEnterpriseList(enterprises) {
      const container = document.getElementById('enterprise-list');
      if (!enterprises || enterprises.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>暂无企业数据</p><button class="btn btn-primary" onclick="showCreateModal()">添加第一个企业</button></div>';
        return;
      }
      container.innerHTML = `
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>企业名称</th>
              <th>行业</th>
              <th>规模</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            ${enterprises.map(e => `
              <tr>
                <td>${e.id}</td>
                <td><a href="#" onclick="showEnterpriseDetail(${e.id})" style="color:#667eea;text-decoration:none;">${e.name}</a></td>
                <td>${e.industry || '-'}</td>
                <td>${getScaleText(e.scale)}</td>
                <td>${e.created_at ? new Date(e.created_at).toLocaleDateString('zh-CN') : '-'}</td>
                <td>
                  <button class="btn btn-primary" style="padding:4px 8px;font-size:12px;" onclick="showEditModal(${e.id}, '${e.name}', '${e.industry || ''}', '${e.scale || ''}')">编辑</button>
                  <button class="btn btn-danger" style="padding:4px 8px;font-size:12px;" onclick="deleteEnterprise(${e.id})">删除</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    }

    function getScaleText(scale) {
      const map = { small: '小微', medium: '中小', large: '大型', unknown: '待确认' };
      return map[scale] || scale || '待确认';
    }

    function showCreateModal() {
      document.getElementById('modal-title').textContent = '添加企业';
      document.getElementById('enterprise-id').value = '';
      document.getElementById('enterprise-form').reset();
      document.getElementById('enterprise-modal').classList.add('active');
    }

    function showEditModal(id, name, industry, scale) {
      document.getElementById('modal-title').textContent = '编辑企业';
      document.getElementById('enterprise-id').value = id;
      document.getElementById('enterprise-name').value = name;
      document.getElementById('enterprise-industry').value = industry;
      document.getElementById('enterprise-scale').value = scale || 'unknown';
      document.getElementById('enterprise-modal').classList.add('active');
    }

    function closeModal() {
      document.getElementById('enterprise-modal').classList.remove('active');
    }

    async function handleEnterpriseSubmit(e) {
      e.preventDefault();
      const id = document.getElementById('enterprise-id').value;
      const data = {
        name: document.getElementById('enterprise-name').value,
        industry: document.getElementById('enterprise-industry').value,
        scale: document.getElementById('enterprise-scale').value
      };
      try {
        if (id) {
          await enterpriseApi.update(parseInt(id), data);
        } else {
          await enterpriseApi.create(data);
        }
        closeModal();
        loadEnterprises();
      } catch (e) {
        alert('保存失败: ' + e.message);
      }
    }

    async function deleteEnterprise(id) {
      if (!confirm('确定要删除该企业吗？')) return;
      try {
        await enterpriseApi.delete(id);
        loadEnterprises();
      } catch (e) {
        alert('删除失败: ' + e.message);
      }
    }

    async function showEnterpriseDetail(id) {
      currentEnterpriseId = id;
      try {
        const enterprise = await enterpriseApi.get(id);
        document.getElementById('detail-title').textContent = enterprise.name;
        const metaConfig = enterprise.meta_config || {};
        const modules = metaConfig.modules || [];
        renderDetailContent(enterprise, modules);
        document.getElementById('detail-modal').classList.add('active');
      } catch (e) {
        alert('加载企业详情失败: ' + e.message);
      }
    }

    function renderDetailContent(enterprise, modules) {
      const container = document.getElementById('detail-content');
      const scaleText = getScaleText(enterprise.scale);
      container.innerHTML = `
        <div style="margin-bottom:20px;">
          <p><strong>行业:</strong> ${enterprise.industry || '-'}</p>
          <p><strong>规模:</strong> ${scaleText}</p>
          <p><strong>创建时间:</strong> ${enterprise.created_at ? new Date(enterprise.created_at).toLocaleString('zh-CN') : '-'}</p>
        </div>
        <h4 style="margin-bottom:12px;">管理模块</h4>
        <div class="grid-2" style="margin-bottom:20px;">
          ${modules.length === 0 ? '<p style="color:#999;">暂无配置模块</p>' : modules.map(m => `
            <div class="card" style="padding:16px;">
              <h5 style="margin-bottom:8px;">${m.name} <span class="badge badge-${m.priority === 1 ? 'danger' : m.priority === 2 ? 'warning' : 'default'}">${m.priority === 1 ? '高优' : m.priority === 2 ? '中优' : '低优'}</span></h5>
              <p style="font-size:13px;color:#666;">${m.metadata?.recommendation || '建议部署'}</p>
              <div style="margin-top:8px;">
                ${(m.features || []).map(f => `<span class="badge badge-default" style="margin-right:4px;">${f.name || f}</span>`).join('')}
              </div>
              <div style="margin-top:12px;">
                <button class="btn btn-primary" style="padding:6px 12px;font-size:12px;" onclick="openModulePage('${m.id}', ${enterprise.id})">进入管理</button>
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

    function openModulePage(moduleId, enterpriseId) {
      const pageMap = {
        order_management: 'pages/orders.html',
        inventory_management: 'pages/inventory.html',
        accounts_receivable: 'pages/accounts.html'
      };
      const page = pageMap[moduleId];
      if (page) {
        window.location.href = `${page}?enterpriseId=${enterpriseId}`;
      } else {
        alert('该模块页面暂未实现');
      }
    }

    function closeDetailModal() {
      document.getElementById('detail-modal').classList.remove('active');
    }

    document.getElementById('enterprise-form').addEventListener('submit', handleEnterpriseSubmit);

    // 页面加载时获取企业列表
    loadEnterprises();
  </script>
</body>
</html>
```

- [ ] **Step 2: 测试仪表板**

Run: `node server/index.js`（如果未运行）
浏览器访问：`http://localhost:3000`

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add enterprise dashboard page"
```

---

## Task 10: 订单管理页面

**Files:**
- Create: `frontend/pages/orders.html`

- [ ] **Step 1: 编写订单管理页面**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>订单管理</title>
  <link rel="stylesheet" href="../assets/css/main.css">
</head>
<body>
  <div class="header">
    <div class="container" style="display:flex;justify-content:space-between;align-items:center;">
      <h1>订单管理</h1>
      <a href="../index.html" class="btn" style="text-decoration:none;">返回首页</a>
    </div>
  </div>

  <div class="container">
    <div class="card">
      <h2>订单列表</h2>
      <div style="margin-bottom:16px;">
        <button class="btn btn-primary" onclick="showCreateModal()">+ 新建订单</button>
      </div>
      <div id="orders-container">
        <div class="empty-state"><p>暂无订单数据</p></div>
      </div>
    </div>
  </div>

  <!-- 模态框 -->
  <div class="modal" id="order-modal">
    <div class="modal-content">
      <div class="modal-header">
        <h3 id="modal-title">新建订单</h3>
        <span class="modal-close" onclick="closeModal()">&times;</span>
      </div>
      <form id="order-form">
        <input type="hidden" id="order-id">
        <div class="form-group">
          <label>订单号</label>
          <input type="text" id="order-no" required>
        </div>
        <div class="form-group">
          <label>客户名称</label>
          <input type="text" id="customer-name">
        </div>
        <div class="form-group">
          <label>产品名称</label>
          <input type="text" id="product-name">
        </div>
        <div class="grid-2">
          <div class="form-group">
            <label>数量</label>
            <input type="number" id="quantity" value="0">
          </div>
          <div class="form-group">
            <label>单价</label>
            <input type="number" id="price" value="0" step="0.01">
          </div>
        </div>
        <div class="form-group">
          <label>交货日期</label>
          <input type="date" id="delivery-date">
        </div>
        <div class="form-group">
          <label>状态</label>
          <select id="order-status">
            <option value="pending">待处理</option>
            <option value="processing">生产中</option>
            <option value="completed">已完成</option>
            <option value="cancelled">已取消</option>
          </select>
        </div>
        <div style="text-align:right;">
          <button type="button" class="btn" onclick="closeModal()">取消</button>
          <button type="submit" class="btn btn-primary">保存</button>
        </div>
      </form>
    </div>
  </div>

  <script src="../assets/js/api.js"></script>
  <script>
    let enterpriseId = null;

    function getQueryParam(name) {
      const params = new URLSearchParams(window.location.search);
      return params.get(name);
    }

    async function loadOrders() {
      if (!enterpriseId) return;
      try {
        const orders = await enterpriseApi.getOrders(enterpriseId);
        renderOrders(orders);
      } catch (e) {
        console.error('加载订单失败:', e);
      }
    }

    function renderOrders(orders) {
      const container = document.getElementById('orders-container');
      if (!orders || orders.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>暂无订单数据</p><button class="btn btn-primary" onclick="showCreateModal()">新建订单</button></div>';
        return;
      }
      container.innerHTML = `
        <table class="table">
          <thead>
            <tr>
              <th>订单号</th>
              <th>客户</th>
              <th>产品</th>
              <th>数量</th>
              <th>单价</th>
              <th>金额</th>
              <th>状态</th>
              <th>交货日期</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            ${orders.map(o => `
              <tr>
                <td>${o.order_no}</td>
                <td>${o.customer_name || '-'}</td>
                <td>${o.product_name || '-'}</td>
                <td>${o.quantity}</td>
                <td>¥${parseFloat(o.price || 0).toFixed(2)}</td>
                <td>¥${(o.quantity * o.price).toFixed(2)}</td>
                <td><span class="badge ${getStatusClass(o.status)}">${getStatusText(o.status)}</span></td>
                <td>${o.delivery_date || '-'}</td>
                <td>
                  <button class="btn btn-primary" style="padding:4px 8px;font-size:12px;" onclick='showEditModal(${JSON.stringify(o)})'>编辑</button>
                  <button class="btn btn-danger" style="padding:4px 8px;font-size:12px;" onclick="deleteOrder(${o.id})">删除</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    }

    function getStatusClass(status) {
      const map = { pending: 'badge-warning', processing: 'badge-default', completed: 'badge-success', cancelled: 'badge-danger' };
      return map[status] || 'badge-default';
    }

    function getStatusText(status) {
      const map = { pending: '待处理', processing: '生产中', completed: '已完成', cancelled: '已取消' };
      return map[status] || status;
    }

    function showCreateModal() {
      document.getElementById('modal-title').textContent = '新建订单';
      document.getElementById('order-id').value = '';
      document.getElementById('order-form').reset();
      document.getElementById('order-no').value = 'ORD' + Date.now().toString().slice(-6);
      document.getElementById('order-modal').classList.add('active');
    }

    function showEditModal(order) {
      document.getElementById('modal-title').textContent = '编辑订单';
      document.getElementById('order-id').value = order.id;
      document.getElementById('order-no').value = order.order_no;
      document.getElementById('customer-name').value = order.customer_name || '';
      document.getElementById('product-name').value = order.product_name || '';
      document.getElementById('quantity').value = order.quantity || 0;
      document.getElementById('price').value = order.price || 0;
      document.getElementById('delivery-date').value = order.delivery_date || '';
      document.getElementById('order-status').value = order.status || 'pending';
      document.getElementById('order-modal').classList.add('active');
    }

    function closeModal() {
      document.getElementById('order-modal').classList.remove('active');
    }

    async function handleSubmit(e) {
      e.preventDefault();
      const id = document.getElementById('order-id').value;
      const data = {
        order_no: document.getElementById('order-no').value,
        customer_name: document.getElementById('customer-name').value,
        product_name: document.getElementById('product-name').value,
        quantity: parseInt(document.getElementById('quantity').value) || 0,
        price: parseFloat(document.getElementById('price').value) || 0,
        delivery_date: document.getElementById('delivery-date').value,
        status: document.getElementById('order-status').value
      };
      try {
        if (id) {
          await enterpriseApi.updateOrder(enterpriseId, parseInt(id), data);
        } else {
          await enterpriseApi.createOrder(enterpriseId, data);
        }
        closeModal();
        loadOrders();
      } catch (e) {
        alert('保存失败: ' + e.message);
      }
    }

    async function deleteOrder(id) {
      if (!confirm('确定要删除该订单吗？')) return;
      try {
        await enterpriseApi.deleteOrder(enterpriseId, id);
        loadOrders();
      } catch (e) {
        alert('删除失败: ' + e.message);
      }
    }

    document.getElementById('order-form').addEventListener('submit', handleSubmit);

    enterpriseId = getQueryParam('enterpriseId');
    if (!enterpriseId) {
      document.getElementById('orders-container').innerHTML = '<div class="empty-state"><p>未指定企业ID</p><a href="../index.html" class="btn btn-primary">返回首页</a></div>';
    } else {
      loadOrders();
    }
  </script>
</body>
</html>
```

- [ ] **Step 2: 测试订单页面**

访问：`http://localhost:3000/pages/orders.html?enterpriseId=1`

- [ ] **Step 3: Commit**

```bash
git add frontend/pages/orders.html
git commit -m "feat: add orders management page"
```

---

## Task 11: 库存管理页面

**Files:**
- Create: `frontend/pages/inventory.html`

- [ ] **Step 1: 编写库存管理页面**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>库存管理</title>
  <link rel="stylesheet" href="../assets/css/main.css">
</head>
<body>
  <div class="header">
    <div class="container" style="display:flex;justify-content:space-between;align-items:center;">
      <h1>库存管理</h1>
      <a href="../index.html" class="btn" style="text-decoration:none;">返回首页</a>
    </div>
  </div>

  <div class="container">
    <div class="card">
      <h2>库存列表</h2>
      <div style="margin-bottom:16px;">
        <button class="btn btn-primary" onclick="showCreateModal()">+ 添加库存</button>
      </div>
      <div id="inventory-container">
        <div class="empty-state"><p>暂无库存数据</p></div>
      </div>
    </div>
  </div>

  <div class="modal" id="inventory-modal">
    <div class="modal-content">
      <div class="modal-header">
        <h3 id="modal-title">添加库存</h3>
        <span class="modal-close" onclick="closeModal()">&times;</span>
      </div>
      <form id="inventory-form">
        <input type="hidden" id="item-id">
        <div class="form-group">
          <label>物料名称</label>
          <input type="text" id="item-name" required>
        </div>
        <div class="form-group">
          <label>类别</label>
          <select id="category">
            <option value="raw_material">原材料</option>
            <option value="finished_goods">成品</option>
            <option value="semi_finished">半成品</option>
            <option value="packaging">包装材料</option>
          </select>
        </div>
        <div class="grid-2">
          <div class="form-group">
            <label>数量</label>
            <input type="number" id="quantity" value="0">
          </div>
          <div class="form-group">
            <label>单位</label>
            <input type="text" id="unit" placeholder="如：箱、吨、个">
          </div>
        </div>
        <div class="form-group">
          <label>最低库存预警</label>
          <input type="number" id="min-stock" value="0">
        </div>
        <div style="text-align:right;">
          <button type="button" class="btn" onclick="closeModal()">取消</button>
          <button type="submit" class="btn btn-primary">保存</button>
        </div>
      </form>
    </div>
  </div>

  <script src="../assets/js/api.js"></script>
  <script>
    let enterpriseId = null;

    function getQueryParam(name) {
      return new URLSearchParams(window.location.search).get(name);
    }

    async function loadInventory() {
      if (!enterpriseId) return;
      try {
        const items = await enterpriseApi.getInventory(enterpriseId);
        renderInventory(items);
      } catch (e) {
        console.error('加载库存失败:', e);
      }
    }

    function renderInventory(items) {
      const container = document.getElementById('inventory-container');
      if (!items || items.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>暂无库存数据</p><button class="btn btn-primary" onclick="showCreateModal()">添加库存</button></div>';
        return;
      }
      container.innerHTML = `
        <table class="table">
          <thead>
            <tr>
              <th>物料名称</th>
              <th>类别</th>
              <th>数量</th>
              <th>单位</th>
              <th>最低库存</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            ${items.map(item => `
              <tr>
                <td>${item.item_name}</td>
                <td>${getCategoryText(item.category)}</td>
                <td>${item.quantity}</td>
                <td>${item.unit || '-'}</td>
                <td>${item.min_stock || 0}</td>
                <td><span class="badge ${getStockStatus(item.quantity, item.min_stock)}">${getStockStatusText(item.quantity, item.min_stock)}</span></td>
                <td>
                  <button class="btn btn-primary" style="padding:4px 8px;font-size:12px;" onclick='showEditModal(${JSON.stringify(item)})'>编辑</button>
                  <button class="btn btn-danger" style="padding:4px 8px;font-size:12px;" onclick="deleteItem(${item.id})">删除</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    }

    function getCategoryText(cat) {
      const map = { raw_material: '原材料', finished_goods: '成品', semi_finished: '半成品', packaging: '包装材料' };
      return map[cat] || cat || '-';
    }

    function getStockStatus(qty, min) {
      if (!min || min === 0) return 'badge-default';
      return qty <= min ? 'badge-danger' : 'badge-success';
    }

    function getStockStatusText(qty, min) {
      if (!min || min === 0) return '正常';
      return qty <= min ? '库存不足' : '正常';
    }

    function showCreateModal() {
      document.getElementById('modal-title').textContent = '添加库存';
      document.getElementById('item-id').value = '';
      document.getElementById('inventory-form').reset();
      document.getElementById('inventory-modal').classList.add('active');
    }

    function showEditModal(item) {
      document.getElementById('modal-title').textContent = '编辑库存';
      document.getElementById('item-id').value = item.id;
      document.getElementById('item-name').value = item.item_name;
      document.getElementById('category').value = item.category || 'raw_material';
      document.getElementById('quantity').value = item.quantity || 0;
      document.getElementById('unit').value = item.unit || '';
      document.getElementById('min-stock').value = item.min_stock || 0;
      document.getElementById('inventory-modal').classList.add('active');
    }

    function closeModal() {
      document.getElementById('inventory-modal').classList.remove('active');
    }

    async function handleSubmit(e) {
      e.preventDefault();
      const id = document.getElementById('item-id').value;
      const data = {
        item_name: document.getElementById('item-name').value,
        category: document.getElementById('category').value,
        quantity: parseInt(document.getElementById('quantity').value) || 0,
        unit: document.getElementById('unit').value,
        min_stock: parseInt(document.getElementById('min-stock').value) || 0
      };
      try {
        if (id) {
          await enterpriseApi.updateInventory(enterpriseId, parseInt(id), data);
        } else {
          await enterpriseApi.createInventory(enterpriseId, data);
        }
        closeModal();
        loadInventory();
      } catch (e) {
        alert('保存失败: ' + e.message);
      }
    }

    async function deleteItem(id) {
      if (!confirm('确定要删除该库存记录吗？')) return;
      try {
        await enterpriseApi.deleteInventory(enterpriseId, id);
        loadInventory();
      } catch (e) {
        alert('删除失败: ' + e.message);
      }
    }

    document.getElementById('inventory-form').addEventListener('submit', handleSubmit);

    enterpriseId = getQueryParam('enterpriseId');
    if (!enterpriseId) {
      document.getElementById('inventory-container').innerHTML = '<div class="empty-state"><p>未指定企业ID</p><a href="../index.html" class="btn btn-primary">返回首页</a></div>';
    } else {
      loadInventory();
    }
  </script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/pages/inventory.html
git commit -m "feat: add inventory management page"
```

---

## Task 12: 账款管理页面

**Files:**
- Create: `frontend/pages/accounts.html`

- [ ] **Step 1: 编写账款管理页面**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>账款管理</title>
  <link rel="stylesheet" href="../assets/css/main.css">
</head>
<body>
  <div class="header">
    <div class="container" style="display:flex;justify-content:space-between;align-items:center;">
      <h1>账款管理</h1>
      <a href="../index.html" class="btn" style="text-decoration:none;">返回首页</a>
    </div>
  </div>

  <div class="container">
    <div class="grid-3" style="margin-bottom:20px;">
      <div class="stat-card">
        <div class="number" id="total-receivable">¥0</div>
        <div class="label">应收账款</div>
      </div>
      <div class="stat-card" style="background:linear-gradient(135deg,#e74c3c,#c0392b);">
        <div class="number" id="total-payable">¥0</div>
        <div class="label">应付账款</div>
      </div>
      <div class="stat-card" style="background:linear-gradient(135deg,#f39c12,#e67e22);">
        <div class="number" id="total-overdue">¥0</div>
        <div class="label">逾期账款</div>
      </div>
    </div>

    <div class="card">
      <h2>账款列表</h2>
      <div style="margin-bottom:16px;">
        <button class="btn btn-primary" onclick="showCreateModal()">+ 添加账款</button>
      </div>
      <div id="accounts-container">
        <div class="empty-state"><p>暂无账款数据</p></div>
      </div>
    </div>
  </div>

  <div class="modal" id="account-modal">
    <div class="modal-content">
      <div class="modal-header">
        <h3 id="modal-title">添加账款</h3>
        <span class="modal-close" onclick="closeModal()">&times;</span>
      </div>
      <form id="account-form">
        <input type="hidden" id="account-id">
        <div class="form-group">
          <label>账款类型</label>
          <select id="account-type" required>
            <option value="receivable">应收账款</option>
            <option value="payable">应付账款</option>
          </select>
        </div>
        <div class="form-group">
          <label>客户/供应商名称</label>
          <input type="text" id="customer-name">
        </div>
        <div class="form-group">
          <label>金额</label>
          <input type="number" id="amount" value="0" step="0.01" required>
        </div>
        <div class="form-group">
          <label>到期日期</label>
          <input type="date" id="due-date">
        </div>
        <div class="form-group">
          <label>状态</label>
          <select id="account-status">
            <option value="unpaid">未付款</option>
            <option value="paid">已付款</option>
            <option value="overdue">已逾期</option>
          </select>
        </div>
        <div style="text-align:right;">
          <button type="button" class="btn" onclick="closeModal()">取消</button>
          <button type="submit" class="btn btn-primary">保存</button>
        </div>
      </form>
    </div>
  </div>

  <script src="../assets/js/api.js"></script>
  <script>
    let enterpriseId = null;

    function getQueryParam(name) {
      return new URLSearchParams(window.location.search).get(name);
    }

    async function loadAccounts() {
      if (!enterpriseId) return;
      try {
        const accounts = await enterpriseApi.getAccounts(enterpriseId);
        renderAccounts(accounts);
        updateStats(accounts);
      } catch (e) {
        console.error('加载账款失败:', e);
      }
    }

    function updateStats(accounts) {
      const receivable = accounts.filter(a => a.type === 'receivable').reduce((sum, a) => sum + parseFloat(a.amount || 0), 0);
      const payable = accounts.filter(a => a.type === 'payable').reduce((sum, a) => sum + parseFloat(a.amount || 0), 0);
      const overdue = accounts.filter(a => a.status === 'overdue').reduce((sum, a) => sum + parseFloat(a.amount || 0), 0);
      document.getElementById('total-receivable').textContent = '¥' + receivable.toFixed(2);
      document.getElementById('total-payable').textContent = '¥' + payable.toFixed(2);
      document.getElementById('total-overdue').textContent = '¥' + overdue.toFixed(2);
    }

    function renderAccounts(accounts) {
      const container = document.getElementById('accounts-container');
      if (!accounts || accounts.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>暂无账款数据</p><button class="btn btn-primary" onclick="showCreateModal()">添加账款</button></div>';
        return;
      }
      container.innerHTML = `
        <table class="table">
          <thead>
            <tr>
              <th>类型</th>
              <th>客户/供应商</th>
              <th>金额</th>
              <th>到期日期</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            ${accounts.map(a => `
              <tr>
                <td><span class="badge ${a.type === 'receivable' ? 'badge-success' : 'badge-warning'}">${a.type === 'receivable' ? '应收' : '应付'}</span></td>
                <td>${a.customer_name || '-'}</td>
                <td>¥${parseFloat(a.amount || 0).toFixed(2)}</td>
                <td>${a.due_date || '-'}</td>
                <td><span class="badge ${getStatusClass(a.status)}">${getStatusText(a.status)}</span></td>
                <td>
                  <button class="btn btn-primary" style="padding:4px 8px;font-size:12px;" onclick='showEditModal(${JSON.stringify(a)})'>编辑</button>
                  <button class="btn btn-danger" style="padding:4px 8px;font-size:12px;" onclick="deleteAccount(${a.id})">删除</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    }

    function getStatusClass(status) {
      return { paid: 'badge-success', unpaid: 'badge-warning', overdue: 'badge-danger' }[status] || 'badge-default';
    }

    function getStatusText(status) {
      return { paid: '已付款', unpaid: '未付款', overdue: '已逾期' }[status] || status;
    }

    function showCreateModal() {
      document.getElementById('modal-title').textContent = '添加账款';
      document.getElementById('account-id').value = '';
      document.getElementById('account-form').reset();
      document.getElementById('account-modal').classList.add('active');
    }

    function showEditModal(account) {
      document.getElementById('modal-title').textContent = '编辑账款';
      document.getElementById('account-id').value = account.id;
      document.getElementById('account-type').value = account.type || 'receivable';
      document.getElementById('customer-name').value = account.customer_name || '';
      document.getElementById('amount').value = account.amount || 0;
      document.getElementById('due-date').value = account.due_date || '';
      document.getElementById('account-status').value = account.status || 'unpaid';
      document.getElementById('account-modal').classList.add('active');
    }

    function closeModal() {
      document.getElementById('account-modal').classList.remove('active');
    }

    async function handleSubmit(e) {
      e.preventDefault();
      const id = document.getElementById('account-id').value;
      const data = {
        type: document.getElementById('account-type').value,
        customer_name: document.getElementById('customer-name').value,
        amount: parseFloat(document.getElementById('amount').value) || 0,
        due_date: document.getElementById('due-date').value,
        status: document.getElementById('account-status').value
      };
      try {
        if (id) {
          await enterpriseApi.updateAccount(enterpriseId, parseInt(id), data);
        } else {
          await enterpriseApi.createAccount(enterpriseId, data);
        }
        closeModal();
        loadAccounts();
      } catch (e) {
        alert('保存失败: ' + e.message);
      }
    }

    async function deleteAccount(id) {
      if (!confirm('确定要删除该账款记录吗？')) return;
      try {
        await enterpriseApi.deleteAccount(enterpriseId, id);
        loadAccounts();
      } catch (e) {
        alert('删除失败: ' + e.message);
      }
    }

    document.getElementById('account-form').addEventListener('submit', handleSubmit);

    enterpriseId = getQueryParam('enterpriseId');
    if (!enterpriseId) {
      document.getElementById('accounts-container').innerHTML = '<div class="empty-state"><p>未指定企业ID</p><a href="../index.html" class="btn btn-primary">返回首页</a></div>';
    } else {
      loadAccounts();
    }
  </script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/pages/accounts.html
git commit -m "feat: add accounts management page"
```

---

## Task 13: 导入已有企业数据

**Files:**
- Create: `bin/import-enterprise.js`

- [ ] **Step 1: 编写导入脚本**

```javascript
#!/usr/bin/env node
/**
 * 导入已有企业数据到系统
 * 用法: node bin/import-enterprise.js "企业名称" --meta-config ./output/企业_meta_config.json
 */

const fs = require('fs');
const path = require('path');
const { getDb, closeDb } = require('../server/db');

function importEnterprise(companyName, metaConfigPath) {
  const db = getDb();

  // 读取 meta_config 文件
  let metaConfig = null;
  if (metaConfigPath && fs.existsSync(metaConfigPath)) {
    const content = fs.readFileSync(metaConfigPath, 'utf8');
    metaConfig = JSON.parse(content);
  }

  // 构建企业数据
  const enterprise = {
    name: metaConfig?.company?.name || companyName,
    industry: metaConfig?.company?.industry || '',
    scale: metaConfig?.company?.scale || 'unknown',
    meta_config: metaConfig
  };

  // 插入数据库
  const result = db.run(
    'INSERT INTO enterprises (name, industry, scale, meta_config) VALUES (?, ?, ?, ?)',
    [enterprise.name, enterprise.industry, enterprise.scale, JSON.stringify(enterprise.meta_config)]
  );

  console.log(`企业导入成功！`);
  console.log(`企业ID: ${result.lastInsertRowid}`);
  console.log(`企业名称: ${enterprise.name}`);
  console.log(`行业: ${enterprise.industry}`);
  console.log(`规模: ${enterprise.scale}`);

  closeDb();
  return result.lastInsertRowid;
}

// 命令行解析
const args = process.argv.slice(2);
if (args.length < 1) {
  console.log('用法: node bin/import-enterprise.js "企业名称" [--meta-config <文件路径>]');
  process.exit(1);
}

const companyName = args[0];
let metaConfigPath = null;

for (let i = 1; i < args.length; i++) {
  if (args[i] === '--meta-config' && args[i + 1]) {
    metaConfigPath = args[i + 1];
    break;
  }
}

importEnterprise(companyName, metaConfigPath);
```

- [ ] **Step 2: 测试导入脚本**

Run: `node bin/import-enterprise.js "东社造纸厂" --meta-config ./output/东社造纸厂_meta_config.json`
Expected: 输出企业导入成功

- [ ] **Step 3: Commit**

```bash
git add bin/import-enterprise.js
git commit -m "feat: add enterprise import script"
```

---

## Task 14: 验收测试

**验证步骤:**

- [ ] **Step 1: 启动服务器**

Run: `node server/index.js`
Expected: 服务器在 http://localhost:3000 启动

- [ ] **Step 2: 初始化数据库（如果未初始化）**

Run: `node server/db/init.js`

- [ ] **Step 3: 导入已有企业数据**

Run: `node bin/import-enterprise.js "东社造纸厂" --meta-config ./output/东社造纸厂_meta_config.json`
Expected: 企业导入成功，企业ID: 1

- [ ] **Step 4: 访问前端**

浏览器打开：`http://localhost:3000`
Expected: 看到企业管理后台，显示东社造纸厂

- [ ] **Step 5: 点击企业查看详情**

Expected: 看到订单管理、库存管理、账款管理模块卡片

- [ ] **Step 6: 测试订单管理**

点击订单管理的"进入管理" → 新建订单 → 填写信息 → 保存
Expected: 订单出现在列表中

- [ ] **Step 7: 测试库存管理**

返回首页 → 进入库存管理 → 添加库存记录
Expected: 库存记录出现在列表中

- [ ] **Step 8: 测试账款管理**

返回首页 → 进入账款管理 → 添加应收账款 → 查看统计卡片更新
Expected: 统计卡片正确显示合计金额

- [ ] **Step 9: 验证数据持久化**

重启服务器 `node server/index.js` → 刷新页面
Expected: 数据仍然存在

---

## 自检清单

1. **Spec 覆盖检查：** 逐条对照设计文档，所有功能都有对应实现
2. **占位符检查：** 无 TBD/TODO/未完成部分
3. **类型一致性检查：** 所有 API 方法签名与前端调用一致
4. **空状态处理：** 所有列表页面都有空状态展示
5. **表单验证：** 必填字段有验证
6. **错误处理：** API 调用有 try-catch 和用户友好的错误提示

**Plan 覆盖完毕，输出最终确认。**
