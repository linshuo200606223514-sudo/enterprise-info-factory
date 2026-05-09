"""AI实体提取模块"""
import os
import sys
import json
import re
from typing import Dict, List, Optional

class EntityExtractor:
    """从文本中提取企业实体信息"""

    def __init__(self, provider: str = "openai", model: str = "gpt-4o-mini"):
        self.provider = provider
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY")

    def extract(self, raw_data: Dict) -> Dict:
        """
        从原始搜索数据中提取结构化实体

        Args:
            raw_data: 包含搜索结果的原始数据

        Returns:
            Dict - 结构化的企业信息
        """
        # 合并所有文本来源
        combined_text = self._combine_text(raw_data)

        # 使用规则提取基本信息（V1阶段）
        # V2会使用LLM进行智能提取
        structured = {
            "basic_info": self.extract_basic_info(combined_text),
            "business_scope": self.extract_business_scope(combined_text),
            "organization": self.extract_organization(combined_text),
            "industry_features": self.extract_industry_features(combined_text),
            "potential_pain_points": self.extract_pain_points(combined_text),
        }

        return structured

    def _combine_text(self, raw_data: Dict) -> str:
        """合并多个来源的文本"""
        texts = []
        if "search_results" in raw_data:
            for result in raw_data["search_results"]:
                if "title" in result:
                    texts.append(result["title"])
                if "abstract" in result:
                    texts.append(result["abstract"])
        if "tianyancha_data" in raw_data:
            tianyancha = raw_data["tianyancha_data"]
            if "data" in tianyancha and "items" in tianyancha["data"]:
                for item in tianyancha["data"]["items"]:
                    texts.append(str(item))
        return "\n".join(texts)

    def extract_basic_info(self, text: str) -> Dict:
        """提取基础工商信息"""
        info = {}

        # 提取公司名称（简单规则）
        name_match = re.search(r'([一-龥]{2,20}(?:造纸厂|纸业|包装|科技|有限|公司))', text)
        if name_match:
            info["name"] = name_match.group(1)

        # 提取注册资本
        capital_match = re.search(r'注册资本[：:]\s*([\d.]+(?:亿万)?)', text)
        if capital_match:
            info["capital"] = capital_match.group(1)

        # 提取成立时间
        date_match = re.search(r'成立[于时]?\s*(\d{4})', text)
        if date_match:
            info["established"] = date_match.group(1)

        return info

    def extract_business_scope(self, text: str) -> List[str]:
        """提取业务范围"""
        keywords = ["纸箱", "包装", "造纸", "印刷", "纸板", "纸制品", "蜂窝板"]
        found = [k for k in keywords if k in text]
        return found if found else ["待确认"]

    def extract_organization(self, text: str) -> Dict:
        """提取组织规模信息"""
        scale = {}
        if "人数" in text or "员工" in text or "规模" in text:
            scale["estimated_headcount"] = "待调研"
        return scale

    def extract_industry_features(self, text: str) -> List[str]:
        """提取行业特征"""
        features = []
        if "制造业" in text or "工厂" in text:
            features.append("制造业")
        if "纸箱" in text:
            features.append("纸箱包装行业")
        return features

    def extract_pain_points(self, text: str) -> List[str]:
        """基于行业特征推断可能的痛点"""
        # 造纸箱行业常见痛点
        common_pain_points = [
            "订单管理混乱",
            "生产排程困难",
            "库存管理不准",
            "财务对账麻烦"
        ]
        return common_pain_points

if __name__ == "__main__":
    search_results_json = None
    tianyancha_data_json = None
    for arg in sys.argv[1:]:
        if arg.startswith("search_results="):
            search_results_json = arg.split("=", 1)[1]
        elif arg.startswith("tianyancha_data="):
            tianyancha_data_json = arg.split("=", 1)[1]

    if not search_results_json or not tianyancha_data_json:
        print("Error: search_results and tianyancha_data are required")
        sys.exit(1)

    search_results = json.loads(search_results_json)
    tianyancha_data = json.loads(tianyancha_data_json)

    extractor = EntityExtractor()
    result = extractor.extract({"search_results": search_results, "tianyancha_data": tianyancha_data})
    print(json.dumps(result, ensure_ascii=False))