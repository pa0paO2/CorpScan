
"""天眼查爬虫 - 小程序资产查询模块"""

from models import CompanyModel, AssetType
from core import downloader
from utils import logger
from typing import List, Dict, Any
from datetime import datetime

def query_miniapps(company_id: str, company_name: str, headers: dict,
                   page: int, page_size: int) -> List[CompanyModel]:
    """
    查询小程序备案信息（单页）
    :param company_id: 公司ID
    :param company_name: 公司名称
    :param headers: 请求头
    :param page: 页码
    :param page_size: 每页数量
    :return: CompanyModel 列表
    """
    timestamp = int(datetime.now().timestamp() * 1000)
    url = f"https://capi.tianyancha.com/cloud-intellectual-property/intellectualProperty/miniProgramIcpRecordList?_={timestamp}&gid={company_id}&pageSize={page_size}&pageNum={page}"

    try:
        resp = downloader.get(url, headers=headers)
        data = resp.json()

        if resp.status_code != 200:
            logger.error(f"请求失败，状态码: {resp.status_code}")
            return []

        if data.get("state") != "ok":
            logger.warning(f"API返回异常: {data.get('message', 'unknown')}")
            return []

        # 注意：实际返回的字段路径是 data['data']['miniProgramIcpRecordList']
        response_data = data.get("data", {})
        miniapp_list = response_data.get("miniProgramIcpRecordList", [])
        results = []

        for app in miniapp_list:
            # 提取备案详情中的信息
            detail = app.get("miniProgramIcpRecordDetail", {})
            service_info = detail.get("icpFilingServiceInformation", {})
            subject_info = detail.get("icpFilingSubjectInformation", {})

            # 优先使用传入的公司名称（确保是完整名称）
            api_company_name = subject_info.get("organizingName", "")
            results.append(CompanyModel(
                name=company_name,
                source="tianyancha",
                asset_type=AssetType.MINIPROGRAM.value,
                miniapp_name=app.get("serviceName", ""),
                icp_number=app.get("serviceFilingNumber", ""),
                extra={
                    "examineDate": app.get("examineDate", ""),
                    "icpLicenseNumber": service_info.get("icpLicenseNumber", ""),
                    "organizingProperty": subject_info.get("organizingProperty", ""),
                    "apiCompanyName": api_company_name if api_company_name != company_name else "",
                }
            ))

        return results

    except Exception as e:
        logger.error(f"小程序数据异常: {str(e)}")
        return []


def query_all_miniapps(company_id: str, company_name: str, headers: dict,
                       page_size: int = 10) -> List[CompanyModel]:
    """
    查询小程序备案信息（自动分页获取全部数据）
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
        results = query_miniapps(company_id, company_name, headers, current_page, page_size)

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

    results = query_all_miniapps(company_id, test_company, spider.custom_headers, page_size=10)
    print(f"查询完成，共 {len(results)} 条小程序备案记录")
