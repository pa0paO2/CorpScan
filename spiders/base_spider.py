from typing import List, Dict, Any, Optional
from utils import logger
from models import CompanyModel


class BaseSpider:
    """
    爬虫基类（所有爬虫必须继承）
    统一规范：接收 args 参数，支持多条件搜索和分页
    """
    name: str = "base"

    # 子类可重写此属性来定义自己的请求头
    custom_headers: Dict[str, str] = {}

    # 默认分页配置
    default_page_size: int = 10
    max_pages: int = 100  # 最大爬取页数，防止无限循环

    def __init__(self):
        self.logger = logger
        self.results: List[CompanyModel] = []
        self.current_page: int = 1

    def start(self):
        """爬虫启动前准备"""
        self.logger.info(f"✅ 启动爬虫: [{self.name}]")

    def crawl(self, args: Dict[str, Any]) -> List[CompanyModel]:
        """
        【必须实现】爬虫入口
        :param args: 所有参数: name, domain, icp, page, page_size等
        """
        raise NotImplementedError("子类必须实现 crawl(args) 方法")

    def crawl_with_pagination(self, args: Dict[str, Any]) -> List[CompanyModel]:
        """
        【可选重写】带分页的爬虫入口
        默认实现：循环调用 parse_page 直到没有更多数据
        :param args: 包含 page, page_size 等参数
        """
        page = args.get("page", 1)
        page_size = args.get("page_size", self.default_page_size)

        all_results = []

        for current_page in range(page, self.max_pages + 1):
            self.logger.info(f"正在爬取第 {current_page} 页...")

            # 调用子类的页面解析方法
            page_results = self.parse_page(args, current_page, page_size)

            if not page_results:
                self.logger.info(f"第 {current_page} 页无数据，停止分页")
                break

            all_results.extend(page_results)
            self.logger.info(f"第 {current_page} 页获取 {len(page_results)} 条数据")

            # 如果返回数据少于页大小，说明是最后一页
            if len(page_results) < page_size:
                break

        self.results = all_results
        self.logger.info(f"爬取完成，共获取 {len(self.results)} 条数据")
        return self.results

    def parse_page(self, args: Dict[str, Any], page: int, page_size: int) -> List[CompanyModel]:
        """
        【必须实现】解析单页数据
        :param args: 搜索参数
        :param page: 当前页码
        :param page_size: 每页数量
        :return: 当前页的数据列表
        """
        raise NotImplementedError("子类必须实现 parse_page(args, page, page_size) 方法")

    def add_result(self, item: CompanyModel):
        """添加一条结果"""
        if item:
            self.results.append(item)

    def get_results(self) -> List[CompanyModel]:
        """获取所有结果"""
        return self.results

    def clear_results(self):
        """清空结果"""
        self.results.clear()
