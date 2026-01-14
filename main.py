"""
Manus PPT Generator - 主入口
"""

import argparse
import sys
from pathlib import Path

from src.services import PPTGenerator
from src.utils.logger import setup_logger, get_logger


def main():
    """主函数"""
    setup_logger()
    logger = get_logger(__name__)

    parser = argparse.ArgumentParser(
        description="Manus PPT Generator - 自动生成 PPT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --topic "人工智能发展趋势"
  python main.py --topic "Q4销售报告" --audience "管理层" --slides 10
  python main.py --topic "产品介绍" --style "简约商务风" --files data.pdf
        """,
    )

    parser.add_argument(
        "--topic",
        "-t",
        required=True,
        help="PPT 主题",
    )

    parser.add_argument(
        "--audience",
        "-a",
        help="目标受众",
    )

    parser.add_argument(
        "--slides",
        "-s",
        type=int,
        help="页数",
    )

    parser.add_argument(
        "--style",
        help="风格描述（如：简约商务风、科技感、学术风格）",
    )

    parser.add_argument(
        "--files",
        "-f",
        nargs="+",
        help="参考文件路径（支持多个）",
    )

    parser.add_argument(
        "--output",
        "-o",
        help="输出文件名",
    )

    args = parser.parse_args()

    logger.info("Starting PPT generation...")

    try:
        generator = PPTGenerator()

        output_path = generator.generate(
            topic=args.topic,
            audience=args.audience,
            slides_count=args.slides,
            style=args.style,
            reference_files=args.files,
            output_filename=args.output,
        )

        print(f"\n✅ PPT 生成成功！")
        print(f"📁 文件路径: {output_path}")

    except ValueError as e:
        logger.error(f"配置错误: {e}")
        print(f"\n❌ 配置错误: {e}")
        print("请确保已配置 MANUS_API_KEY 环境变量")
        sys.exit(1)

    except TimeoutError as e:
        logger.error(f"超时: {e}")
        print(f"\n❌ 任务超时: {e}")
        sys.exit(1)

    except RuntimeError as e:
        logger.error(f"运行错误: {e}")
        print(f"\n❌ 生成失败: {e}")
        sys.exit(1)

    except Exception as e:
        logger.exception(f"未知错误: {e}")
        print(f"\n❌ 未知错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

