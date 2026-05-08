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

async function getDb() {
  if (!dbInstance) {
    dbInstance = createDbClient(process.env.DATABASE_URL || 'sqlite:./data/enterprise.db');
    await dbInstance.init();
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