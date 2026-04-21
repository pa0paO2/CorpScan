import sys
from typing import Dict, Any, List
from utils import logger
from core import Engine
from spiders import BeianxSpider, TianyanchaSpider
from models import AssetType
from utils.exporter import export_results


def parse_args() -> Dict[str, Any]:
    args = {
        "name": None,
        "domain": None,
        "icp": None,
        "equity": None,
        "site": "all",
        "export": None,   # 导出格式：csv/excel
        "output": None    # 自定义输出文件名
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
        elif sys.argv[i] == "--site" and i+1 < len(sys.argv):
            args["site"] = sys.argv[i+1]
        elif sys.argv[i] == "--export" and i+1 < len(sys.argv):
            args["export"] = sys.argv[i+1].lower()
        elif sys.argv[i] == "--output" and i+1 < len(sys.argv):
            args["output"] = sys.argv[i+1]
    return args


def print_help():
    print("=" * 50)
    print("CorpScan - 企业资产收集工具")
    print("=" * 50)
    print("参数：")
    print("  --name      公司名称")
    print("  --domain    域名")
    print("  --icp       备案号")
    print("  --equity    股权比例")
    print("  --site      指定爬虫（tianyancha/beianx/all）默认：all")
    print("  --export    导出格式（csv/excel）默认：csv")
    print("  --output    自定义输出文件名（如 result.xlsx）")
    print("\n示例：")
    print("  python main.py --name 字节跳动 --site tianyancha")
    print("  python main.py --name 腾讯 --site all --export excel")
    print("  python main.py --name 小米 --export csv")
    print("  python main.py --name 小米 --output mi_assets.xlsx")
    print("  python main.py --icp 京ICP123 --site beianx")
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


def main():
    args = parse_args()
    if all(v is None for v in args.values()):
        print_help()
        return

    logger.info(f"启动参数：{args}")

    engine = Engine()
    site = args["site"]
    if site in ["tianyancha", "all"]:
        engine.register_spider(TianyanchaSpider())

    if site in ["beianx", "all"]:
        engine.register_spider(BeianxSpider())

    engine.run(args=args)
    results = engine.get_results()
    print_results_table(results)

    # 导出结果到文件（默认自动导出为 CSV）
    export_format = args.get("export") or "xlsx"
    output_file = args.get("output")

    # 如果指定了输出文件名，根据扩展名推断格式
    if output_file:
        if output_file.lower().endswith(".xlsx"):
            export_format = "excel"
        elif output_file.lower().endswith(".csv"):
            export_format = "csv"
        export_results(results, format=export_format, filename=output_file)
    else:
        # 默认自动导出（自动生成文件名）
        export_results(results, format=export_format)

    logger.info("任务完成")


if __name__ == "__main__":
    main()
