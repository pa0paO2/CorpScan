from .base_spider import BaseSpider
from .baidu_spider import BaiduSpider
from .beianx_spider import BeianxSpider  # <--- 加这行

__all__ = ["BaseSpider", "BaiduSpider", "BeianxSpider"]