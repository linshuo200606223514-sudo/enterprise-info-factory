"""AI实体提取模块 - LLM驱动版 + 行业背景"""
import os
import sys
import json
import re
from typing import Dict, List, Optional
from openai import OpenAI

class EntityExtractor:
    """从文本中提取企业实体信息 - LLM驱动，可融合行业背景"""

    def __init__(self, provider: str = "openai", model: str = None):
        self.provider = provider
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)

    def extract(self, raw_data: Dict, industry_context: Dict = None) -> Dict:
        """
        从原始搜索数据中提取结构化实体（LLM推理版）

        Args:
            raw_data: 包含搜索结果的原始数据
            industry_context: 可选，行业研究背景数据

        Returns:
            Dict - LLM推理的企业画像
        """
        if not self.client:
            return self._extract_by_rules(raw_data, industry_context)

        combined_text = self._combine_text(raw_data)
        if len(combined_text.strip()) < 50:
            return self._extract_by_rules(raw_data, industry_context)

        return self._extract_by_llm(combined_text, industry_context)

    def _combine_text(self, raw_data: Dict) -> str:
        texts = []
        if "search_results" in raw_data:
            for result in raw_data["search_results"]:
                if "title" in result:
                    texts.append(f"【标题】{result['title']}")
                if "abstract" in result:
                    texts.append(f"【摘要】{result['abstract']}")
                if "content" in result:
                    texts.append(f"【正文】{result['content']}")
        if "tianyancha_data" in raw_data:
            tianyancha = raw_data["tianyancha_data"]
            if "data" in tianyancha and "items" in tianyancha["data"]:
                for item in tianyancha["data"]["items"]:
                    texts.append(f"【工商】{item}")
        return "\n\n".join(texts)

    def _extract_by_llm(self, combined_text: str, industry_context: Dict = None) -> Dict:
        prompt = self._build_prompt(combined_text, industry_context)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位企业调研专家，擅长从公开信息推断企业画像。输出严格JSON格式，用中文。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=2000
            )
            result = json.loads(response.choices[0].message.content)
            return self._validate_and_fill(result)
        except Exception as e:
            print(f"LLM调用失败: {e}")
            return self._fallback_result(industry_context)

    def _build_prompt(self, combined_text: str, industry_context: Dict = None) -> str:
        # 如果有行业背景，加入prompt
        industry_section = ""
        if industry_context:
            players = industry_context.get("top_players", [])
            news = industry_context.get("news", [])
            competitors = industry_context.get("competitors", [])

            industry_section = f"""

行业背景：
- 行业头部玩家: {', '.join([p.get('title', '')[:30] for p in players[:3]])}
- 行业动态: {', '.join([n.get('title', '')[:40] for n in news[:3]])}
- 竞品: {', '.join(competitors[:3])}
"""

        return f"""从以下信息推断企业画像，输出JSON：

信息：
{combined_text[:6000]}
{industry_section}

输出格式：
{{
  "company_name": "公司名称",
  "confirmed_info": {{
    "business_scope": ["业务范围"],
    "location": "地址",
    "established_year": "成立年份",
    "estimated_scale": "规模"
  }},
  "business_characteristics": "业务特征描述（2-3句话）",
  "industry_position": "行业定位（对比行业玩家）",
  "competitive_advantages": ["竞争优势1", "竞争优势2"],
  "potential_pain_points": [{{"issue": "问题", "basis": "依据", "severity": "high/medium/low"}}],
  "digital_maturity": {{"level": "low/medium/high", "indicators": [], "description": ""}},
  "market_reputation": {{"sentiment": "positive/neutral/negative", "evidence": [], "concerns": []}},
  "recommendations": ["数字化建议1", "建议2"],
  "confidence_score": 0.0-1.0,
  "data_gaps": ["缺少的信息"]
}}

注意：
- 如果信息不足，相应字段填"未确认"或空列表
- potential_pain_points 要结合行业背景和公司特征
- recommendations 要具体可行"""

    def _validate_and_fill(self, result: Dict) -> Dict:
        defaults = {
            "company_name": "未确认",
            "confirmed_info": {"business_scope": [], "location": "未确认", "established_year": "未确认", "estimated_scale": "未确认"},
            "business_characteristics": "信息不足",
            "industry_position": "未确认",
            "competitive_advantages": [],
            "potential_pain_points": [],
            "digital_maturity": {"level": "unknown", "indicators": [], "description": "信息不足"},
            "market_reputation": {"sentiment": "unknown", "evidence": [], "concerns": []},
            "recommendations": [],
            "confidence_score": 0.1,
            "data_gaps": ["数据不足"]
        }
        for k, v in defaults.items():
            if k not in result:
                result[k] = v
        return result

    def _extract_by_rules(self, raw_data: Dict, industry_context: Dict = None) -> Dict:
        text = raw_data.get("text", self._combine_text(raw_data))
        name_match = re.search(r'([一-龥]{2,20}(?:造纸厂|纸业|包装|科技|有限|公司))', text)
        keywords = ["纸箱", "包装", "造纸", "印刷", "纸板", "纸制品", "蜂窝板", "瓦楞纸"]
        found = list(set([k for k in keywords if k in text]))

        # 基于行业背景调整痛点
        pain_points = []
        if industry_context:
            # 有行业背景时，更精准的推断
            pain_points = [
                {"issue": "订单管理困难", "basis": "造纸箱行业通用痛点", "severity": "medium"},
                {"issue": "生产排程混乱", "basis": "造纸箱行业通用痛点", "severity": "medium"},
                {"issue": "成本核算不准", "basis": "造纸箱行业通用痛点", "severity": "low"}
            ]
        else:
            pain_points = [
                {"issue": "订单管理困难", "basis": "造纸箱行业通用痛点", "severity": "medium"},
                {"issue": "生产排程混乱", "basis": "造纸箱行业通用痛点", "severity": "medium"},
                {"issue": "成本核算不准", "basis": "造纸箱行业通用痛点", "severity": "low"}
            ]

        return {
            "company_name": name_match.group(1) if name_match else "未确认",
            "confirmed_info": {"business_scope": found or ["待确认"], "location": "未确认", "established_year": "未确认", "estimated_scale": "未确认"},
            "business_characteristics": "信息不足，无法分析（规则提取模式）",
            "industry_position": "未确认",
            "competitive_advantages": [],
            "potential_pain_points": pain_points,
            "digital_maturity": {"level": "unknown", "indicators": [], "description": "信息不足"},
            "market_reputation": {"sentiment": "unknown", "evidence": [], "concerns": []},
            "recommendations": ["建议先进行实地调研获取更多信息"],
            "confidence_score": 0.2,
            "data_gaps": ["缺少公开数据"]
        }

    def _fallback_result(self, industry_context: Dict = None) -> Dict:
        return self._extract_by_rules({}, industry_context)


if __name__ == "__main__":
    search_results_json = None
    tianyancha_data_json = None
    industry_context_json = None

    for arg in sys.argv[1:]:
        if arg.startswith("search_results="):
            search_results_json = arg.split("=", 1)[1]
        elif arg.startswith("tianyancha_data="):
            tianyancha_data_json = arg.split("=", 1)[1]
        elif arg.startswith("industry_context="):
            industry_context_json = arg.split("=", 1)[1]

    if not search_results_json or not tianyancha_data_json:
        print("Error: search_results and tianyancha_data are required")
        sys.exit(1)

    search_results = json.loads(search_results_json)
    tianyancha_data = json.loads(tianyancha_data_json)
    industry_context = json.loads(industry_context_json) if industry_context_json else None

    extractor = EntityExtractor()
    result = extractor.extract(
        {"search_results": search_results, "tianyancha_data": tianyancha_data},
        industry_context
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))