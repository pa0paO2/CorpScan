from spiders import BaseSpider
from models import CompanyModel, AssetType
from core import downloader
from bs4 import BeautifulSoup
from urllib.parse import quote
from utils import logger
from typing import List, Dict, Any


class BeianxSpider(BaseSpider):
    name = "beianx"  # 唯一标识

    # 为 beianx 定制请求头
    custom_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.beianx.cn/",
        "Cookie": "__51vcke__JfvlrnUmvss1wiTZ=2ed97da4-130f-5e4d-8c2f-8955cae56234; __51vuft__JfvlrnUmvss1wiTZ=1752488893939; acw_tc=707c9f7817763029060142431e9f8bfaf8d90276dd56ff30f8761d0bccbf64; .AspNetCore.Antiforgery.OGq99nrNx5I=CfDJ8NYelk06Dw5AkNNJBvqDFlqxRAJ6Ogdl13aHnsJinXEOiS1ANiB78se-I3D7hj-1StEguN51OkhGY8KHRWhzLyrw273fHoIjpDk8tjidgskrRy8QtbTcScvyKh2Wt5-I3wZ1MGfvKHvqj6-4QshjGGU; __51uvsct__JfvlrnUmvss1wiTZ=36; .AspNetCore.Session=CfDJ8NYelk06Dw5AkNNJBvqDFlpvbE1lO4XBKoB7CLv8RkSEixmKCzlMWyFeIwJ4ngJgg5BQWRJNdyk1bf4D%2Bh2hVD%2BNa9pWMepo5sJyusNHwZAk%2BOySvVeGpxjV8dvFJkLB3wsGXmUfdCaWRJT0ZdkMtD5XsAI0csBCs44O0MrGwinY; __vtins__JfvlrnUmvss1wiTZ=%7B%22sid%22%3A%20%22550c3675-faaa-52f4-9f8d-f7022a675d2d%22%2C%20%22vd%22%3A%203%2C%20%22stt%22%3A%2024914%2C%20%22dr%22%3A%2018951%2C%20%22expires%22%3A%201776304732406%2C%20%22ct%22%3A%201776302932406%7D; machine_str=1667be594e-7222-4270-b889-f40a67dd4b70"
    }

    def crawl(self, args: dict):
        """
        标准爬虫入口（兼容旧接口）
        支持：--name 公司名 / --domain 域名 / --icp 备案号
        """
        # 检查是否需要分页
        if args.get("enable_pagination"):
            return self.crawl_with_pagination(args)

        # 原有逻辑：只爬取第一页
        return self.parse_page(args, page=1, page_size=self.default_page_size)

    def parse_page(self, args: Dict[str, Any], page: int, page_size: int) -> List[CompanyModel]:
        """
        解析单页数据
        :param args: 搜索参数
        :param page: 页码（beianx可能不支持分页，这里做兼容）
        :param page_size: 每页数量
        """
        # 1. 获取参数
        name = args.get("name")
        icp = args.get("icp")
        domain = args.get("domain")
        asset_filter = args.get("asset_type")  # 可选：过滤资产类型

        # 2. 确定搜索关键词（优先级：icp > domain > name）
        keyword = icp or domain or name
        if not keyword:
            self.logger.warning("未提供搜索关键词：icp / domain / name")
            return []

        # 3. URL编码 + 拼接地址
        kw_encoded = quote(keyword)
        url = f"https://www.beianx.cn/search/{kw_encoded}"

        # TODO: 如果beianx支持分页参数，在这里添加
        # if page > 1:
        #     url += f"?page={page}&pageSize={page_size}"

        # 4. 使用统一下载器请求（传入自定义headers）
        resp = downloader.get(url, headers=self.custom_headers)
        if resp.status_code != 200:
            self.logger.error(f"请求失败，状态码：{resp.status_code}")
            return []

        # 5. 解析页面
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", class_="table")
        if not table:
            self.logger.info("未查询到备案数据")
            return []

        # 6. 遍历数据，组装成 CompanyModel
        page_results = []
        for tr in table.find_all("tr")[1:]:
            tds = tr.find_all("td")
            if len(tds) < 6:
                continue

            # 提取备案信息
            company_name = tds[1].get_text(strip=True)
            icp_number = tds[3].get_text(strip=True)
            site_name = tds[4].get_text(strip=True)
            home_url = tds[5].get_text(strip=True)

            # 如果指定了资产类型过滤，跳过不匹配的
            if asset_filter and asset_filter != AssetType.WEBSITE.value:
                continue

            # 构造成项目统一的数据模型
            item = CompanyModel(
                name=company_name,
                source=self.name,
                icp_number=icp_number,
                domain=home_url,
                site_name=site_name,
                asset_type=AssetType.WEBSITE.value,
            )

            page_results.append(item)

        return page_results

    def parse_app_page(self, args: Dict[str, Any], page: int, page_size: int) -> List[CompanyModel]:
        """
        解析APP备案数据（如果beianx支持APP查询）
        :param args: 搜索参数
        :param page: 页码
        :param page_size: 每页数量
        """
        # TODO: 实现APP备案查询逻辑
        # 示例URL: https://www.beianx.cn/app-search/xxx?page=1
        self.logger.warning("APP备案查询功能待实现")
        return []

    def parse_miniapp_page(self, args: Dict[str, Any], page: int, page_size: int) -> List[CompanyModel]:
        """
        解析小程序备案数据（如果beianx支持小程序查询）
        :param args: 搜索参数
        :param page: 页码
        :param page_size: 每页数量
        """
        # TODO: 实现小程序备案查询逻辑
        # 示例URL: https://www.beianx.cn/miniprogram-search/xxx?page=1
        self.logger.warning("小程序备案查询功能待实现")
        return []
