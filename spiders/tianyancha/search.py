
"""天眼查爬虫 - 模糊搜索模块"""

from urllib.parse import quote
from core import downloader
from utils import logger
from typing import Optional, List, Dict, Any
from datetime import datetime
from difflib import SequenceMatcher


def _calc_similarity(a: str, b: str) -> float:
    """计算两个字符串的相似度 (0.0 ~ 1.0)"""
    if not a or not b:
        return 0.0
    a, b = a.lower().strip(), b.lower().strip()
    # 完全匹配直接返回 1.0
    if a == b:
        return 1.0
    # 包含关系给予较高权重
    if a in b or b in a:
        return 0.9
    return SequenceMatcher(None, a, b).ratio()

def search_company_id(keyword: str, headers: dict) -> Optional[str]:
    """
    通过公司名称模糊搜索获取公司ID
    :param keyword: 公司名称
    :param headers: 请求头
    :return: 公司ID，失败返回None
    """
    timestamp = int(datetime.now().timestamp() * 1000)
    url = f"https://capi.tianyancha.com/cloud-tempest/search/suggest/company/main?_={timestamp}"

    try:
        json_data = {
            "keyword": keyword,
            # "pageNum": 1,
            # "pageSize": 10,
            # "type": 1,
        }
        resp = downloader.post(url, json_data=json_data, headers=headers)
        if resp.status_code != 200:
            logger.error(f"模糊搜索失败，状态码：{resp.status_code}")
            return None

        data = resp.json()

        if data.get("state") == "ok" and data.get("data"):
            # 注意：实际返回的字段名是 companySuggestList
            company_list = data["data"].get("companySuggestList", [])
            if company_list:
                # 计算每个结果与输入关键词的相似度，选择最匹配的
                best_match = None
                best_score = -1.0

                for company in company_list:
                    # 使用 comName（纯净名称），name 字段包含 <em> 高亮标签
                    com_name = company.get("comName", "")
                    match_type = company.get("matchType", "")
                    similarity = _calc_similarity(keyword, com_name)

                    # 名称匹配给予更高权重，曾用名/品牌次之
                    if match_type == "名称":
                        similarity = min(1.0, similarity * 1.1)
                    elif match_type in ["曾用名", "品牌"]:
                        similarity = min(1.0, similarity * 1.05)

                    logger.debug(f"匹配: {com_name} ({match_type}) -> 相似度: {similarity:.3f}")

                    if similarity > best_score:
                        best_score = similarity
                        best_match = company

                if best_match and best_score > 0.3:  # 相似度阈值，避免完全无关的结果
                    company_id = best_match.get("id")
                    matched_name = best_match.get("comName", "")
                    match_type = best_match.get("matchType", "")
                    logger.info(f"模糊搜索成功: {matched_name} (ID: {company_id}, 相似度: {best_score:.3f}, 匹配类型: {match_type})")
                    return str(company_id)
                else:
                    logger.warning(f"搜索结果与输入关键词相似度过低，放弃匹配")

        logger.warning(f"未找到公司: {keyword}")
        return None



    except Exception as e:
        logger.error(f"模糊搜索异常: {str(e)}")
        return None


if __name__ == "__main__":
    from spiders.tianyancha.spider import TianyanchaSpider

    spider = TianyanchaSpider()
    test_keyword = "小米"

    company_id = search_company_id(test_keyword, spider.custom_headers)
    if company_id:
        print(f"搜索成功: {test_keyword} -> ID: {company_id}")
    else:
        print(f"未找到公司: {test_keyword}")
