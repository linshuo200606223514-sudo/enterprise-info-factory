require('dotenv').config();
const path = require('path');
const fs = require('fs');
const { ensureDb, getDb, closeDb } = require('./index');

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

CREATE TABLE IF NOT EXISTS company_cache (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company_name TEXT NOT NULL UNIQUE,
  data TEXT,
  credit_score REAL,
  credit_grade TEXT,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company_name TEXT NOT NULL,
  change_type TEXT,
  old_value TEXT,
  new_value TEXT,
  old_score REAL,
  new_score REAL,
  old_grade TEXT,
  new_grade TEXT,
  alert_sent INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  level TEXT DEFAULT '高'
);
`;

async function initDatabase() {
  const db = await ensureDb();

  // 执行建表（sql.js 需要逐条执行）
  const statements = SCHEMA_SQL.split(';').filter(s => s.trim());
  for (const stmt of statements) {
    if (stmt.trim()) {
      db.run(stmt);
    }
  }

  console.log('数据库初始化完成');
  closeDb();
}

initDatabase().catch(err => {
  console.error('初始化失败:', err);
  process.exit(1);
});