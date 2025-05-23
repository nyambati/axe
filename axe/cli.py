import argparse
import logging
from .tree import tree
from .route_evaluator import evaluate
from .config_manager import render

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        prog="axe",
        description="Axe CLI tool for managing and troubleshooting prometheus alertmanager configurations",
    )
    subparsers = parser.add_subparsers()

    # Tree command
    tree_parser = subparsers.add_parser(
        "tree", help="Displays alertmanager configuration route tree"
    )
    tree_parser.add_argument("file_path", help="Path to the YAML file")
    tree_parser.set_defaults(func=tree)

    # Evaluate command
    evaluate_parser = subparsers.add_parser(
        "eval", help="Evaluates alertmanager configuration route tree"
    )
    evaluate_parser.add_argument("file_path", help="Path to the YAML file")
    evaluate_parser.add_argument("--alert", help="Alert to evaluate")
    evaluate_parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output"
    )
    evaluate_parser.set_defaults(func=evaluate)

    # Config command
    config_parser = subparsers.add_parser(
        "render", help="Renders alertmanager configuration"
    )
    config_parser.add_argument("file_path", help="Path to the YAML file")
    config_parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output"
    )
    config_parser.set_defaults(func=render)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
