from typing import List, Dict, Any
from utils import logger
from spiders import BaseSpider
from models import CompanyModel

class Engine:
    """
    爬虫引擎（核心调度器）
    负责加载爬虫、执行任务、收集结果
    支持多条件搜索：名称 / 域名 / 备案 / 子公司股权
    """
    def __init__(self):
        self.logger = logger
        self.spiders: List[BaseSpider] = []
        self.results: List[CompanyModel] = []

    def register_spider(self, spider: BaseSpider):
        """注册爬虫（可注册多个）"""
        self.spiders.append(spider)
        self.logger.info(f"✅ 注册爬虫: {spider.name}")

    def run(self, args: Dict[str, Any]):
        """
        引擎启动（接收完整参数）
        :param args: 命令行参数 {name, domain, icp, equity}
        """
        self.logger.info("=" * 50)
        self.logger.info(f"🚀 CorpScan 引擎启动")
        self.logger.info(f"📝 任务参数: {args}")
        self.logger.info("=" * 50)

        # 遍历所有爬虫并执行
        for spider in self.spiders:
            try:
                spider.start()
                items = spider.crawl(args=args)  # 给爬虫传全部参数
                self.results.extend(items)
                self.logger.info(f"✅ [{spider.name}] 完成 | 获取 {len(items)} 条数据")

            except Exception as e:
                self.logger.error(f"❌ [{spider.name}] 执行失败: {str(e)}")

        self.logger.info("=" * 50)
        self.logger.info(f"🏁 全部任务结束 | 总计结果: {len(self.results)} 条")
        self.logger.info("=" * 50)

    def get_results(self) -> List[CompanyModel]:
        """获取最终结果列表"""
        return self.results