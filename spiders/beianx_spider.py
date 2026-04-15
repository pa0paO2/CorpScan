from spiders import BaseSpider
from models import CompanyModel
from core import downloader
from bs4 import BeautifulSoup
from urllib.parse import quote
from utils import logger

class BeianxSpider(BaseSpider):
    name = "beianx"  # 唯一标识

    def crawl(self, args: dict):
        """
        标准爬虫入口
        支持：--name 公司名 / --domain 域名 / --icp 备案号
        """
        # 1. 获取参数
        name = args.get("name")
        icp = args.get("icp")
        domain = args.get("domain")

        # 2. 确定搜索关键词（优先级：icp > domain > name）
        keyword = icp or domain or name
        if not keyword:
            self.logger.warning("未提供搜索关键词：icp / domain / name")
            return []

        # 3. URL编码 + 拼接地址
        kw_encoded = quote(keyword)
        url = f"https://www.beianx.cn/search/{kw_encoded}"

        # 4. 使用统一下载器请求（自带headers、session、日志）
        resp = downloader.get(url)
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
        for tr in table.find_all("tr")[1:]:
            tds = tr.find_all("td")
            if len(tds) < 6:
                continue

            # 提取备案信息
            icp_number = tds[3].get_text(strip=True)
            site_name = tds[4].get_text(strip=True)
            home_url = tds[5].get_text(strip=True)

            # 构造成项目统一的数据模型
            item = CompanyModel(
                name=site_name,               # 公司/网站名
                source=self.name,             # 来源：beianx
                icp_number=icp_number,        # 备案号
                domain=home_url,              # 域名
                asset_type="备案网站",        # 资产类型
            )

            self.add_result(item)

        self.logger.info(f"爬取完成，共获取 {len(self.results)} 条备案数据")
        return self.results