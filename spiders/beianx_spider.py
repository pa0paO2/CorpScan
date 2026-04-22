from spiders import BaseSpider
from models import CompanyModel, AssetType
from core import downloader
from bs4 import BeautifulSoup
from urllib.parse import quote
from utils import logger
from typing import List, Dict, Any, Optional


class BeianxSpider(BaseSpider):
    name = "beianx"  # 唯一标识

    # 为 beianx 定制请求头
    custom_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.beianx.cn/",
        "Cookie": "__51vcke__JfvlrnUmvss1wiTZ=2ed97da4-130f-5e4d-8c2f-8955cae56234; __51vuft__JfvlrnUmvss1wiTZ=1752488893939; acw_tc=76b20fb017768226290668087eb24a64eb3e9309910a91631ae5734c598729; .AspNetCore.Antiforgery.OGq99nrNx5I=CfDJ8NYelk06Dw5AkNNJBvqDFlq2UkvS75jSf63l3Wmi4ys-nJVxP4SOQWdlJk9pjXfZmFNzBzKBDMTC5wStwEuWLXU9_waX1bYowdokiKBcmiCa4IIGVmCIZigI4upAP1_5Jec7OabAIN9WvGGInjXEAtQ; __51uvsct__JfvlrnUmvss1wiTZ=38; .AspNetCore.Session=CfDJ8NYelk06Dw5AkNNJBvqDFlpkhgPyjC%2BDyKnp%2Bvso2yt4e0O5%2BAaI68QBsUdaWJQKUAK7wbC7JVAJZltexsNb0AITnBXfRIXLDP2sVzTbMUbhG2IyT272GRAvpQ%2FJOtvjKGuHiLkAukTlFrJlZ8LG%2Fy4iaq50RPInl8NVyPE75w5R; __vtins__JfvlrnUmvss1wiTZ=%7B%22sid%22%3A%20%22e7817e38-69ba-5c9d-b2fc-42a9a07ede05%22%2C%20%22vd%22%3A%2011%2C%20%22stt%22%3A%2095719%2C%20%22dr%22%3A%2011975%2C%20%22expires%22%3A%201776824530523%2C%20%22ct%22%3A%201776822730523%7D; machine_str=22b85b7ced-4af0-4614-be83-37bac78e4654"
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


def get_company_by_icp(icp_number: str) -> Optional[str]:
    """
    通过 ICP 备案号查询公司名称（独立函数，供 TianyanchaSpider 调用）

    实现：创建临时 BeianxSpider 实例，调用 parse_page 获取第一行公司名

    :param icp_number: ICP 备案号（如 "京ICP备16020685号" 或 "京ICP备16020685号-1"）
    :return: 公司名称，未找到返回 None
    """
    if not icp_number:
        logger.warning("ICP 备案号为空")
        return None

    spider = BeianxSpider()
    args = {"icp": icp_number}

    results = spider.parse_page(args, page=1, page_size=1)
    if results and len(results) > 0:
        company_name = results[0].name
        logger.info(f"ICP {icp_number} -> 公司: {company_name}")
        return company_name

    logger.warning(f"ICP 查询无结果: {icp_number}")
    return None


if __name__ == "__main__":
    # 测试：通过 ICP 备案号查询公司名
    test_icp = "京ICP备10046444号"
    company_name = get_company_by_icp(test_icp)

    if company_name:
        print(f"\n查询成功！")
        print(f"ICP 备案号: {test_icp}")
        print(f"公司名称: {company_name}")
    else:
        print(f"\n未找到 ICP 备案号对应的公司: {test_icp}")
