import requests
from typing import Optional, Dict
from utils.logger import logger
from config.settings import TIMEOUT, DEFAULT_HEADERS


class Downloader:
    """
    同步下载器（基于 requests）
    所有爬虫共用，简单、稳定、抗封
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.logger = logger
        self.logger.info("✅ 同步下载器初始化完成（requests）")

    def get(
            self,
            url: str,
            headers: Optional[Dict[str, str]] = None,
            cookies: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        """
        发送 GET 请求
        """
        try:
            self.logger.info(f"GET -> {url}")

            # 合并自定义请求头
            final_headers = DEFAULT_HEADERS.copy()
            if headers:
                final_headers.update(headers)

            # 发送请求
            resp = self.session.get(
                url=url,
                headers=final_headers,
                cookies=cookies,
                timeout=TIMEOUT,
                allow_redirects=True
            )
            return resp

        except Exception as e:
            self.logger.error(f"请求失败: {str(e)}")
            raise

    def close(self):
        """关闭 session"""
        self.session.close()
        self.logger.info("✅ 下载器已关闭")


# 全局单例（整个程序共用一个下载器）
downloader = Downloader()