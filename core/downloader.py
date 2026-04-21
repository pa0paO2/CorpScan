import json

import requests
import time
import random
from typing import Optional, Dict
from utils.logger import logger
from config.settings import TIMEOUT, DEFAULT_HEADERS, REQUEST_DELAY_MIN, REQUEST_DELAY_MAX, ENABLE_REQUEST_DELAY


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

    def _delay(self):
        """请求前延迟（反爬策略）"""
        if ENABLE_REQUEST_DELAY:
            delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
            self.logger.debug(f"请求延迟 {delay:.2f} 秒")
            time.sleep(delay)

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
            self._delay()
            self.logger.info(f"GET -> {url}")

            # 合并自定义请求头（优先使用传入的headers）
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

    def post(
            self,
            url: str,
            json_data: Optional[Dict] = None,
            headers: Optional[Dict[str, str]] = None,
            cookies: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        """
        发送 POST 请求（JSON格式）
        """
        try:
            self._delay()
            self.logger.info(f"POST -> {url}")

            # 合并自定义请求头（优先使用传入的headers）
            final_headers = DEFAULT_HEADERS.copy()
            if headers:
                final_headers.update(headers)

            # 设置 Content-Type 为 JSON
            final_headers["Content-Type"] = "application/json;charset=UTF-8"

            # 发送请求
            resp = self.session.post(
                url=url,
                data=json.dumps(json_data, ensure_ascii=False).encode('utf-8') if json_data else None,
                headers=final_headers,
                cookies=cookies,
                timeout=TIMEOUT,
                allow_redirects=True
            )
            return resp

        except Exception as e:
            self.logger.error(f"请求失败: {str(e)}")
            raise


# 全局单例（整个程序共用一个下载器）
downloader = Downloader()