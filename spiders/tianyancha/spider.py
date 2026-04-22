import json
import sys
from pathlib import Path
from spiders.base_spider import BaseSpider
from models import CompanyModel, AssetType
from utils import logger
from typing import List, Dict, Any, Optional


def _find_secrets_json() -> Path:
    """
    查找 secrets.json 配置文件（支持开发和打包环境）

    查找顺序：
        1. 当前工作目录 (./secrets.json)
        2. 程序所在目录 (与 exe 同级)
        3. 项目 config 目录 (开发环境兼容)

    :return: 配置文件路径（可能不存在）
    """
    # 1. 当前工作目录
    cwd_path = Path.cwd() / "secrets.json"
    if cwd_path.exists():
        return cwd_path

    # 2. 程序所在目录（打包后的 exe 目录）
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的 exe 环境
        exe_dir = Path(sys.executable).parent
    else:
        # 普通 Python 环境
        exe_dir = Path(__file__).parent.parent.parent

    exe_path = exe_dir / "secrets.json"
    if exe_path.exists():
        return exe_path

    # 3. 开发环境：config/secrets.json
    config_path = exe_dir / "config" / "secrets.json"
    return config_path  # 返回默认路径（即使不存在）

from spiders.tianyancha.search import search_company_id
from spiders.tianyancha.website import query_all_websites as query_websites
from spiders.tianyancha.app import query_all_apps as query_apps
from spiders.tianyancha.miniapp import query_all_miniapps as query_miniapps
from spiders.tianyancha.subsidiary import query_subsidiaries
from spiders.beianx_spider import get_company_by_icp


class TianyanchaSpider(BaseSpider):
    """
    天眼查爬虫 - 从 secrets.json 读取敏感配置

    配置路径（按优先级）：
        1. ./secrets.json（当前工作目录）
        2. ./secrets.json（程序所在目录，与exe同级）
        3. ./config/secrets.json（开发环境）

    secrets.json 格式：
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

        # 查找并加载 secrets.json
        config_path = _find_secrets_json()
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    secrets = json.load(f)
                tyc_secrets = secrets.get("tianyancha", {})
                headers.update({k: v for k, v in tyc_secrets.items() if v})
                logger.debug(f"已从 {config_path} 加载配置")
            except Exception as e:
                logger.warning(f"加载 secrets.json 失败: {e}")
        else:
            logger.warning(f"未找到 secrets.json，已尝试路径: {config_path}")

        return headers

    def __init__(self):
        super().__init__()
        self._company_id: Optional[str] = None
        self._company_name: Optional[str] = None

    def crawl(self, args: Dict[str, Any]) -> List[CompanyModel]:
        """
        统一入口

        参数：
            - name: 公司名称
            - icp: ICP备案号（自动查公司名）
            - asset_type: 资产类型过滤（可选，默认查全部）
        """
        # 1. 获取公司名称
        company_name = args.get("name")
        icp_number = args.get("icp")

        # 如果没有 name 但有 icp，先通过备案号查询公司名
        if not company_name and icp_number:
            company_name = get_company_by_icp(icp_number)
            if company_name:
                self.logger.info(f"ICP {icp_number} -> 公司: {company_name}")
                args["name"] = company_name  # 更新参数供后续使用

        if not company_name:
            self.logger.error("缺少必要参数: name 或 icp")
            return []

        # 2. 获取公司ID（优先从args传入，避免重复搜索）
        if not self._company_id:
            self._company_id = args.get("company_id")
            if not self._company_id:
                self._company_id = search_company_id(company_name, self.custom_headers)
            if not self._company_id:
                return []
            self._company_name = company_name

        # 3. 查询控股公司（仅当指定了equity参数时才查询）
        subsidiaries = []
        # 只有当显式传入equity参数时才查询控股公司
        if args.get("equity") is not None and not args.get("skip_subsidiary_query"):
            min_equity = args.get("equity", 0.5)
            if isinstance(min_equity, str):
                try:
                    min_equity = float(min_equity)
                except ValueError:
                    min_equity = 0.5

            # 如果args中已传入subsidiaries，直接使用（避免重复查询）
            subsidiaries = args.get("subsidiaries", [])
            if not subsidiaries:
                subsidiaries = query_subsidiaries(
                    self._company_id,
                    self._company_name,
                    self.custom_headers,
                    min_equity=min_equity
                )
            self.logger.info(f"[控股公司] 获取 {len(subsidiaries)} 条（股权>={min_equity}）")

        # 4. 查询资产（各query函数内部自动分页）
        all_results = []
        filter_type = args.get("asset_type")

        # 网站
        if not filter_type or filter_type == AssetType.WEBSITE.value:
            websites = query_websites(self._company_id, self._company_name, self.custom_headers, page_size=10)
            # 为主公司记录添加控股公司信息
            if websites and subsidiaries:
                for site in websites:
                    site.extra["subsidiaries"] = [
                        {
                            "name": sub.name,
                            "companyId": sub.extra.get("companyId"),
                            "equityRatio": sub.extra.get("equityRatio"),
                            "equityPercent": sub.extra.get("equityPercent"),
                            "investAmount": sub.extra.get("investAmount"),
                            "registerStatus": sub.extra.get("registerStatus"),
                        }
                        for sub in subsidiaries
                    ]
            all_results.extend(websites)
            self.logger.info(f"[网站] 获取 {len(websites)} 条")

        # APP
        if not filter_type or filter_type == AssetType.APP.value:
            apps = query_apps(self._company_id, self._company_name, self.custom_headers, page_size=10)
            if apps and subsidiaries:
                for app in apps:
                    app.extra["subsidiaries"] = [
                        {
                            "name": sub.name,
                            "companyId": sub.extra.get("companyId"),
                            "equityRatio": sub.extra.get("equityRatio"),
                            "equityPercent": sub.extra.get("equityPercent"),
                        }
                        for sub in subsidiaries
                    ]
            all_results.extend(apps)
            self.logger.info(f"[APP] 获取 {len(apps)} 条")

        # 小程序
        if not filter_type or filter_type == AssetType.MINIPROGRAM.value:
            miniapps = query_miniapps(self._company_id, self._company_name, self.custom_headers, page_size=10)
            if miniapps and subsidiaries:
                for mini in miniapps:
                    mini.extra["subsidiaries"] = [
                        {
                            "name": sub.name,
                            "companyId": sub.extra.get("companyId"),
                            "equityRatio": sub.extra.get("equityRatio"),
                            "equityPercent": sub.extra.get("equityPercent"),
                        }
                        for sub in subsidiaries
                    ]
            all_results.extend(miniapps)
            self.logger.info(f"[小程序] 获取 {len(miniapps)} 条")

        self.results = all_results
        self.logger.info(f"爬取完成，共 {len(self.results)} 条数据")
        return self.results
