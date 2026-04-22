
"""天眼查爬虫 - 网站资产查询模块"""

from models import CompanyModel, AssetType
from core import downloader
from utils import logger
from typing import List, Dict, Any
from datetime import datetime

def query_websites(company_id: str, company_name: str, headers: dict,
                   page: int, page_size: int) -> List[CompanyModel]:
    """
    查询网站备案信息（单页）
    :param company_id: 公司ID
    :param company_name: 公司名称
    :param headers: 请求头
    :param page: 页码
    :param page_size: 每页数量
    :return: CompanyModel 列表
    """
    timestamp = int(datetime.now().timestamp() * 1000)
    url = f"https://capi.tianyancha.com/cloud-intellectual-property/intellectualProperty/icpRecordList?_={timestamp}&id={company_id}&pageSize={page_size}&pageNum={page}"

    try:
        resp = downloader.get(url, headers=headers)
        data = resp.json()

        if resp.status_code != 200:
            logger.error(f"请求失败，状态码: {resp.status_code}")
            return []

        if data.get("state") != "ok":
            logger.warning(f"API返回异常: {data.get('message', 'unknown')}")
            return []

        # 注意：实际返回的字段路径是 data['data']['item']，不是 'items'
        website_list = data.get("data", {}).get("item", [])
        results = []

        for item in website_list:
            results.append(CompanyModel(
                name=item.get("companyName", company_name),
                source="tianyancha",
                icp_number=item.get("liscense", ""),
                domain=item.get("ym", ""),
                site_name=item.get("webName", ""),
                asset_type=AssetType.WEBSITE.value,
                extra={
                    "examineDate": item.get("examineDate", ""),
                    "companyType": item.get("companyType", ""),
                }
            ))

        return results

    except Exception as e:
        logger.error(f"网站数据异常: {str(e)}")
        return []


def query_all_websites(company_id: str, company_name: str, headers: dict,
                       page_size: int = 10) -> List[CompanyModel]:
    """
    查询网站备案信息（自动分页获取全部数据）
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
        results = query_websites(company_id, company_name, headers, current_page, page_size)

        if not results:
            break

        all_results.extend(results)

        # 如果返回数据不足一页，说明是最后一页
        if len(results) < page_size:
            break

        current_page += 1

    return all_results


if __name__ == "__main__":
    from spiders.tianyancha.spider import TianyanchaSpider
    from spiders.tianyancha.search import search_company_id

    spider = TianyanchaSpider()
    test_company = "小米"

    company_id = search_company_id(test_company, spider.custom_headers)
    if not company_id:
        print(f"未找到公司: {test_company}")
        exit(1)

    results = query_all_websites(company_id, test_company, spider.custom_headers, page_size=10)
    print(f"查询完成，共 {len(results)} 条网站备案记录")

