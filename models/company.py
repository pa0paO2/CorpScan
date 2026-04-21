from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class AssetType(Enum):
    """资产类型枚举"""

    WEBSITE = "备案网站"
    APP = "移动应用"
    MINIPROGRAM = "小程序"
    PUBLIC_ACCOUNT = "公众号"
    WEIBO = "微博账号"
    DOUYIN = "抖音账号"
    TIKTOK = "TikTok账号"


@dataclass
class CompanyModel:
    """
    企业信息统一数据模型（所有爬虫必须输出该格式）
    字段说明：
    - 必选字段：name（企业名称）、source（数据来源）
    - 可选字段：为空时填 None，禁止用空字符串占位
    """
    # 必选字段
    name: str  # 企业全称（例：字节跳动有限公司）
    source: str  # 数据来源（例：beianx、tianyancha）

    # 基础信息
    legal_person: Optional[str] = None  # 法定代表人
    phone: Optional[str] = None  # 联系电话
    email: Optional[str] = None  # 联系邮箱
    address: Optional[str] = None  # 注册地址/经营地址
    status: Optional[str] = None  # 经营状态（例：存续、注销）
    credit_code: Optional[str] = None  # 统一社会信用代码

    # 网站备案信息
    icp_number: Optional[str] = None  # ICP备案号
    domain: Optional[str] = None  # 域名/网址
    site_name: Optional[str] = None  # 网站名称
    asset_type: Optional[str] = None  # 资产类型（使用 AssetType 枚举值）

    # APP信息
    app_name: Optional[str] = None  # APP名称
    app_version: Optional[str] = None  # APP版本
    app_package: Optional[str] = None  # APP包名

    # 小程序信息
    miniapp_name: Optional[str] = None  # 小程序名称
    miniapp_id: Optional[str] = None  # 小程序ID

    # 社交媒体信息
    social_account: Optional[str] = None  # 社交账号名
    social_id: Optional[str] = None  # 社交账号ID
    followers_count: Optional[int] = None  # 粉丝数

    # 扩展字段（用于存储其他额外信息）
    extra: dict = field(default_factory=dict)


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
