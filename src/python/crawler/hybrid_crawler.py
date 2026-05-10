"""并行爬虫模块 - 使用 ThreadPoolExecutor 并行采集页面内容"""
import os
import time
import re
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from storage.document import Document


class HybridCrawler:
    """混合爬虫 - 并行采集页面内容"""

    def __init__(
        self,
        max_workers: int = 10,
        timeout: int = 30,
        max_retries: int = 3,
        min_content_length: int = 100,
    ):
        self.max_workers = max_workers
        self.timeout = timeout
        self.max_retries = max_retries
        self.min_content_length = min_content_length
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def crawl(self, urls: List[str], priority: int = 0) -> List[Document]:
        """
        并行爬取多个 URL

        Args:
            urls: URL 列表
            priority: 优先级（影响线程分配）

        Returns:
            List[Document]: 文档列表
        """
        documents = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._fetch_document, url): url
                for url in urls
            }
            for future in as_completed(futures):
                url = futures[future]
                try:
                    doc = future.result()
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    print(f"Crawl failed for {url}: {e}")
        return documents

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _fetch_with_retry(self, url: str) -> Optional[str]:
        """带重试的页面获取"""
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def _fetch_document(self, url: str) -> Optional[Document]:
        """获取单个页面并构建 Document"""
        try:
            html = self._fetch_with_retry(url)
            if not html:
                return None

            soup = BeautifulSoup(html, 'html.parser')

            # 提取标题
            title = self._extract_title(soup)

            # 提取正文内容
            content = self._extract_content(soup)

            # 检测乱码和导航内容
            is_garbled = Document.is_garbled_text(title) or Document.is_garbled_text(content)
            is_navigation = Document.is_navigation_content(content)

            # 构建 Document
            doc = Document(
                url=url,
                title=title,
                content=content,
                domain="",
                fetched_at=datetime.now(),
                content_length=len(content),
                is_valid=not is_garbled and not is_navigation,
                is_garbled=is_garbled,
                is_navigation=is_navigation,
            )
            return doc

        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """提取页面标题"""
        # 尝试多种标题标签
        title_tag = (
            soup.find('h1') or
            soup.find('title') or
            soup.find('meta', property='og:title') or
            soup.find('meta', attrs={'name': 'title'})
        )
        if title_tag:
            return title_tag.get_text(strip=True)
        return ""

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """提取页面正文内容"""
        # 移除脚本和样式
        for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
            tag.decompose()

        # 尝试提取 main 或 article 内容区域
        main_content = (
            soup.find('main') or
            soup.find('article') or
            soup.find('div', class_=re.compile(r'content|article|post|body', re.I)) or
            soup.find('div', id=re.compile(r'content|article|post|body', re.I))
        )

        if main_content:
            text = main_content.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)

        # 清理空白
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)

    def crawl_with_metadata(
        self, urls: List[str], titles: List[str] = None, scores: List[float] = None
    ) -> List[Document]:
        """
        带元数据的爬取（用于合并 Tavily 结果）

        Args:
            urls: URL 列表
            titles: 标题列表（可选）
            scores: 原始评分列表（可选）

        Returns:
            List[Document]: 文档列表
        """
        documents = self.crawl(urls)

        # 如果提供了标题，用原始标题覆盖
        if titles:
            for doc, title in zip(documents, titles):
                if title:
                    doc.title = title

        # 如果提供了分数，存储在额外字段（不覆盖 Document 属性）
        if scores:
            for doc, score in zip(documents, scores):
                doc.raw_score = score  # 临时存储原始分数

        return documents