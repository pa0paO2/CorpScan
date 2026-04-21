
"""天眼查爬虫 - APP资产查询模块"""

from models import CompanyModel, AssetType
from core import downloader
from utils import logger
from typing import List, Dict, Any
from datetime import datetime

def query_apps(company_id: str, company_name: str, headers: dict,
               page: int, page_size: int) -> List[CompanyModel]:
    """
    查询APP信息
    :param company_id: 公司ID
    :param company_name: 公司名称
    :param headers: 请求头
    :param page: 页码
    :param page_size: 每页数量
    :return: CompanyModel 列表
    """
    timestamp = int(datetime.now().timestamp() * 1000)
    url = f"https://capi.tianyancha.com/cloud-business-state/v3/ar/appbkinfo?_={timestamp}&id={company_id}&pageSize={page_size}&pageNum={page}"

    try:
        resp = downloader.get(url, headers=headers)
        if resp.status_code != 200:
            logger.error(f"请求失败，状态码: {resp.status_code}")
            return []

        data = resp.json()
        logger.info(f"APP数据: {data}")
        if data.get("state") != "ok":
            return []

        response_data = data.get("data", {})
        app_list = response_data.get("items", [])
        results = []

        for app in app_list:
            results.append(CompanyModel(
                name=company_name,
                source="tianyancha",
                asset_type=AssetType.APP.value,
                app_name=app.get("name", ""),
                domain=app.get("icon", ""),
                extra={
                    "brief": app.get("brief", ""),
                    "filterName": app.get("filterName", ""),
                    "appType": app.get("type", ""),
                    "classes": app.get("classes", ""),
                    "appId": app.get("id", ""),
                }
            ))

        return results

    except Exception as e:
        logger.error(f"APP数据异常: {str(e)}")
        return []


def query_all_apps(company_id: str, company_name: str, headers: dict,
                   page_size: int = 10) -> List[CompanyModel]:
    """
    查询APP信息（自动分页获取全部数据）
    :param company_id: 公司ID
    :param company_name: 公司名称
    :param headers: 请求头
    :param page_size: 每页数量
    :return: CompanyModel 列表
    """
    all_results = []
    current_page = 1
    max_pages = 100  # 最大分页数限制，防止无限循环

    while current_page <= max_pages:
        results = query_apps(company_id, company_name, headers, current_page, page_size)

        if not results:
            logger.info(f"第 {current_page} 页无数据，停止分页")
            break

        all_results.extend(results)
        logger.info(f"第 {current_page} 页获取 {len(results)} 条记录，累计: {len(all_results)}")

        # 如果返回数据不足一页，说明是最后一页
        if len(results) < page_size:
            break

        current_page += 1

    logger.info(f"共获取 {len(all_results)} 条 APP 记录")
    return all_results


if __name__ == "__main__":
    # 测试 APP 查询功能
    from spiders.tianyancha.spider import TianyanchaSpider
    from spiders.tianyancha.search import search_company_id

    spider = TianyanchaSpider()
    test_company = "小米"

    logger.info(f"测试查询: {test_company}")

    # 1. 搜索公司ID
    company_id = search_company_id(test_company, spider.custom_headers)
    if not company_id:
        logger.warning(f"❌ 未找到公司: {test_company}")
        exit(1)

    # 2. 查询 APP（获取全部数据）
    results = query_all_apps(company_id, test_company, spider.custom_headers, page_size=10)

    if results:
        logger.info(f"✅ 查询成功，共 {len(results)} 条 APP 记录：")
        for item in results:
            logger.info(f"  - APP: {item.app_name}, 类型: {item.extra.get('appType', '')}, 分类: {item.extra.get('classes', '')}")
    else:
        logger.warning(f"⚠️ 未找到 {test_company} 的 APP 信息")
