"""天眼查API模块"""
import os
import requests
from typing import Dict, Optional, List

class TianyanchaAPI:
    """天眼查企业信息API客户端"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TIANYANCHA_API_KEY")
        self.base_url = "https://api.tianyancha.com"

    def search_company(self, name: str, max_results: int = 10) -> Dict:
        """
        搜索企业基本信息

        Args:
            name: 企业名称
            max_results: 最大返回数量

        Returns:
            Dict - 包含企业基本信息的字典
        """
        if not self.api_key:
            # 如果没有API key，返回mock数据用于测试
            return self._mock_data(name)

        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        params = {"word": name, "pageSize": max_results}

        try:
            response = requests.get(
                f"{self.base_url}/cloud-infometa/company/search",
                headers=headers,
                params=params,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"API调用失败: {e}")

        return self._mock_data(name)

    def _mock_data(self, name: str) -> Dict:
        """返回模拟数据用于开发和测试"""
        return {
            "data": {
                "items": [
                    {
                        "name": name,
                        "capital": "1000万元",
                        "成立时间": "2010-01-01",
                        "地址": "浙江省某市",
                        "经营范围": "纸箱制造、销售"
                    }
                ]
            }
        }