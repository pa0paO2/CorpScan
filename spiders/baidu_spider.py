from spiders import BaseSpider
from models import CompanyModel
from core import downloader

class BaiduSpider(BaseSpider):
    name = "baidu"

    def crawl(self, args: dict):
        # 从参数里取 公司名称
        name = args.get("name")
        if not name:
            self.logger.warning("未传入公司名称，跳过爬取")
            return []

        # 百度搜索
        url = f"https://www.baidu.com/s?wd={name}"
        resp = downloader.get(url)

        self.logger.info(f"请求完成 | 状态码: {resp.status_code}")

        # 构造标准数据模型
        item = CompanyModel(
            name=f"百度搜索结果_{name}",
            source=self.name,
            status="正常",
            phone="123456789",
            email="test@corp.com"
        )

        self.add_result(item)
        return self.results