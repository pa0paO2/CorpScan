import sys
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from utils import logger
from core import Engine
from spiders import TianyanchaSpider
from spiders.beianx_spider import get_company_by_icp  # 仅用于ICP反查公司名
from spiders.tianyancha.search import search_company_id, search_company
from spiders.tianyancha.subsidiary import query_subsidiaries
from spiders.tianyancha.website import query_all_websites
from spiders.tianyancha.app import query_all_apps
from spiders.tianyancha.miniapp import query_all_miniapps
from models import AssetType
from utils.exporter import export_results


def parse_args() -> Dict[str, Any]:
    args: Dict[str, Any] = {
        "name": None,
        "domain": None,
        "icp": None,
        "equity": None,
        "source": "tyc",   # 数据来源：tyc(天眼查)/beianx(备案查询)
        "export": None,    # 导出格式：csv/excel
        "output": None,    # 自定义输出文件名
        "subsidiary": False  # 仅查询控股公司
    }

    for i in range(len(sys.argv)):
        if sys.argv[i] == "--name" and i+1 < len(sys.argv):
            args["name"] = sys.argv[i+1]
        elif sys.argv[i] == "--domain" and i+1 < len(sys.argv):
            args["domain"] = sys.argv[i+1]
        elif sys.argv[i] == "--icp" and i+1 < len(sys.argv):
            args["icp"] = sys.argv[i+1]
        elif sys.argv[i] == "--equity" and i+1 < len(sys.argv):
            args["equity"] = sys.argv[i+1]
        elif sys.argv[i] == "--source" and i+1 < len(sys.argv):
            args["source"] = sys.argv[i+1].lower()
        elif sys.argv[i] == "--export" and i+1 < len(sys.argv):
            args["export"] = sys.argv[i+1].lower()
        elif sys.argv[i] == "--output" and i+1 < len(sys.argv):
            args["output"] = sys.argv[i+1]
        elif sys.argv[i] == "--subsidiary":
            args["subsidiary"] = True
    return args


def print_help():
    print("=" * 50)
    print("CorpScan - 企业资产收集工具")
    print("=" * 50)
    print("参数：")
    print("  --name        公司名称")
    print("  --domain      域名")
    print("  --icp         备案号（自动查公司名）")
    print("  --source      数据来源：tyc(天眼查,默认)，后续将支持更多平台")
    print("  --equity      股权比例（控股公司筛选，仅tyc支持）")
    print("  --subsidiary  仅查询控股公司（仅tyc支持）")
    print("  --export      导出格式（csv/excel）默认：xlsx")
    print("  --output      自定义输出文件名（如 result.xlsx）")
    print("\n示例：")
    print("  python main.py --name 字节跳动")
    print("  python main.py --name 腾讯 --source tyc --export excel")
    print("  python main.py --name 小米 --subsidiary --equity 0.5")
    print("  python main.py --icp 京ICP备10046444号")
    print("=" * 50)


def truncate(s: str, width: int) -> str:
    """截断字符串到指定宽度"""
    if not s:
        return "-"
    if len(s) <= width:
        return s
    return s[:width-3] + "..."


def print_results_table(results: List):
    """以表格格式打印资产结果（类似MySQL查询输出）"""
    if not results:
        print("\n[!] 未找到任何资产信息\n")
        return

    print(f"\n[+] 共找到 {len(results)} 条资产记录\n")

    # 按资产类型分组
    grouped = {}
    for item in results:
        t = item.asset_type or "未知"
        if t not in grouped:
            grouped[t] = []
        grouped[t].append(item)

    # 按类型分别输出表格
    for asset_type, items in grouped.items():
        print(f"\n【{asset_type}】共 {len(items)} 条")
        print("-" * 80)

        if asset_type == AssetType.WEBSITE.value:
            # 网站备案表格
            print(f"{'序号':<4} {'网站名称':<30} {'域名':<30} {'备案号':<20}")
            print("-" * 80)
            for idx, item in enumerate(items, 1):
                name = truncate(item.site_name, 28)
                domain = truncate(item.domain, 28)
                icp = truncate(item.icp_number, 18)
                print(f"{idx:<4} {name:<30} {domain:<30} {icp:<20}")

        elif asset_type == AssetType.APP.value:
            # APP表格
            print(f"{'序号':<4} {'APP名称':<30} {'类型':<8} {'分类':<15}")
            print("-" * 80)
            for idx, item in enumerate(items, 1):
                name = truncate(item.app_name, 28)
                app_type = truncate(item.extra.get("appType", "应用") if item.extra else "应用", 6)
                classes = truncate(item.extra.get("classes", "-") if item.extra else "-", 13)
                print(f"{idx:<4} {name:<30} {app_type:<8} {classes:<15}")

        elif asset_type == AssetType.MINIPROGRAM.value:
            # 小程序表格
            print(f"{'序号':<4} {'小程序名称':<30} {'备案号':<25} {'审核日期':<12}")
            print("-" * 80)
            for idx, item in enumerate(items, 1):
                name = truncate(item.miniapp_name, 28)
                icp = truncate(item.icp_number, 23)
                date = truncate(item.extra.get("examineDate", "-") if item.extra else "-", 10)
                print(f"{idx:<4} {name:<30} {icp:<25} {date:<12}")

        else:
            # 通用表格
            print(f"{'序号':<4} {'名称':<35} {'来源':<10}")
            print("-" * 80)
            for idx, item in enumerate(items, 1):
                name = truncate(item.name, 33)
                print(f"{idx:<4} {name:<35} {item.source:<10}")

        print()


def setup_output_folder(keyword: str) -> tuple[Path, str]:
    """
    创建输出文件夹（格式：output/关键词_YYYYMMDD_HHMMSS）
    返回：(文件夹路径, 时间戳字符串)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{keyword}_{timestamp}"
    folder_path = Path("output") / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)
    return folder_path, timestamp


def setup_file_logger(folder_path: Path):
    """设置文件日志处理器，将日志写入指定文件夹"""
    import logging
    log_file = folder_path / "run.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return log_file


def create_spider(source: str):
    """
    根据数据源创建对应的 spider 实例
    :param source: 数据源标识 (tyc)
    :return: Spider 实例
    """
    if source == "tyc":
        return TianyanchaSpider()
    else:
        logger.warning(f"未知数据源: {source}，使用默认天眼查(tyc)")
        return TianyanchaSpider()


def query_subsidiaries_by_source(args: Dict[str, Any], spider) -> tuple:
    """
    根据数据源查询控股公司和资产（仅tyc支持）
    :return: (subsidiaries列表, sub_assets列表, full_company_name, company_id)
    """
    source = args.get("source", "tyc")
    keyword = args["name"]

    if source != "tyc":
        # 目前仅tyc支持控股公司查询
        logger.info(f"数据源 {source} 暂不支持控股公司查询")
        return [], [], keyword, None

    # tyc 天眼查逻辑
    equity_str = args.get("equity", "0")
    try:
        min_equity = float(equity_str)
    except ValueError:
        min_equity = 0.0

    headers = spider.custom_headers

    print(f"[+] 正在搜索公司: {keyword}")
    search_result = search_company(keyword, headers)
    if not search_result:
        print(f"[x] 未找到公司: {keyword}")
        return [], [], keyword

    company_id, full_company_name = search_result
    print(f"[+] 已匹配到公司: {full_company_name} (ID: {company_id})")
    print(f"[+] 正在查询控股公司（股权>={min_equity}）...")

    # 查询控股公司
    subsidiaries = query_subsidiaries(company_id, full_company_name, headers, min_equity)
    logger.info(f"[控股公司] 获取 {len(subsidiaries)} 条（股权>={min_equity}）")
    print(f"[+] 找到 {len(subsidiaries)} 家控股公司")

    # 过滤有效子公司并查询资产
    sub_assets = []
    active_subs = [s for s in subsidiaries
                   if not any(status in s.extra.get("registerStatus", "")
                              for status in ["注销", "吊销", "撤销", "停业", "清算"])]
    print(f"[+] 其中 {len(active_subs)} 家状态有效")

    if active_subs:
        print(f"[+] 开始查询子公司资产...")
        sub_assets = query_subsidiary_assets(active_subs, headers, full_company_name)
        print(f"[+] 子公司资产查询完成，共 {len(sub_assets)} 条记录")

    return subsidiaries, sub_assets, full_company_name, company_id


def query_subsidiaries_only(args: Dict[str, Any], folder_path: Path, timestamp: str):
    """仅查询控股公司并导出结果（仅tyc支持）"""
    source = args.get("source", "tyc")

    if source != "tyc":
        print(f"[x] 数据源 {source} 暂不支持控股公司查询")
        return

    company_name = args["name"]
    equity_str = args.get("equity", "0")
    try:
        min_equity = float(equity_str)
    except ValueError:
        min_equity = 0.0

    # 根据source创建spider
    spider = create_spider(source)
    headers = spider.custom_headers

    # 搜索公司ID
    print(f"[+] 正在搜索公司: {company_name}")
    company_id = search_company_id(company_name, headers)
    if not company_id:
        print(f"[x] 未找到公司: {company_name}")
        return []

    print(f"[+] 已获取公司ID: {company_id}")

    # 查询控股公司
    print(f"[+] 正在查询控股公司（股权>={min_equity}）...")
    results = query_subsidiaries(company_id, company_name, headers, min_equity)
    print(f"[+] 找到 {len(results)} 家控股公司")

    # 打印结果表格
    if results:
        print(f"\n[+] 共找到 {len(results)} 条控股公司记录\n")
        print(f"{'序号':<4} {'公司名称':<35} {'股权比例':<12} {'注册状态':<10}")
        print("-" * 80)
        for idx, item in enumerate(results, 1):
            name = item.name[:33] + "..." if len(item.name) > 33 else item.name
            equity = item.extra.get("equityPercent", "-")
            status = item.extra.get("registerStatus", "-")[:8]
            print(f"{idx:<4} {name:<35} {equity:<12} {status:<10}")
        print()

    # 导出结果
    export_format = args.get("export") or "xlsx"
    output_file = args.get("output")

    if not output_file:
        # 默认命名：公司名称_时间戳.扩展名
        safe_name = company_name.replace(" ", "_").replace("/", "_")[:20]
        output_file = f"{safe_name}_{timestamp}.{export_format if export_format != 'excel' else 'xlsx'}"

    output_path = folder_path / output_file
    export_results(results, format=export_format, filename=str(output_path))

    return results


def query_subsidiary_assets(subsidiaries: List, headers: dict, parent_name: str) -> List:
    """
    查询子公司的资产（网站、APP、小程序）
    过滤掉状态为注销的子公司
    """
    all_results = []
    total_websites, total_apps, total_miniapps = 0, 0, 0

    for sub in subsidiaries:
        # 获取子公司ID
        sub_id = sub.extra.get("companyId")
        if not sub_id:
            continue

        # 查询子公司资产
        try:
            # 网站
            websites = query_all_websites(sub_id, sub.name, headers, page_size=10)
            for site in websites:
                site.extra["parentCompany"] = parent_name
                site.extra["subsidiaryName"] = sub.name
                site.extra["equityPercent"] = sub.extra.get("equityPercent", "-")
            all_results.extend(websites)
            total_websites += len(websites)

            # APP
            apps = query_all_apps(sub_id, sub.name, headers, page_size=10)
            for app in apps:
                app.extra["parentCompany"] = parent_name
                app.extra["subsidiaryName"] = sub.name
                app.extra["equityPercent"] = sub.extra.get("equityPercent", "-")
            all_results.extend(apps)
            total_apps += len(apps)

            # 小程序
            miniapps = query_all_miniapps(sub_id, sub.name, headers, page_size=10)
            for mini in miniapps:
                mini.extra["parentCompany"] = parent_name
                mini.extra["subsidiaryName"] = sub.name
                mini.extra["equityPercent"] = sub.extra.get("equityPercent", "-")
            all_results.extend(miniapps)
            total_miniapps += len(miniapps)

            # 只有找到资产时才输出日志
            if websites or apps or miniapps:
                logger.info(f"[{sub.name}] 网站:{len(websites)} APP:{len(apps)} 小程序:{len(miniapps)}")

        except Exception as e:
            logger.warning(f"子公司资产查询失败 {sub.name}: {e}")

    # 汇总输出
    if all_results:
        logger.info(f"子公司资产汇总: 网站{total_websites} APP{total_apps} 小程序{total_miniapps} 总计{len(all_results)}")

    return all_results


def main():
    args = parse_args()

    # 检查必要参数：name 或 icp 至少提供一个
    if not args["name"] and not args["icp"]:
        print_help()
        return

    # 保存原始搜索关键词（用于创建文件夹）
    # 如果是ICP查询，用ICP号；否则用公司名
    folder_keyword = args["icp"] if args["icp"] else args["name"]

    # 如果提供了 icp 但没有 name，先通过备案号查询公司名
    if args["icp"] and not args["name"]:
        print(f"[+] 正在通过 ICP 备案号查询公司名: {args['icp']}")
        company_name = get_company_by_icp(args["icp"])
        if not company_name:
            print(f"[x] 未找到 ICP 备案号对应的公司: {args['icp']}")
            return
        args["name"] = company_name
        print(f"[+] 已获取公司名称: {company_name}\n")

    # 创建输出文件夹（使用原始关键词）
    folder_path, timestamp = setup_output_folder(folder_keyword)
    print(f"[+] 输出文件夹: {folder_path}")

    # 设置文件日志
    log_file = setup_file_logger(folder_path)
    logger.info(f"启动参数：{args}")
    logger.info(f"输出文件夹: {folder_path}")

    # 如果是仅查询控股公司模式
    if args.get("subsidiary"):
        query_subsidiaries_only(args, folder_path, timestamp)
        logger.info("任务完成")
        print(f"\n[+] 日志已保存: {log_file}")
        return

    # 根据 source 创建对应的 spider
    source = args.get("source", "tyc")
    spider = create_spider(source)
    logger.info(f"使用数据源: {source}")

    subsidiaries = []
    sub_assets = []  # 保存子公司资产，避免重复查询
    full_company_name = args["name"]
    company_id = None

    # 如果指定了 equity 但没有指定 subsidiary，查询子公司资产（仅tyc支持）
    if args.get("equity") and not args.get("subsidiary") and source == "tyc":
        subs_result = query_subsidiaries_by_source(args, spider)
        subsidiaries, sub_assets, full_company_name, company_id = subs_result

        # 更新args以便spider使用
        args["name"] = full_company_name
        args["company_id"] = company_id
        args["subsidiaries"] = subsidiaries

    # 正常资产查询流程
    engine = Engine()

    # 如果已获取完整公司名称，更新args
    if full_company_name != args["name"]:
        args["name"] = full_company_name

    # 使用同一个spider实例
    engine.register_spider(spider)
    logger.info(f"启动 {source} 爬虫查询")

    engine.run(args=args)
    results = engine.get_results()

    # 合并子公司资产到结果中（使用之前保存的结果，避免重复查询）
    if sub_assets:
        # 检查 results 中是否已有子公司资产（避免重复添加）
        existing_sub_names = {item.name for item in results if item.extra.get("subsidiaryName")}
        new_sub_assets = [item for item in sub_assets if item.name not in existing_sub_names]
        if new_sub_assets:
            results.extend(new_sub_assets)
            logger.info(f"已合并 {len(new_sub_assets)} 条子公司资产")

    print_results_table(results)

    # 导出结果到文件
    export_format = args.get("export") or "xlsx"
    output_file = args.get("output")

    # 如果指定了输出文件名
    if output_file:
        if output_file.lower().endswith(".xlsx"):
            export_format = "excel"
        elif output_file.lower().endswith(".csv"):
            export_format = "csv"
        output_path = folder_path / output_file
        export_results(results, format=export_format, filename=str(output_path))
    else:
        # 默认命名：完整公司名称_时间戳.扩展名
        safe_name = full_company_name.replace(" ", "_").replace("/", "_")[:30]
        output_file = f"{safe_name}_{timestamp}.{export_format if export_format != 'excel' else 'xlsx'}"
        output_path = folder_path / output_file
        export_results(results, format=export_format, filename=str(output_path))

    logger.info("任务完成")
    print(f"\n[+] 日志已保存: {log_file}")


if __name__ == "__main__":
    main()
