from dataclasses import dataclass
from typing import Optional


@dataclass
class CompanyModel:
    """
    企业信息统一数据模型（所有爬虫必须输出该格式）
    字段说明：
    - 必选字段：name（企业名称）、source（数据来源，如 tianyancha/qcc）
    - 可选字段：为空时填 None，禁止用空字符串占位
    """
    # 必选字段
    name: str  # 企业全称（例：字节跳动有限公司）
    source: str  # 数据来源（例：tianyancha、qcc）

    # 可选字段（爬虫爬取到就填，爬不到填 None）
    legal_person: Optional[str] = None  # 法定代表人
    phone: Optional[str] = None  # 联系电话
    email: Optional[str] = None  # 联系邮箱
    address: Optional[str] = None  # 注册地址/经营地址
    status: Optional[str] = None  # 经营状态（例：存续、注销）
    credit_code: Optional[str] = None  # 统一社会信用代码


# 测试代码（验证数据模型是否可用）
if __name__ == "__main__":
    # 实例化一个测试企业数据
    test_company = CompanyModel(
        name="字节跳动有限公司",
        source="tianyancha",
        legal_person="张一鸣",
        phone="12345678901",
        credit_code="91110108MA0045N86B"
    )
    print("✅ 数据模型实例化成功！")
    print(test_company)