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