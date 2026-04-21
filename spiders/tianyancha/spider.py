import json
from pathlib import Path
from spiders.base_spider import BaseSpider
from models import CompanyModel, AssetType
from utils import logger
from typing import List, Dict, Any, Optional

from spiders.tianyancha.search import search_company_id
from spiders.tianyancha.website import query_all_websites as query_websites
from spiders.tianyancha.app import query_all_apps as query_apps
from spiders.tianyancha.miniapp import query_all_miniapps as query_miniapps


class TianyanchaSpider(BaseSpider):
    """
    天眼查爬虫 - 从 config/secrets.json 读取敏感配置

    配置路径：项目根目录/config/secrets.json
    {
        "tianyancha": {
            "X-AUTH-TOKEN": "your_token",
            "X-TYCID": "your_tycid"
        }
    }
    """
    name = "tianyancha"

    # 基础请求头（非敏感）
    _base_headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Host": "capi.tianyancha.com",
        "Origin": "https://www.tianyancha.com",
        "Pragma": "no-cache",
        "Referer": "https://www.tianyancha.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0",
        "sec-ch-ua": '"Microsoft Edge";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "version": "TYC-Web"
    }

    @property
    def custom_headers(self) -> Dict[str, str]:
        """动态加载配置（支持运行时修改 secrets.json）"""
        headers = self._base_headers.copy()

        # 加载 secrets.json
        config_path = Path(__file__).parent.parent.parent / "config" / "secrets.json"
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    secrets = json.load(f)
                tyc_secrets = secrets.get("tianyancha", {})
                headers.update({k: v for k, v in tyc_secrets.items() if v})
            except Exception as e:
                logger.warning(f"加载 secrets.json 失败: {e}")

        return headers

    def __init__(self):
        super().__init__()
        self._company_id: Optional[str] = None
        self._company_name: Optional[str] = None

    def crawl(self, args: Dict[str, Any]) -> List[CompanyModel]:
        """
        统一入口

        参数：
            - name: 公司名称（必需）
            - asset_type: 资产类型过滤（可选，默认查全部）
        """
        # 1. 验证参数
        company_name = args.get("name")
        if not company_name:
            self.logger.error("缺少必要参数: name")
            return []

        # 2. 获取公司ID
        if not self._company_id:
            self._company_id = search_company_id(company_name, self.custom_headers)
            if not self._company_id:
                return []
            self._company_name = company_name

        # 3. 查询资产（各query函数内部自动分页）
        all_results = []
        filter_type = args.get("asset_type")

        # 网站
        if not filter_type or filter_type == AssetType.WEBSITE.value:
            websites = query_websites(self._company_id, self._company_name, self.custom_headers, page_size=10)
            all_results.extend(websites)
            self.logger.info(f"[网站] 获取 {len(websites)} 条")

        # APP
        if not filter_type or filter_type == AssetType.APP.value:
            apps = query_apps(self._company_id, self._company_name, self.custom_headers, page_size=10)
            all_results.extend(apps)
            self.logger.info(f"[APP] 获取 {len(apps)} 条")

        # 小程序
        if not filter_type or filter_type == AssetType.MINIPROGRAM.value:
            miniapps = query_miniapps(self._company_id, self._company_name, self.custom_headers, page_size=10)
            all_results.extend(miniapps)
            self.logger.info(f"[小程序] 获取 {len(miniapps)} 条")

        self.results = all_results
        self.logger.info(f"爬取完成，共 {len(self.results)} 条数据")
        return self.results
