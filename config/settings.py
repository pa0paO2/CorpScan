# 全局请求配置（可后续根据需求调整）
TIMEOUT: int = 10  # 请求超时时间（秒）
MAX_CONCURRENT_TASKS: int = 5  # 最大并发任务数（反爬友好）
REQUEST_DELAY_MIN: float = 1.0  # 请求前最小延迟（秒）
REQUEST_DELAY_MAX: float = 3.0  # 请求前最大延迟（秒）
ENABLE_REQUEST_DELAY: bool = True  # 是否启用请求延迟

# 网络重试配置（指数退避策略）
MAX_RETRIES: int = 3  # 最大重试次数
RETRY_BACKOFF_BASE: float = 2.0  # 退避基数（秒），首次重试等待 2^1=2秒，第二次 2^2=4秒...
RETRY_STATUS_CODES: list = [429, 500, 502, 503, 504]  # 需要重试的 HTTP 状态码
# 默认请求头（伪造浏览器，避免被识别为爬虫）
DEFAULT_HEADERS: dict = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Connection": "keep-alive"
}

# 目录配置（自动创建，无需手动建）
OUTPUT_DIR: str = "output"  # 导出文件目录
LOG_DIR: str = "logs"       # 日志文件目录（后续扩展）

# 爬虫配置（后续扩展，暂时预留）
SPIDER_ENABLED: dict = {
    "tianyancha": True,  # 天眼查爬虫开关
    "qcc": True          # 企查查爬虫开关
}

# 在 settings.py 末尾添加测试代码
if __name__ == "__main__":
    print("✅ 全局配置加载成功！")
    print(f"请求超时时间：{TIMEOUT} 秒")
    print(f"最大并发数：{MAX_CONCURRENT_TASKS}")