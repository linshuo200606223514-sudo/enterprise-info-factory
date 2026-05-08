const initSqlJs = require('sql.js');
const path = require('path');
const fs = require('fs');

class SqliteAdapter {
  constructor(dbPath) {
    this.dbPath = dbPath;
    this.db = null;
  }

  async init() {
    const SQL = await initSqlJs();
    if (fs.existsSync(this.dbPath)) {
      const buffer = fs.readFileSync(this.dbPath);
      this.db = new SQL.Database(buffer);
    } else {
      this.db = new SQL.Database();
    }
  }

  run(sql, params = []) {
    this.db.run(sql, params);
    this._save();
  }

  exec(sql, params = []) {
    let result;
    if (params.length > 0) {
      const stmt = this.db.prepare(sql);
      stmt.bind(params);
      const columns = stmt.getColumnNames();
      const values = [];
      while (stmt.step()) {
        values.push(stmt.get());
      }
      stmt.free();
      result = [{ columns, values }];
    } else {
      result = this.db.exec(sql);
    }
    this._save();
    return result;
  }

  get(sql, params = []) {
    const stmt = this.db.prepare(sql);
    stmt.bind(params);
    if (stmt.step()) {
      const row = stmt.getAsObject();
      stmt.free();
      return row;
    }
    stmt.free();
    return null;
  }

  all(sql, params = []) {
    const results = [];
    const stmt = this.db.prepare(sql);
    stmt.bind(params);
    while (stmt.step()) {
      results.push(stmt.getAsObject());
    }
    stmt.free();
    return results;
  }

  _save() {
    const data = this.db.export();
    const buffer = Buffer.from(data);
    const dir = path.dirname(this.dbPath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(this.dbPath, buffer);
  }

  close() {
    if (this.db) {
      this._save();
      this.db.close();
    }
  }
}

module.exports = SqliteAdapter;