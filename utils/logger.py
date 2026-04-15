import logging
import sys
from datetime import datetime
from typing import Optional


def get_logger(name: str = "CorpScan", log_level: int = logging.INFO) -> logging.Logger:
    """
    获取全局统一日志器
    :param name: 日志器名称，默认 CorpScan
    :param log_level: 日志级别，默认 INFO
    :return: 配置好的日志器
    """
    # 避免重复添加处理器
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    # 设置日志级别
    logger.setLevel(log_level)

    # 定义日志格式：[时间] [级别] 内容
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台输出处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# 实例化全局日志器，供其他模块直接导入使用
logger = get_logger()

# 测试代码（运行该文件可验证日志是否正常）
if __name__ == "__main__":
    logger.info("✅ CorpScan 日志工具初始化成功！")
    logger.warning("⚠️  这是一条警告日志（测试）")
    logger.error("❌ 这是一条错误日志（测试）")