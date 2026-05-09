"""网站内容LLM提取模块 - 使用GPT解析官网内容"""
import os
import json
from typing import Dict, Optional
from openai import OpenAI

class WebsiteContentExtractor:
    """使用LLM从网站内容中提取结构化信息"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.client = None
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)

    def extract(self, content: str, url: str = "") -> Dict:
        """
        从网站内容中提取结构化信息

        Returns:
            Dict: {
                "core_functions": str,  # 核心功能描述
                "pricing": str,          # 定价信息
                "target_users": str,    # 目标用户
                "highlights": str,      # 产品亮点
                "use_cases": str       # 典型用例
            }
        """
        if not self.client:
            return self._fallback_extract(content)

        if not content or len(content.strip()) < 100:
            return self._fallback_extract(content)

        prompt = self._build_prompt(content, url)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位专业的B2B产品分析师，擅长从网页内容中提取产品核心信息。输出严格JSON格式，用中文。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=1500
            )
            result = json.loads(response.choices[0].message.content)
            return self._validate_and_fill(result)
        except Exception as e:
            print(f"LLM提取失败: {e}")
            return self._fallback_extract(content)

    def _build_prompt(self, content: str, url: str) -> str:
        url_hint = f"\n来源URL: {url}" if url else ""
        return f"""从以下网站内容中提取产品核心信息：

内容：
{content[:8000]}
{url_hint}

输出格式（JSON）：
{{
  "core_functions": "核心功能描述（2-3句话，突出解决什么问题）",
  "pricing": "定价信息（如有，含价格范围、版本差异）",
  "target_users": "目标用户（1-2句话）",
  "highlights": "产品亮点（突出差异化优势）",
  "use_cases": "典型应用场景（1-2个具体例子）"
}}

如果某项信息不明确，输出"未提及"而非空值。"""

    def _validate_and_fill(self, result: Dict) -> Dict:
        defaults = {
            "core_functions": "未提及",
            "pricing": "未提及",
            "target_users": "未提及",
            "highlights": "未提及",
            "use_cases": "未提及"
        }
        for k, v in defaults.items():
            if k not in result or not result[k]:
                result[k] = v
        return result

    def _fallback_extract(self, content: str) -> Dict:
        """简单基于关键词的备用提取"""
        if not content or len(content) < 100:
            return {
                "core_functions": "内容不足",
                "pricing": "未提及",
                "target_users": "未提及",
                "highlights": "未提及",
                "use_cases": "未提及"
            }

        # 简单关键词提取
        result = {"core_functions": "未提及", "pricing": "未提及",
                  "target_users": "未提及", "highlights": "未提及", "use_cases": "未提及"}

        # 尝试找功能相关段落
        for keyword in ['功能', '产品介绍', '解决方案', '核心优势']:
            idx = content.find(keyword)
            if idx >= 0:
                snippet = content[idx:idx+500]
                snippet = ' '.join(snippet.split())[:300]
                result['core_functions'] = snippet
                break

        # 尝试找定价相关段落
        for keyword in ['价格', '定价', '费用', '元/', '元/年', '套餐']:
            idx = content.find(keyword)
            if idx >= 0:
                snippet = content[idx:idx+300]
                snippet = ' '.join(snippet.split())[:200]
                result['pricing'] = snippet
                break

        return result


def extract_website_content(content: str, url: str = "") -> Dict:
    """便捷函数：从网站内容提取结构化信息"""
    extractor = WebsiteContentExtractor()
    return extractor.extract(content, url)
