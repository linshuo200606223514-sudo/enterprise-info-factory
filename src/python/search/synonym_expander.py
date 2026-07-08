"""同义词扩展模块"""
from typing import List, Set, Dict


# 核心业务同义词表
BUSINESS_SYNONYMS: Dict[str, List[str]] = {
    "CRM": ["客户关系管理", "客户管理", "CRM系统", "客户管理系统", "Customer Relationship Management"],
    "ERP": ["企业资源计划", "ERP系统", "企业管理软件", "企业管理系统", "Enterprise Resource Planning"],
    "SaaS": ["软件即服务", "在线软件", "云端软件", "SaaS平台", "Software as a Service"],
    "POS": ["收银系统", "收银软件", "收银机", "POS系统", "收银管理系统"],
    "OMS": ["订单管理系统", "订单系统", "订单管理", "Order Management System"],
    "SCM": ["供应链管理", "供应链系统", "Supply Chain Management"],
    "WMS": ["仓库管理系统", "仓储管理", "WMS系统"],
    "MES": ["生产执行系统", "制造执行系统", "MES系统"],

    # 业务场景
    "数字化转型": ["数字化", "数转", "数字化升级", "企业数字化", "digital transformation"],
    "新零售": ["智慧零售", "零售数字化", "全渠道零售", "omni-channel"],
    "电商": ["电子商务", "网上商城", "网络购物", "e-commerce"],
    "餐饮": ["餐饮行业", "餐饮业", "饮食行业"],
    "医疗": ["医疗行业", "医疗健康", "医疗服务"],
    "教育": ["教育培训", "在线教育", "教育行业", "edtech"],
    "金融": ["金融服务", "金融行业", " fintech"],

    # 技术术语
    "人工智能": ["AI", "人工智能技术", "机器智能"],
    "大数据": ["大数据分析", "数据挖掘", "big data"],
    "云计算": ["云服务", "云平台", "cloud computing"],
    "物联网": ["IoT", "物联网技术", "万物互联"],
    "区块链": ["blockchain", "分布式账本", "链上技术"],
}

# 通用同义词
COMMON_SYNONYMS: Dict[str, List[str]] = {
    "系统": ["软件", "平台", "解决方案", "工具"],
    "管理": ["管控", "治理", "管理平台"],
    "解决方案": ["方案", "解决", "解决方案", "全套"],
    "领先": ["第一", "头部", "顶级", "一流"],
    "专业": ["专注", "资深", "专家级"],
    "企业": ["公司", "商业", "商务"],
    "服务": ["服务", "业务", "支持"],
}


class SynonymExpander:
    """同义词扩展器"""

    def __init__(self, custom_synonyms: Dict[str, List[str]] = None):
        self.synonym_dict = {}
        # 合并：默认同义词 + 自定义同义词
        for d in [BUSINESS_SYNONYMS, COMMON_SYNONYMS, custom_synonyms or {}]:
            for key, values in d.items():
                if key not in self.synonym_dict:
                    self.synonym_dict[key] = []
                self.synonym_dict[key].extend(values)
                self.synonym_dict[key] = list(set(self.synonym_dict[key]))

        # 构建反向索引：value -> key
        self.reverse_dict: Dict[str, str] = {}
        for key, values in self.synonym_dict.items():
            for v in values:
                self.reverse_dict[v.lower()] = key
                self.reverse_dict[v] = key

    def expand_query(self, query: str) -> List[str]:
        """
        扩展查询词

        Args:
            query: 原始查询

        Returns:
            扩展后的查询列表（包含原始词和同义词）
        """
        if not query:
            return [query]

        # 分词
        tokens = list(jieba.cut(query))
        expanded = set()
        expanded.add(query)  # 保留原始查询

        for token in tokens:
            token_lower = token.lower()

            # 查找同义词
            if token in self.synonym_dict:
                expanded.update(self.synonym_dict[token])
            if token_lower in self.synonym_dict:
                expanded.update(self.synonym_dict[token_lower])
            if token in self.reverse_dict:
                key = self.reverse_dict[token]
                expanded.add(key)
                expanded.update(self.synonym_dict.get(key, []))

        # 清理空字符串
        expanded = {t.strip() for t in expanded if t.strip()}
        return sorted(list(expanded), key=len, reverse=True)  # 按长度降序（更具体的词排前面）

    def expand_document_terms(self, text: str) -> List[str]:
        """
        扩展文档中的术语（用于索引时统一表示）

        Args:
            text: 原始文本

        Returns:
            扩展后的词列表
        """
        tokens = list(jieba.cut(text))
        expanded = []
        for token in tokens:
            token_lower = token.lower()
            if token in self.reverse_dict:
                expanded.append(self.reverse_dict[token])  # 归一化到主词
            else:
                expanded.append(token)
        return expanded


# 懒加载 jieba（避免循环导入）
import jieba


# 全局实例
_global_expander = None


def get_expander() -> SynonymExpander:
    global _global_expander
    if _global_expander is None:
        _global_expander = SynonymExpander()
    return _global_expander


def expand_query(query: str) -> List[str]:
    """便捷函数：扩展查询词"""
    return get_expander().expand_query(query)