"""
混合搜索使用示例

用法:
    python examples/hybrid_search_demo.py
"""
import sys
import os

# 将项目根目录添加到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from datetime import datetime
from storage.document import Document
from indexer.bm25_indexer import BM25Indexer
from indexer.vector_indexer import VectorIndexer
from search.hybrid.hybrid_search import HybridSearcher


def create_demo_documents():
    """创建演示用文档"""
    docs = [
        Document(
            url="https://example.com/erp",
            title="餐饮 ERP 系统 - 头部供应商",
            content="专业的餐饮行业ERP解决方案，帮助企业实现数字化转型，提升运营效率，降低成本。提供采购、库存、财务一体化管理。",
            domain="example.com",
            fetched_at=datetime.now(),
        ),
        Document(
            url="https://example.com/pos",
            title="智能 POS 系统",
            content="新一代智能POS收银系统，支持多种支付方式，会员管理，营销工具。适用于餐饮、零售等场景。简单易用，功能强大。",
            domain="example.com",
            fetched_at=datetime.now(),
        ),
        Document(
            url="https://test.com/saas",
            title="SaaS 电商平台",
            content="一站式SaaS电商解决方案，提供店铺装修、商品管理、订单处理、物流配送等全链路服务。支持多渠道分销。",
            domain="test.com",
            fetched_at=datetime.now(),
        ),
        Document(
            url="https://test.com/crm",
            title="客户关系管理系统",
            content="CRM系统帮助企业管理客户数据，分析客户行为，提升销售转化率。支持自定义字段，数据导出，API集成。",
            domain="test.com",
            fetched_at=datetime.now(),
        ),
        Document(
            url="https://demo.com/oms",
            title="订单管理系统 OMS",
            content="OMS订单管理系统，支持多平台订单聚合，智能分配，自动化处理。提升发货效率，减少人工错误。",
            domain="demo.com",
            fetched_at=datetime.now(),
        ),
    ]
    return docs


def main():
    print("=" * 60)
    print("混合搜索演示 - BM25 + 向量混合检索")
    print("=" * 60)

    # 创建演示文档
    docs = create_demo_documents()
    print(f"\n已加载 {len(docs)} 个演示文档")

    # 构建索引
    print("\n构建 BM25 索引...")
    bm25_indexer = BM25Indexer()
    bm25_indexer.build_index(docs)
    print(f"  BM25 索引构建完成，文档数: {len(bm25_indexer.doc_ids)}")

    print("\n构建向量索引 (m3e-base)...")
    try:
        vector_indexer = VectorIndexer()
        vector_indexer.initialize()
        vector_indexer.build_index(docs)
        print(f"  向量索引构建完成，维度: {vector_indexer.vector_dim}")
        use_vector = True
    except Exception as e:
        print(f"  向量索引构建失败: {e}")
        print("  将仅使用 BM25 搜索")
        vector_indexer = None
        use_vector = False

    # 创建搜索器
    searcher = HybridSearcher()
    searcher.documents = {doc.url: doc for doc in docs}
    searcher.bm25_indexer = bm25_indexer
    searcher.vector_indexer = vector_indexer if use_vector else None

    # 测试搜索
    queries = [
        "餐饮 ERP 系统",
        "电商平台 SaaS",
        "客户管理 CRM",
    ]

    print("\n" + "=" * 60)
    for query in queries:
        print(f"\n搜索查询: {query}")
        print("-" * 40)
        results = searcher.search(query, top_k=3)
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r.title}")
            print(f"     URL: {r.url}")
            print(f"     融合分: {r.fused_score:.3f} (BM25={r.bm25_score:.3f}, Vector={r.vector_score:.3f})")
            print(f"     质量分: {r.quality_score:.3f}")
        print()

    print("=" * 60)
    print("演示完成!")


if __name__ == "__main__":
    main()