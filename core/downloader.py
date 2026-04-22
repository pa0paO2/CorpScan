"""
网络下载器（带重试机制）

特性：
    - 指数退避重试
    - 自动处理超时、连接错误、5xx错误
    - 限流保护（429 Too Many Requests）
"""

import json
import time
import random
from typing import Optional, Dict, Callable
from functools import wraps

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.logger import logger
from config.settings import (
    TIMEOUT, DEFAULT_HEADERS,
    REQUEST_DELAY_MIN, REQUEST_DELAY_MAX, ENABLE_REQUEST_DELAY,
    MAX_RETRIES, RETRY_BACKOFF_BASE, RETRY_STATUS_CODES
)


class RetryableError(Exception):
    """可重试的错误基类"""
    pass


class NonRetryableError(Exception):
    """不可重试的错误（如 404, 403 等）"""
    pass


def retry_with_backoff(max_retries: int = MAX_RETRIES, backoff_base: float = RETRY_BACKOFF_BASE):
    """
    指数退避重试装饰器

    重试策略：
        - 第 1 次重试：等待 2 秒
        - 第 2 次重试：等待 4 秒
        - 第 3 次重试：等待 8 秒
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except RetryableError as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = backoff_base ** (attempt + 1)
                        wait_time += random.uniform(0, 1)  # 添加抖动，避免雪崩
                        logger.warning(f"请求失败，{wait_time:.1f}秒后重试 ({attempt + 1}/{max_retries}): {e}")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"请求失败，已达到最大重试次数 ({max_retries}): {e}")

                except NonRetryableError as e:
                    logger.error(f"请求失败（不可重试）: {e}")
                    raise

                except Exception as e:
                    # 未知错误，转为可重试
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = backoff_base ** (attempt + 1)
                        logger.warning(f"未知错误，{wait_time:.1f}秒后重试 ({attempt + 1}/{max_retries}): {e}")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"未知错误，已达到最大重试次数: {e}")

            # 所有重试都失败了
            raise last_exception if last_exception else Exception("请求失败")

        return wrapper
    return decorator


class Downloader:
    """
    同步下载器（带重试机制）
    所有爬虫共用，简单、稳定、抗封
    """

    def __init__(self):
        self.session = requests.Session()

        # 配置连接池和重试策略
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=Retry(
                total=0,  # 我们使用自定义重试逻辑
                connect=None,
                read=None,
                redirect=3  # 允许 3 次重定向
            )
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.headers.update(DEFAULT_HEADERS)
        self.logger = logger
        self.logger.debug("同步下载器初始化完成（带重试机制）")

    def _delay(self):
        """请求前延迟（反爬策略）"""
        if ENABLE_REQUEST_DELAY:
            delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
            self.logger.debug(f"请求延迟 {delay:.2f} 秒")
            time.sleep(delay)

    def _check_response(self, resp: requests.Response) -> None:
        """
        检查响应状态，决定是否需要重试

        :raises RetryableError: 需要重试的错误
        :raises NonRetryableError: 不需要重试的错误
        """
        if resp.status_code in RETRY_STATUS_CODES:
            raise RetryableError(f"HTTP {resp.status_code}: {resp.reason}")

        # 4xx 客户端错误（不需要重试）
        if 400 <= resp.status_code < 500:
            raise NonRetryableError(f"HTTP {resp.status_code}: {resp.reason}")

        # 其他 5xx 错误
        if resp.status_code >= 500:
            raise RetryableError(f"HTTP {resp.status_code}: {resp.reason}")

    @retry_with_backoff()
    def get(
            self,
            url: str,
            headers: Optional[Dict[str, str]] = None,
            cookies: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        """
        发送 GET 请求（带重试）

        :param url: 请求 URL
        :param headers: 自定义请求头
        :param cookies: Cookie
        :return: Response 对象
        :raises Exception: 所有重试都失败时抛出
        """
        self._delay()
        self.logger.debug(f"GET -> {url}")

        # 合并自定义请求头
        final_headers = DEFAULT_HEADERS.copy()
        if headers:
            final_headers.update(headers)

        try:
            resp = self.session.get(
                url=url,
                headers=final_headers,
                cookies=cookies,
                timeout=TIMEOUT,
                allow_redirects=True
            )
            self._check_response(resp)
            return resp

        except requests.exceptions.Timeout as e:
            raise RetryableError(f"请求超时: {e}")
        except requests.exceptions.ConnectionError as e:
            raise RetryableError(f"连接错误: {e}")
        except requests.exceptions.HTTPError as e:
            raise RetryableError(f"HTTP 错误: {e}")
        except requests.exceptions.RequestException as e:
            raise RetryableError(f"请求异常: {e}")

    @retry_with_backoff()
    def post(
            self,
            url: str,
            json_data: Optional[Dict] = None,
            headers: Optional[Dict[str, str]] = None,
            cookies: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        """
        发送 POST 请求（带重试）

        :param url: 请求 URL
        :param json_data: JSON 数据
        :param headers: 自定义请求头
        :param cookies: Cookie
        :return: Response 对象
        :raises Exception: 所有重试都失败时抛出
        """
        self._delay()
        self.logger.debug(f"POST -> {url}")

        # 合并自定义请求头
        final_headers = DEFAULT_HEADERS.copy()
        if headers:
            final_headers.update(headers)

        # 设置 Content-Type 为 JSON
        final_headers["Content-Type"] = "application/json;charset=UTF-8"

        try:
            resp = self.session.post(
                url=url,
                data=json.dumps(json_data, ensure_ascii=False).encode('utf-8') if json_data else None,
                headers=final_headers,
                cookies=cookies,
                timeout=TIMEOUT,
                allow_redirects=True
            )
            self._check_response(resp)
            return resp

        except requests.exceptions.Timeout as e:
            raise RetryableError(f"请求超时: {e}")
        except requests.exceptions.ConnectionError as e:
            raise RetryableError(f"连接错误: {e}")
        except requests.exceptions.HTTPError as e:
            raise RetryableError(f"HTTP 错误: {e}")
        except requests.exceptions.RequestException as e:
            raise RetryableError(f"请求异常: {e}")


# 全局单例（整个程序共用一个下载器）
downloader = Downloader()
