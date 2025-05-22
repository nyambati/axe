import argparse
import logging
import os
import yaml
from .tree import tree

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
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
