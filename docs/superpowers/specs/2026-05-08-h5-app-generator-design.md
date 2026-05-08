# H5 管理应用生成器设计文档

> **状态：** 已批准

## 1. 目标

将 `meta_config.json` 元模型配置转换为真实可运行的 H5 管理页面，支持订单录入、库存查询等真实交互，数据通过 Node.js 后端持久化。

## 2. 架构概览

```
┌─────────────────────────────────────────────────────────┐
│  enterprise-info-factory                                 │
│                                                          │
│  ┌──────────────┐    ┌──────────────┐                  │
│  │ meta_config  │───▶│ App Generator │                  │
│  │  .json       │    └──────┬───────┘                  │
│  └──────────────┘           │                           │
│                              ▼                           │
│  ┌──────────────┐    ┌──────────────┐                  │
│  │   frontend/  │◀──▶│   server/    │                  │
│  │  (H5 页面)   │    │  (Express)   │                  │
│  └──────────────┘    └──────┬───────┘                  │
│                              │                           │
│                     ┌────────▼────────┐                  │
│                     │   db/           │                  │
│                     │  SQLite (dev)   │                  │
│                     │  MySQL (prod)   │                  │
│                     └─────────────────┘                  │
└─────────────────────────────────────────────────────────┘
```

## 3. 目录结构

```
enterprise-info-factory/
├── server/                     # Node.js 后端
│   ├── index.js               # Express 入口，端口 3000
│   ├── routes/
│   │   └── enterprise.js      # 企业 CRUD 路由
│   ├── db/
│   │   ├── index.js           # 数据库工厂，导出 db.getClient()
│   │   ├── sqlite.js          # SQLite 开发适配器
│   │   └── mysql.js           # MySQL 生产适配器
│   ├── middleware/
│   │   └── cors.js            # CORS 中间件
│   └── services/
│       └── enterpriseService.js  # 企业业务逻辑
│
├── frontend/                   # H5 管理页面
│   ├── index.html             # 企业列表/仪表板
│   ├── pages/
│   │   ├── orders.html         # 订单管理（根据 meta_config 动态渲染）
│   │   ├── inventory.html      # 库存管理
│   │   └── cfg.html           # 企业配置管理
│   ├── assets/
│   │   ├── css/
│   │   │   └── main.css       # 统一样式
│   │   └── js/
│   │       ├── api.js         # API 调用封装
│   │       ├── router.js      # 前端路由
│   │       └── generator.js    # 动态页面生成器
│   └── components/
│       └── module-form.html   # 模块表单组件
│
├── generator/                  # 应用生成器
│   └── index.js               # 读取 meta_config，生成页面模板
│
└── docs/                      # 设计文档
```

## 4. 数据库设计

### 4.1 SQLite 开发模式（默认）

数据库文件：`./data/enterprise.db`

```sql
-- 企业表
CREATE TABLE enterprises (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  industry TEXT,
  scale TEXT,
  meta_config_path TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 订单表（订单管理模块）
CREATE TABLE orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  enterprise_id INTEGER NOT NULL,
  order_no TEXT NOT NULL,
  customer_name TEXT,
  product_name TEXT,
  quantity INTEGER DEFAULT 0,
  price DECIMAL(10,2) DEFAULT 0,
  status TEXT DEFAULT 'pending',
  delivery_date DATE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (enterprise_id) REFERENCES enterprises(id)
);

-- 库存表（库存管理模块）
CREATE TABLE inventory (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  enterprise_id INTEGER NOT NULL,
  item_name TEXT NOT NULL,
  category TEXT,
  quantity INTEGER DEFAULT 0,
  unit TEXT,
  min_stock INTEGER DEFAULT 0,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (enterprise_id) REFERENCES enterprises(id)
);

-- 账款表（账款管理模块）
CREATE TABLE accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  enterprise_id INTEGER NOT NULL,
  type TEXT NOT NULL,  -- 'receivable' | 'payable'
  customer_name TEXT,
  amount DECIMAL(12,2) DEFAULT 0,
  due_date DATE,
  status TEXT DEFAULT 'unpaid',  -- 'paid' | 'unpaid' | 'overdue'
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (enterprise_id) REFERENCES enterprises(id)
);
```

### 4.2 MySQL 生产模式

通过 `DATABASE_URL` 环境变量切换：

```bash
DATABASE_URL=mysql://user:pass@localhost:3306/enterprise_factory
```

表结构与 SQLite 一致，SQLite 仅作开发/演示用途。

## 5. API 设计

### 5.1 企业接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/enterprises | 获取企业列表 |
| GET | /api/enterprises/:id | 获取企业详情（含 meta_config） |
| POST | /api/enterprises | 创建企业（关联 meta_config） |
| PUT | /api/enterprises/:id | 更新企业信息 |
| DELETE | /api/enterprises/:id | 删除企业 |

### 5.2 业务数据接口（按模块动态暴露）

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/enterprises/:id/orders | 订单列表 |
| POST | /api/enterprises/:id/orders | 创建订单 |
| PUT | /api/enterprises/:id/orders/:orderId | 更新订单 |
| GET | /api/enterprises/:id/inventory | 库存列表 |
| POST | /api/enterprises/:id/inventory | 创建库存记录 |
| PUT | /api/enterprises/:id/inventory/:itemId | 更新库存 |
| GET | /api/enterprises/:id/accounts | 账款列表 |

### 5.3 响应格式

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

错误响应：

```json
{
  "success": false,
  "error": "错误描述",
  "code": "ENTERPRISE_NOT_FOUND"
}
```

## 6. 前端动态生成机制

### 6.1 generator.js 工作流程

```javascript
// 1. 从 meta_config 读取模块配置
const metaConfig = await fetch('/api/enterprises/1').then(r => r.json());
const modules = metaConfig.data.modules; // [{id: 'order_management', name: '订单管理', features: [...]}]

// 2. 根据模块动态渲染导航和页面
modules.forEach(module => {
  // 生成侧边栏导航项
  renderNavItem(module);
  // 动态注入页面
  generatePage(module);
});
```

### 6.2 页面结构约定

每个模块页面使用统一的 DOM 结构：

```html
<template id="module-template">
  <div class="module-page" data-module="{module_id}">
    <header class="page-header">
      <h2>{module_name}</h2>
    </header>
    <div class="data-table">
      <!-- 动态表格 -->
    </div>
    <div class="data-form modal">
      <!-- 动态表单 -->
    </div>
  </div>
</template>
```

## 7. 启动流程

### 7.1 开发模式（SQLite）

```bash
cd enterprise-info-factory

# 初始化数据库
node server/db/init.js

# 启动后端
node server/index.js

# 新开终端：启动前端（静态文件服务）
npx serve frontend -l 3001
```

访问：`http://localhost:3001`

### 7.2 生产模式（MySQL）

```bash
DATABASE_URL=mysql://user:pass@localhost:3306/enterprise_factory node server/index.js
```

### 7.3 从现有企业数据导入

```bash
# 将已有的 meta_config 导入系统
node bin/import-enterprise.js "东社造纸厂" --meta-config ./output/东社造纸厂_meta_config.json
```

## 8. 配置管理

环境变量：

| 变量 | 默认值 | 描述 |
|------|--------|------|
| PORT | 3000 | 服务器端口 |
| DATABASE_URL | sqlite:./data/enterprise.db | 数据库连接字符串 |
| NODE_ENV | development | development \| production |
| CORS_ORIGIN | http://localhost:3001 | 允许的跨域来源 |

## 9. 扩展机制

### 9.1 添加新模块

只需在 `meta_config.json` 中定义新模块，前端和后端自动支持：

```json
{
  "modules": [
    {
      "id": "quality_control",
      "name": "质量管理",
      "priority": 2,
      "features": [
        {"name": "质检记录", "status": "recommended"},
        {"name": "不合格品处理", "status": "recommended"}
      ]
    }
  ]
}
```

系统自动：
- 后端创建 `quality_records` 表
- 前端生成质量管理页面和导航

### 9.2 数据库适配器

新增数据库只需实现 `db/adapters/xxx.js`：

```javascript
class XxxAdapter {
  async query(sql, params) { ... }
  async run(sql, params) { ... }
  async getOne(sql, params) { ... }
  async close() { ... }
}
```

## 10. 依赖

```json
{
  "dependencies": {
    "express": "^4.18.2",
    "better-sqlite3": "^9.4.0",
    "mysql2": "^3.6.0",
    "cors": "^2.8.5",
    "dotenv": "^16.3.1"
  }
}
```

## 11. 验收标准

- [ ] 后端能启动，SQLite 数据库能初始化
- [ ] 企业 CRUD API 正常工作
- [ ] 前端能显示企业列表
- [ ] 点击企业能展示该企业的 meta_config 对应模块
- [ ] 订单/库存/账款模块能进行增删改查
- [ ] 数据能持久化到数据库
- [ ] 切换 MySQL 后端后数据一致
