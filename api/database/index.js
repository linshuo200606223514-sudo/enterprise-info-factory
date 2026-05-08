/**
 * 数据库模块
 * 封装 better-sqlite3 操作
 */

const Database = require('better-sqlite3');
const path = require('path');
const fs = require('fs');

// 数据库文件路径
const DB_PATH = process.env.DB_PATH || path.join(__dirname, '../../data/enterprise.db');

// 确保数据目录存在
const dbDir = path.dirname(DB_PATH);
if (!fs.existsSync(dbDir)) {
  fs.mkdirSync(dbDir, { recursive: true });
}

// 初始化数据库连接
let db = null;

function getDb() {
  if (!db) {
    db = new Database(DB_PATH);
    db.pragma('journal_mode = WAL');
    db.pragma('foreign_keys = ON');
    initializeSchema();
  }
  return db;
}

/**
 * 初始化数据库表结构
 */
function initializeSchema() {
  const initSqlPath = path.join(__dirname, 'init.sql');

  if (fs.existsSync(initSqlPath)) {
    const initSql = fs.readFileSync(initSqlPath, 'utf-8');
    db.exec(initSql);
    console.log('[Database] 初始化SQL已执行');
  }

  // 检查 enterprises 表是否存在
  const tables = db.exec("SELECT name FROM sqlite_master WHERE type='table' AND name='enterprises'");
  if (!tables.length || tables[0].values.length === 0) {
    // 创建 enterprises 表（如果不存在）
    db.exec(`
      CREATE TABLE IF NOT EXISTS enterprises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        data TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
      )
    `);
    console.log('[Database] enterprises 表已创建');
  }
}

/**
 * 执行查询并返回结果
 * @param {string} sql - SQL语句
 * @param {Array} params - 参数
 * @returns {Array} 查询结果
 */
function query(sql, params = []) {
  const stmt = getDb().prepare(sql);
  return stmt.all(params);
}

/**
 * 执行写入操作
 * @param {string} sql - SQL语句
 * @param {Array} params - 参数
 * @returns {Object} 写入结果
 */
function run(sql, params = []) {
  const stmt = getDb().prepare(sql);
  return stmt.run(params);
}

/**
 * 关闭数据库连接
 */
function close() {
  if (db) {
    db.close();
    db = null;
    console.log('[Database] 数据库连接已关闭');
  }
}

/**
 * 获取单行数据
 * @param {string} sql - SQL语句
 * @param {Array} params - 参数
 * @returns {Object|null}
 */
function get(sql, params = []) {
  const stmt = getDb().prepare(sql);
  return stmt.get(params);
}

module.exports = {
  getDb,
  query,
  run,
  get,
  close
};