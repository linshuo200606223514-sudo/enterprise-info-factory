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