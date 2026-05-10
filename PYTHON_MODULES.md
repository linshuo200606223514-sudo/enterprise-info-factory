# 企业信息工厂 - Python 模块

Python 混合检索搜索系统（BM25 + 向量），用于企业信息收集和报告生成。

## 搜索模块结构

```
src/python/
├── storage/               # 文档数据模型和存储
│   ├── document.py        # Document 数据模型 + 乱码/导航检测
│   └── document_store.py  # 文档持久化存储
├── crawler/               # 并行爬虫
│   └── hybrid_crawler.py  # ThreadPoolExecutor 并行采集
├── indexer/               # 索引模块
│   ├── bm25_indexer.py    # BM25 索引 (jieba 分词 + 自定义术语)
│   └── vector_indexer.py  # 向量索引 (m3e-base + Qdrant)
├── search/               # 搜索模块
│   ├── hybrid/
│   │   └── hybrid_search.py  # 混合搜索 (BM25*0.5 + cosine*0.5)
│   └── hybrid_api.py      # 对外 API
└── scoring/               # 评分模块
    └── content_scorer.py   # 四因子评分 (可用率/质量/多样/新鲜)
```

## 安装依赖

```bash
pip install rank-bm25 jieba sentence-transformers qdrant-client tenacity
```

## 使用示例

```python
from search.hybrid_api import HybridSearchAPI

api = HybridSearchAPI()
api.crawl_and_index(["https://example.com"])
results = api.search("餐饮 ERP 头部玩家", top_k=20)

for r in results:
    print(f"{r.title} (score={r.fused_score:.3f})")
```

或者运行演示脚本：

```bash
python src/python/examples/hybrid_search_demo.py
```

## 四因子评分体系

| 指标 | 权重 | 说明 |
|------|------|------|
| 可用率 | 40% | 非乱码、非导航内容 |
| 内容质量 | 30% | 正文长度（>2000字满分） |
| 域名多样性 | 15% | 同域名文档越少越好 |
| 新鲜度 | 15% | 内容发布时间 |

## 技术规格

- **BM25**: `rank-bm25` + `jieba` 分词，支持自定义术语
- **向量**: `moka-ai/m3e-base` (768维)，可选 Qdrant 或内存存储
- **融合**: `fused_score = BM25*0.5 + cosine*0.5`

## 运行测试

```bash
python -m pytest tests/python/test_hybrid_search.py -v
```