const path = require('path');
const SqliteAdapter = require('./sqlite');
const MysqlAdapter = require('./mysql');

let dbInstance = null;
let initPromise = null;

function createDbClient(databaseUrl) {
  if (databaseUrl.startsWith('mysql://')) {
    return new MysqlAdapter(databaseUrl);
  }
  // 默认 SQLite
  const dbPath = databaseUrl.replace('sqlite:', '') || './data/enterprise.db';
  const absolutePath = path.isAbsolute(dbPath) ? dbPath : path.join(__dirname, '../../', dbPath);
  return new SqliteAdapter(absolutePath);
}

async function initDb() {
  if (!dbInstance) {
    dbInstance = createDbClient(process.env.DATABASE_URL || 'sqlite:./data/enterprise.db');
    await dbInstance.init();
  }
  return dbInstance;
}

// 同步获取数据库实例（仅在 initDb() 后有效）
function getDb() {
  if (!dbInstance) {
    throw new Error('Database not initialized. Call await initDb() first.');
  }
  return dbInstance;
}

// 异步初始化（启动时调用）
async function ensureDb() {
  if (!initPromise) {
    initPromise = initDb();
  }
  return initPromise;
}

function closeDb() {
  if (dbInstance) {
    dbInstance.close();
    dbInstance = null;
    initPromise = null;
  }
}

module.exports = { getDb, ensureDb, closeDb };
