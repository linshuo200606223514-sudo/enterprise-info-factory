"""网站内容LLM提取模块 - 使用GPT解析官网内容"""
import os
import json
from typing import Dict, Optional
from openai import OpenAI

class WebsiteContentExtractor:
    """使用LLM从网站内容中提取结构化信息"""

    def __init__(self):
        # 先加载.env文件
        from dotenv import load_dotenv
        load_dotenv()
        load_dotenv(os.path.expanduser("~/.env"))

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
        # 暂时禁用LLM提取，因API key格式不兼容MiniMax
        # TODO: 配置正确的API endpoint后启用
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

    def _is_navigation_content(self, content: str) -> bool:
        """检测是否是导航/标签类内容（非正文）"""
        if not content:
            return False
        # URL链接模式 = 导航内容
        if '](https://' in content:
            return True
        nav_patterns = ['](/', 'tag-', 'article/', 'category/']
        nav_count = sum(content.count(p) for p in nav_patterns)
        if nav_count > 3:
            return True
        if len(content) > 0 and nav_count / len(content) > 0.05:
            return True
        return False

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

        # 尝试找功能相关段落（跳过导航内容）
        for keyword in ['功能', '产品介绍', '解决方案', '核心优势']:
            idx = content.find(keyword)
            if idx >= 0:
                snippet = content[idx:idx+500]
                snippet = ' '.join(snippet.split())[:300]
                # 跳过导航类内容
                if self._is_navigation_content(snippet):
                    continue
                result['core_functions'] = snippet
                break

        # 尝试找定价相关段落（跳过导航内容）
        for keyword in ['价格', '定价', '费用', '元/', '元/年', '套餐']:
            idx = content.find(keyword)
            if idx >= 0:
                snippet = content[idx:idx+300]
                snippet = ' '.join(snippet.split())[:200]
                # 跳过导航类内容
                if self._is_navigation_content(snippet):
                    continue
                result['pricing'] = snippet
                break

        # 尝试找目标用户相关段落
        for keyword in ['目标用户', '适用', '面向', '适合', '客户', '人群', '场景']:
            idx = content.find(keyword)
            if idx >= 0:
                snippet = content[idx:idx+200]
                snippet = ' '.join(snippet.split())[:150]
                if self._is_navigation_content(snippet):
                    continue
                result['target_users'] = snippet
                break

        # 尝试找亮点/优势相关段落
        for keyword in ['亮点', '优势', '特色', '特点', ' 차별화', '核心竞争']:
            idx = content.find(keyword)
            if idx >= 0:
                snippet = content[idx:idx+200]
                snippet = ' '.join(snippet.split())[:150]
                if self._is_navigation_content(snippet):
                    continue
                result['highlights'] = snippet
                break

        return result


def extract_website_content(content: str, url: str = "") -> Dict:
    """便捷函数：从网站内容提取结构化信息"""
    extractor = WebsiteContentExtractor()
    return extractor.extract(content, url)
