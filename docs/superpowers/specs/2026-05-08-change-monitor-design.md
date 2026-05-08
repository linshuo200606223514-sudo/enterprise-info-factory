# 客户变更监控与预警设计文档

> **状态：** 已批准

## 1. 目标

为AI企业信息工厂添加客户变更监控元能力，当监控的企业发生工商变更（法人变更、司法风险新增）时，自动重新计算信用评分并通过企业微信机器人推送预警，帮助东社造纸厂及时掌握客户风险动态，从"被动查询"升级为"主动预警"。

## 2. 架构概览

```
api/services/
├── changeMonitor.js    # 新增：变更监控服务
├── creditScorer.js     # 现有：信用评分
└── wechatNotifier.js   # 新增：企业微信通知

server/jobs/
└── monitor.js          # 新增：定时任务入口

server/routes/
└── alerts.js          # 新增：预警记录查询 API
```

## 3. 功能流程

```
定时任务触发 (每日 08:00)
    │
    ▼
读取所有已监控客户列表
    │
    ▼
遍历每个客户：
    │
    ▼
采集最新工商数据
    │
    ▼
与本地缓存数据比对
    │
    ├── 无变更 → 跳过
    │
    └── 有变更
            │
            ▼
        记录变更明细到 alerts 表
            │
            ▼
        重新计算信用评分
            │
            ▼
        推送企业微信预警
            │
            ▼
        更新本地缓存数据
```

## 4. 监控规则

### 4.1 监控变更类型

| 变更类型 | 检测方法 | 预警级别 |
|----------|----------|----------|
| 法人变更 | 对比 `legal_representative` 字段 | 高 |
| 司法风险新增 | 对比 `judicial_risks` 数组 | 高 |
| 失信/老赖新增 | `judicial_risks` 包含失信人类型 | 紧急 |

### 4.2 变更检测算法

```javascript
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
      changes.push({
        type: '司法风险新增',
        field: 'judicial_risks',
        old_value: null,
        new_value: riskType
      });
    }
  }

  return changes;
}
```

## 5. 企业微信通知

### 5.1 Webhook 配置

企业微信机器人通过 Webhook URL 推送消息，需要在 `.env` 中配置：

```
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=XXX
```

### 5.2 消息格式

```json
{
  "msgtype": "markdown",
  "markdown": {
    "content": "🚨 **客户风险预警**\n\n**公司**：XXX纸业有限公司\n**变更类型**：法人变更\n**原法人**：张三\n**新法人**：李四\n**影响**：信用评分从 82 → 75，等级 A → B\n**时间**：2026-05-09 08:00\n\n👉 [查看详情](http://app.example.com)"
  }
}
```

### 5.3 预警级别

| 级别 | 标识 | 触发条件 |
|------|------|----------|
| 紧急 | 🔴 | 失信/老赖新增 |
| 高 | 🟠 | 法人变更、司法风险新增（非失信） |

## 6. API 设计

### 6.1 查询预警历史

```
GET /api/alerts
```

**查询参数：**
- `page` (可选, 默认1) - 页码
- `limit` (可选, 默认20) - 每页数量

**响应：**
```json
{
  "success": true,
  "data": {
    "alerts": [
      {
        "id": 1,
        "company_name": "XXX纸业有限公司",
        "change_type": "法人变更",
        "old_value": "张三",
        "new_value": "李四",
        "old_score": 82,
        "new_score": 75,
        "old_grade": "A",
        "new_grade": "B",
        "alert_sent": 1,
        "created_at": "2026-05-09T08:00:00Z"
      }
    ],
    "total": 50,
    "page": 1,
    "limit": 20
  }
}
```

### 6.2 查询指定客户的预警历史

```
GET /api/alerts/:companyName
```

**响应：**
```json
{
  "success": true,
  "data": {
    "alerts": [...],
    "total": 5
  }
}
```

### 6.3 测试预警推送

```
POST /api/alerts/test
```

**响应：**
```json
{
  "success": true,
  "message": "测试预警推送成功"
}
```

## 7. 数据存储

### 7.1 alerts 表结构

```sql
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
```

### 7.2 company_cache 表（用于存储最新数据）

```sql
CREATE TABLE IF NOT EXISTS company_cache (
  company_name TEXT PRIMARY KEY,
  data TEXT NOT NULL,
  credit_score INTEGER,
  credit_grade TEXT,
  updated_at TEXT DEFAULT (datetime('now'))
);
```

## 8. 定时任务

### 8.1 执行时间

每日早上 08:00 执行。

### 8.2 任务入口

```javascript
// server/jobs/monitor.js
const { runDailyMonitor } = require('../api/services/changeMonitor');

// 使用 node-cron 或类似库
cron.schedule('0 8 * * *', async () => {
  console.log('开始执行每日客户监控...');
  await runDailyMonitor();
  console.log('每日客户监控完成');
});
```

## 9. 错误处理

| 场景 | 处理方式 |
|------|----------|
| 企业微信推送失败 | 记录到日志，alerts 表 alert_sent 标记为 0，人工补发 |
| 某个客户采集失败 | 跳过该客户，继续处理其他客户 |
| 所有客户采集失败 | 发送监控异常通知 |
| 变更检测异常 | 记录错误日志，不阻塞其他客户 |

## 10. 依赖

新增依赖：
```json
{
  "dependencies": {
    "node-cron": "^3.0.0"
  }
}
```

## 11. 验收标准

- [ ] 变更监控服务能正确检测法人变更和司法风险新增
- [ ] 企业微信机器人能成功推送预警消息
- [ ] 预警记录正确存储到 alerts 表
- [ ] API 能查询预警历史
- [ ] 定时任务每日 08:00 正确执行
- [ ] 某个客户失败不影响其他客户
- [ ] 与现有信用评分服务正确集成

## 12. 后续扩展

- [ ] 增加更多变更类型监控（资本变更、地址变更等）
- [ ] 支持自定义监控频率
- [ ] 支持按客户重要性设置不同预警级别
- [ ] 预警消息增加直接跳转小程序的链接
