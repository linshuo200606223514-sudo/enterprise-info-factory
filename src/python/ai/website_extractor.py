"""网站内容LLM提取模块 - 使用GPT解析官网内容"""
import os
import json
import re
from typing import Dict, List
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
        优先使用LLM，fallback到关键词匹配
        """
        # 先尝试LLM提取
        try:
            from ai.llm_extractor import extract_with_llm
            llm_result = extract_with_llm(content, url)
            # 如果LLM提取到了有效信息（不是"未提及"），使用LLM结果
            if llm_result.get('core_functions', '未提及') != '未提及':
                return llm_result
        except Exception as e:
            pass  # LLM失败，继续使用fallback

        # LLM失败或不完整，使用fallback
        return self._fallback_extract(content)

    def _is_navigation_content(self, content: str) -> bool:
        """检测是否是导航/标签类内容（非正文）"""
        if not content:
            return False
        # URL链接模式 = 导航内容
        if '](https://' in content:
            return True
        # 完全由导航元素组成（iframe + 短词列表）= 导航内容
        if content.count('iframe') > 2 and len(content) < 200:
            return True
        # 计算导航词和实际内容词的比例
        nav_words = ['导航', '菜单', '栏目', '标签', '分类', 'iframe', 'src=']
        content_words = ['功能', '产品', '解决方案', '系统', '管理', '平台', '服务', '企业', '应用', '数据']
        nav_count = sum(content.count(w) for w in nav_words)
        content_count = sum(content.count(w) for w in content_words)
        # 如果导航词远多于内容词，认为是导航
        if nav_count > 2 and content_count < 2:
            return True
        # 导航比例过高
        if len(content) > 0 and nav_count / len(content) > 0.1:
            return True
        return False

    def _fallback_extract(self, content: str) -> Dict:
        """增强的基于关键词的备用提取"""
        if not content or len(content) < 100:
            return {
                "core_functions": "内容不足",
                "pricing": "未提及",
                "target_users": "未提及",
                "highlights": "未提及",
                "use_cases": "未提及"
            }

        result = {"core_functions": "未提及", "pricing": "未提及",
                  "target_users": "未提及", "highlights": "未提及", "use_cases": "未提及"}

        # 提取功能描述 - 尝试多个关键词和位置
        result['core_functions'] = self._extract_best_snippet(content,
            ['功能', '产品介绍', '解决方案', '核心优势', '系统功能', '主要功能', '产品功能',
             '模块', '能力', '服务', '系统', '平台', '库存', '订单', '财务', '采购', '销售',
             '生产', '质量管理', '报表', '数据', '移动', '云端', '智能', '自动化'],
            window_before=50, window_after=300, max_length=280)

        # 提取定价信息 - 包含数字+单位的定价模式
        result['pricing'] = self._extract_pricing_snippet(content)

        # 提取目标用户
        result['target_users'] = self._extract_best_snippet(content,
            ['目标用户', '适用', '面向', '适合', '客户', '人群', '场景', '受众', '行业',
             '企业', '公司', '工厂', '店铺', '门店', '餐厅', '酒店', '超市', '仓库'],
            window_before=10, window_after=250, max_length=200)

        # 提取亮点/优势
        result['highlights'] = self._extract_best_snippet(content,
            ['亮点', '优势', '特色', '特点', '核心竞争', '差异化'],
            window_before=10, window_after=250, max_length=200)

        return result

    def _extract_best_snippet(self, content: str, keywords: List[str],
                               window_before: int = 0, window_after: int = 200,
                               max_length: int = 200) -> str:
        """从关键词附近提取最佳片段"""
        best_snippet = "未提及"
        best_score = 0

        for keyword in keywords:
            idx = content.find(keyword)
            if idx < 0:
                continue

            # 提取周围上下文
            start = max(0, idx - window_before)
            end = min(len(content), idx + window_after)
            snippet = content[start:end]
            snippet = ' '.join(snippet.split())  # 规范化空白

            # 跳过导航内容
            if self._is_navigation_content(snippet):
                continue

            # 评分：内容越长且有关键词密度越高越好
            if len(snippet) >= 20:
                score = len(snippet) / (abs(idx - start) + 1)  # 关键词离开始越近越好
                if score > best_score:
                    best_score = score
                    best_snippet = snippet[:max_length] + "..." if len(snippet) > max_length else snippet

        return best_snippet

    def _extract_pricing_snippet(self, content: str) -> str:
        """专门提取定价相关片段"""
        # 优先查找明确的定价模式：数字+元
        patterns = [
            (r'[\d,]+\s*元/[年月]', '元/月或元/年'),
            (r'[\d,]+\s*元', '元'),
            (r'套餐[^\n，,]{10,50}', '套餐'),
            (r'定价[^\n，,]{10,80}', '定价'),
            (r'价格[^\n，,]{10,80}', '价格'),
        ]

        for pattern, _ in patterns:
            matches = list(re.finditer(pattern, content))
            for m in matches:
                start = max(0, m.start() - 20)
                end = min(len(content), m.end() + 100)
                snippet = content[start:end]
                snippet = ' '.join(snippet.split())

                if self._is_navigation_content(snippet):
                    continue

                # 进一步检查是否包含URL
                if '](https://' in snippet or 'href=' in snippet:
                    continue

                return snippet[:180] + "..." if len(snippet) > 180 else snippet

        return "未提及"


def extract_website_content(content: str, url: str = "") -> Dict:
    """便捷函数：从网站内容提取结构化信息"""
    extractor = WebsiteContentExtractor()
    return extractor.extract(content, url)