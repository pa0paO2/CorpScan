"""天眼查爬虫 - 控股公司查询模块"""

from models import CompanyModel, AssetType
from core import downloader
from utils import logger
from typing import List, Dict, Any, Optional
from datetime import datetime


def query_subsidiaries(
    company_id: str,
    company_name: str,
    headers: dict,
    min_equity: float = 0.0
) -> List[CompanyModel]:
    """
    查询控股公司信息（支持股权比例筛选）

    :param company_id: 公司ID
    :param company_name: 公司名称
    :param headers: 请求头
    :param min_equity: 最小股权比例（如0.5表示筛选股权大于50%的），默认0不筛选
    :return: CompanyModel 列表
    """
    timestamp = int(datetime.now().timestamp() * 1000)
    url = f"https://capi.tianyancha.com/tyc-enterprise-graph/ei/get/penetration/slow/graph/single?_={timestamp}"

    # 合并额外请求头
    request_headers = headers.copy()
    request_headers.update({
        "Pm": "9",
        "Spm": "i9",
        "Eventid": "i9"
    })

    # 请求体
    json_data = {
        "idList": [company_id],
        "direct": "OUT",
        "centerId": company_id,
        "entityType": "2",
        "year": datetime.now().year,
        "depth": 1,
        "eventId": "i9",
        "pm": "9",
        "spm": "i9",
        "page_id": "TYCGraphPage",
        "needCenterNode": True,
        "sessionId": "",
        "traceId": timestamp - 4,
        "previousSignature": "",
        "signature": ""
    }

    try:
        resp = downloader.post(url, json_data=json_data, headers=request_headers)
        data = resp.json()

        if resp.status_code != 200:
            logger.error(f"控股公司查询失败，状态码: {resp.status_code}")
            return []

        if data.get("state") != "ok":
            logger.warning(f"控股公司API返回异常: {data.get('message', 'unknown')}")
            return []

        result_data = data.get("data", {})
        nodes_map = result_data.get("nodesMap", {})  # 公司详情映射表
        tree_list = result_data.get("treeList", [])  # 投资关系树

        results = []

        # 从 treeList 解析控股关系
        for tree in tree_list:
            # investorList 是被投资的公司（控股公司）
            investor_list = tree.get("investorList", [])

            for investor in investor_list:
                subsidiary_id = str(investor.get("id", ""))
                equity_ratio = investor.get("ratio", 0)  # 股权比例
                amount = investor.get("amountStr", "")  # 投资金额
                investor_type = investor.get("investorType", 1)

                # 股权比例筛选
                if min_equity > 0 and equity_ratio < min_equity:
                    continue

                # 从 nodesMap 获取公司详细信息
                node_info = nodes_map.get(subsidiary_id, {})

                # 获取公司状态标签
                status_tag = node_info.get("statusTag", {})
                register_status = status_tag.get("name", "")

                # 获取其他标签
                tag_list = node_info.get("tagList", [])
                tags = [tag.get("name", "") for tag in tag_list]

                results.append(CompanyModel(
                    name=node_info.get("name", ""),
                    source="tianyancha",
                    asset_type=AssetType.SUBSIDIARY.value,
                    extra={
                        "companyId": subsidiary_id,
                        "equityRatio": equity_ratio,  # 股权比例
                        "equityPercent": f"{equity_ratio * 100:.2f}%" if equity_ratio else "-",
                        "investAmount": amount,  # 投资金额
                        "investorType": investor_type,
                        "registerStatus": register_status or node_info.get("registerStatus", ""),  # 注册状态
                        "industry": node_info.get("industry", ""),  # 行业
                        "companyType": node_info.get("entityTag", ""),  # 公司类型
                        "tags": tags,  # 标签列表
                        "isValid": node_info.get("isValid", True),
                        "parentName": company_name,
                        "parentId": company_id,
                    }
                ))

        logger.info(f"控股公司查询完成: {company_name} 找到 {len(results)} 家（股权>={min_equity}）")
        return results

    except Exception as e:
        logger.error(f"控股公司数据异常: {str(e)}")
        return []


if __name__ == "__main__":
    from spiders.tianyancha.spider import TianyanchaSpider
    from spiders.tianyancha.search import search_company_id

    spider = TianyanchaSpider()
    test_company = "小米"

    company_id = search_company_id(test_company, spider.custom_headers)
    if not company_id:
        print(f"未找到公司: {test_company}")
        exit(1)

    # 测试：查询股权大于 50% 的控股公司
    results = query_subsidiaries(company_id, test_company, spider.custom_headers, min_equity=0.5)
    print(f"\n查询完成，共 {len(results)} 条控股公司记录（股权>=50%）\n")

    for item in results:
        extra = item.extra
        print(f"- {item.name}")
        print(f"  公司ID: {extra.get('companyId')}")
        print(f"  股权比例: {extra.get('equityPercent', '-')}")
        print(f"  投资金额: {extra.get('investAmount', '-')}")
        print(f"  注册状态: {extra.get('registerStatus', '-')}")
        print(f"  行业: {extra.get('industry', '-')}")
        print(f"  标签: {', '.join(extra.get('tags', []))}")
        print()
