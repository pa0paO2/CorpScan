import sys
from typing import Dict, Any
from utils import logger
from core import Engine
from spiders import BaiduSpider, BeianxSpider

def parse_args() -> Dict[str, Any]:
    args = {
        "name": None,
        "domain": None,
        "icp": None,
        "equity": None,
        "site": "all"  # 默认全部
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
    print("  --site      指定爬虫（baidu/beianx/all）默认：all")
    print("\n示例：")
    print("  python main.py --name 字节跳动 --site beianx")
    print("  python main.py --name 腾讯 --site all")
    print("  python main.py --icp 京ICP123 --site beianx")
    print("=" * 50)

def main():
    args = parse_args()
    if all(v is None for v in args.values()):
        print_help()
        return

    logger.info(f"启动参数：{args}")

    # ======================
    # 根据 --site 自动注册爬虫
    # ======================
    engine = Engine()
    site = args["site"]

    if site in ["baidu", "all"]:
        engine.register_spider(BaiduSpider())

    if site in ["beianx", "all"]:
        engine.register_spider(BeianxSpider())

    # 启动
    engine.run(args=args)

    # 打印结果
    print("\n[+] 最终结果：\n")
    for item in engine.get_results():
        print(f"公司：{item.name}")
        print(f"来源：{item.source}")
        print(f"域名：{item.domain}")
        print(f"备案号：{item.icp_number}")
        print("-" * 40)

    logger.info("任务完成")

if __name__ == "__main__":
    main()