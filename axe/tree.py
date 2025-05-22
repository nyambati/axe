import argparse
import yaml
from rich.tree import Tree
from rich import print
from typing import Dict, Any


class Route:
    def __init__(self, data: Dict[str, Any], parent: "Route" = None):
        self.receiver = data.get("receiver", "")
        self.group_by = data.get("group_by", [])
        self.match = data.get("match", {})
        self.match_re = data.get("match_re", {})
        self.matchers = data.get("matchers", [])
        self.continue_flag = data.get("continue", False)
        self.group_wait = data.get("group_wait", "")
        self.group_interval = data.get("group_interval", "")
        self.repeat_interval = data.get("repeat_interval", "")
        self.routes = [Route(r, self) for r in data.get("routes", [])]
        self.parent = parent

    def to_tree(self, tree: Tree) -> None:
        # Add the route node with receiver color
        route_node = tree.add(f"[bold blue]{self.receiver}[/bold blue]")

        # Add criteria with different colors
        if self.group_by:
            route_node.add(
                f"[bold green]Group By:[/bold green] {'[green]'.join(self.group_by)}"
            )

        if self.match:
            match_node = route_node.add("[bold yellow]Match[/bold yellow]")
            for k, v in self.match.items():
                match_node.add(f"[yellow]{k} = {v}[/yellow]")

        if self.match_re:
            match_re_node = route_node.add("[bold magenta]Match RE[/bold magenta]")
            for k, v in self.match_re.items():
                match_re_node.add(f"[magenta]{k} =~ {v}[/magenta]")

        if self.matchers:
            matchers_node = route_node.add("[bold cyan]Matchers[/bold cyan]")
            for matcher in self.matchers:
                matchers_node.add(f"[cyan]{matcher}[/cyan]")

        if self.continue_flag:
            route_node.add("[bold green]Continue: true[/bold green]")

        # Add intervals with different colors
        if self.group_wait:
            route_node.add(
                f"[bold yellow]Wait:[/bold yellow] [yellow]{self.group_wait}[/yellow]"
            )

        if self.group_interval:
            route_node.add(
                f"[bold yellow]Group Interval:[/bold yellow] [yellow]{self.group_interval}[/yellow]"
            )

        if self.repeat_interval:
            route_node.add(
                f"[bold yellow]Repeat Interval:[/bold yellow] [yellow]{self.repeat_interval}[/yellow]"
            )

        # Add child routes
        for route in self.routes:
            route.to_tree(route_node)


def parse_alertmanager_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


def tree(args: argparse.Namespace) -> int:
    try:
        config = parse_alertmanager_config(args.file_path)

        # Find the route configuration
        root_route = None
        if "route" in config:
            root_route = Route(config["route"])

        if root_route:
            tree = Tree("[bold]Alertmanager Route Tree[/bold]")
            root_route.to_tree(tree)
            print(tree)
        else:
            print("[red]No route configuration found in the YAML file[/red]")
            return 1

    except FileNotFoundError:
        print(f"[red]Error: Config file not found: {args.file_path}[/red]")
        return 1
    except yaml.YAMLError as e:
        print(f"[red]Error parsing YAML: {str(e)}[/red]")
        return 1
    return 0
