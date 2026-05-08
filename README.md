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

## AI 增强分析（可选）

系统支持使用 Claude AI 进行深度分析，增强痛点识别和推荐模块的准确性。

### 启用 AI 增强

1. 获取 Anthropic API Key：
   - 访问 [Anthropic Console](https://console.anthropic.com/)
   - 创建 API Key

2. 设置环境变量：

```bash
# Windows (CMD)
set ANTHROPIC_API_KEY=sk-ant-xxxxx

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="sk-ant-xxxxx"

# Linux/Mac
export ANTHROPIC_API_KEY=sk-ant-xxxxx
```

3. 重新运行搜索命令，AI 分析结果会自动合并到输出中。

### 说明

- 如果未设置 `ANTHROPIC_API_KEY`，系统会使用纯规则引擎分析
- AI 分析结果会覆盖规则引擎的同类痛点（优先级更高）
- 启用 AI 后，输出中 `painPoints.merged` 的 `source` 字段会显示 `ai_overridden`
