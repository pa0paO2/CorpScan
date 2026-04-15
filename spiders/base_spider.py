from typing import List, Dict, Any
from utils import logger
from models import CompanyModel

class BaseSpider:
    """
    爬虫基类（所有爬虫必须继承）
    统一规范：接收 args 参数，支持多条件搜索
    """
    name: str = "base"

    def __init__(self):
        self.logger = logger
        self.results: List[CompanyModel] = []

    def start(self):
        """爬虫启动前准备"""
        self.logger.info(f"✅ 启动爬虫: [{self.name}]")

    def crawl(self, args: Dict[str, Any]) -> List[CompanyModel]:
        """
        【必须实现】爬虫入口
        :param args: 所有参数: name, domain, icp, equity
        """
        raise NotImplementedError("子类必须实现 crawl(args) 方法")

    def add_result(self, item: CompanyModel):
        """添加一条结果"""
        if item:
            self.results.append(item)

    def get_results(self) -> List[CompanyModel]:
        return self.results