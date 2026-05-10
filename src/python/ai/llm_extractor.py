"""LLM内容提取器 - 支持多API回退"""
import os
import json
from typing import Dict
from openai import OpenAI

class LLMExtractor:
    """使用LLM从网站内容中提取结构化信息"""

    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv()
        load_dotenv(os.path.expanduser("~/.env"))

        # 尝试多个API配置
        self.clients = []
        self._init_clients()

    def _init_clients(self):
        """初始化多个API客户端，按优先级排序"""
        # 1. OpenAI (如果设置了OPENAI_API_KEY)
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                client = OpenAI(api_key=openai_key)
                self.clients.append(("openai", client, "gpt-4o-mini"))
            except:
                pass

        # 2. MiniMax (如果设置了MINIMAX_API_KEY)
        minimax_key = os.getenv("MINIMAX_API_KEY")
        minimax_endpoint = os.getenv("MINIMAX_API_BASE", "https://api.minimax.chat/v1")
        if minimax_key:
            try:
                client = OpenAI(api_key=minimax_key, base_url=minimax_endpoint)
                self.clients.append(("minimax", client, "MiniMax-Text-01"))
            except:
                pass

        # 3. DashScope (如果设置了DASHSCOPE_API_KEY)
        dashscope_key = os.getenv("DASHSCOPE_API_KEY")
        dashscope_endpoint = os.getenv("DASHSCOPE_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        if dashscope_key:
            try:
                client = OpenAI(api_key=dashscope_key, base_url=dashscope_endpoint)
                self.clients.append(("dashscope", client, "qwen-plus"))
            except:
                pass

    def extract(self, content: str, url: str = "") -> Dict:
        """从内容中提取结构化信息"""
        if not content or len(content) < 100:
            return self._empty_result()

        # 尝试每个client
        for name, client, model in self.clients:
            try:
                result = self._extract_with_client(client, model, content, url)
                if result and result.get("core_functions", "未提及") != "未提及":
                    return result
            except Exception as e:
                print(f"  [{name}] LLM extraction failed: {e}")
                continue

        # 所有LLM都失败，返回空结果
        return self._empty_result()

    def _extract_with_client(self, client, model: str, content: str, url: str) -> Dict:
        """使用指定client提取内容"""
        prompt = f"""你是一个专业的企业信息分析专家。请从以下网站内容中提取关键信息。

目标URL: {url}

网站内容:
{content[:3000]}

请提取以下信息（如果找不到，填写"未提及"）：
1. 核心功能（产品/服务的主要功能描述，100字以内）
2. 定价信息（价格、收费模式、套餐等，80字以内）
3. 目标用户（产品面向的客户群体，60字以内）
4. 产品亮点（主要优势和特色，60字以内）

输出格式（JSON）：
{{
  "core_functions": "...",
  "pricing": "...",
  "target_users": "...",
  "highlights": "..."
}}
"""
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个专业的企业信息分析专家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )

        result_text = response.choices[0].message.content
        # 尝试解析JSON
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]

        return json.loads(result_text)

    def _empty_result(self) -> Dict:
        return {
            "core_functions": "未提及",
            "pricing": "未提及",
            "target_users": "未提及",
            "highlights": "未提及"
        }


def extract_with_llm(content: str, url: str = "") -> Dict:
    """便捷函数"""
    extractor = LLMExtractor()
    return extractor.extract(content, url)