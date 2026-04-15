from spiders import BaseSpider
from models import CompanyModel
from core import downloader

class DemoSpider(BaseSpider):
    # 【必填】唯一标识，不能重复
    name = "demo"

    def crawl(self, keyword: str):
        """
        【核心方法】
        1. 发送请求
        2. 解析数据
        3. 组装 CompanyModel
        4. 返回列表
        """
        # ======================
        # 1. 拼接URL / 准备参数
        # ======================
        url = f"https://xxx.com/search={keyword}"

        # ======================
        # 2. 发送请求（统一用 downloader）
        # ======================
        resp = downloader.get(url)

        # ======================
        # 3. 解析数据（你自己写）
        # ======================
        # 这里写解析逻辑

        # ======================
        # 4. 组装标准数据模型
        # ======================
        item = CompanyModel(
            name="企业名称",
            source=self.name,
            legal_person="法人",
            phone="电话",
            email="邮箱",
            address="地址",
            status="存续",
            credit_code="统一信用代码"
        )

        # ======================
        # 5. 存入结果并返回
        # ======================
        self.add_result(item)
        return self.results