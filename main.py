import sys
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from utils import logger
from core import Engine
from spiders import TianyanchaSpider
from spiders.beianx_spider import get_company_by_icp
from spiders.tianyancha.search import search_company_id
from spiders.tianyancha.subsidiary import query_subsidiaries
from models import AssetType
from utils.exporter import export_results


def parse_args() -> Dict[str, Any]:
    args: Dict[str, Any] = {
        "name": None,
        "domain": None,
        "icp": None,
        "equity": None,
        "export": None,   # 导出格式：csv/excel
        "output": None,   # 自定义输出文件名
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
    print("  --equity      股权比例（控股公司筛选）")
    print("  --subsidiary  仅查询控股公司")
    print("  --export      导出格式（csv/excel）默认：xlsx")
    print("  --output      自定义输出文件名（如 result.xlsx）")
    print("\n示例：")
    print("  python main.py --name 字节跳动")
    print("  python main.py --name 腾讯 --export excel")
    print("  python main.py --name 小米 --subsidiary")
    print("  python main.py --name 小米 --subsidiary --equity 0.5")
    print("  python main.py --icp 京ICP备10046444号")
    print("  python main.py --icp 京ICP备10046444号 --export csv")
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


def query_subsidiaries_only(args: Dict[str, Any], folder_path: Path, timestamp: str):
    """仅查询控股公司并导出结果"""
    company_name = args["name"]
    equity_str = args.get("equity", "0")
    try:
        min_equity = float(equity_str)
    except ValueError:
        min_equity = 0.0

    # 获取 spider headers
    spider = TianyanchaSpider()
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


def main():
    args = parse_args()

    # 检查必要参数：name 或 icp 至少提供一个
    if not args["name"] and not args["icp"]:
        print_help()
        return

    # 如果提供了 icp 但没有 name，先通过备案号查询公司名
    if args["icp"] and not args["name"]:
        print(f"[+] 正在通过 ICP 备案号查询公司名: {args['icp']}")
        company_name = get_company_by_icp(args["icp"])
        if not company_name:
            print(f"[x] 未找到 ICP 备案号对应的公司: {args['icp']}")
            return
        args["name"] = company_name
        print(f"[+] 已获取公司名称: {company_name}\n")

    # 获取搜索关键词（用于创建文件夹）
    keyword = args["name"]

    # 创建输出文件夹
    folder_path, timestamp = setup_output_folder(keyword)
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

    # 正常资产查询流程（仅支持天眼查）
    engine = Engine()
    engine.register_spider(TianyanchaSpider())
    logger.info("使用天眼查平台查询")

    engine.run(args=args)
    results = engine.get_results()
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
        # 默认命名：公司名称_时间戳.扩展名
        safe_name = args["name"].replace(" ", "_").replace("/", "_")[:20]
        output_file = f"{safe_name}_{timestamp}.{export_format if export_format != 'excel' else 'xlsx'}"
        output_path = folder_path / output_file
        export_results(results, format=export_format, filename=str(output_path))

    logger.info("任务完成")
    print(f"\n[+] 日志已保存: {log_file}")


if __name__ == "__main__":
    main()
