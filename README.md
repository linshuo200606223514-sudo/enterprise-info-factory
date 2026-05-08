# 企业信息工厂

企业信息工厂是一个从公开渠道（百度搜索、天眼查等）收集企业信息并生成结构化报告的工具。

## 安装

```bash
npm install
```

## 使用

### 命令行方式

```bash
# 搜索企业信息
node bin/cli.js search "公司名称"

# 指定输出目录
node bin/cli.js search "公司名称" -o ./output

# 指定输出格式
node bin/cli.js search "公司名称" -f json
```

### API 方式

```javascript
const { collectCompanyInfo } = require('./api/index.js');

async function main() {
  const result = await collectCompanyInfo('公司名称', {
    outputDir: './output',
    format: 'json'
  });
  console.log(result);
}

main();
```

## 架构

```
enterprise-info-factory/
├── api/              # API 入口
│   └── index.js      # 主模块，暴露 collectCompanyInfo 函数
├── bin/              # CLI 入口
│   └── cli.js        # 命令行工具
├── scrapers/         # 爬虫模块
│   └── .gitkeep
├── templates/        # 报告模板
│   └── .gitkeep
└── output/           # 输出目录
```

### 核心模块

- **api/index.js**: 主入口，提供 `collectCompanyInfo` 函数
- **bin/cli.js**: 命令行工具，支持 `search` 子命令

## 运行测试

```bash
npm test
```
