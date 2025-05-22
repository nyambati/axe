import argparse
import json
import yaml
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich import print  # Keep this for rich.print
import re


class Route:
    def __init__(
        self,
        data: Dict[str, Any],
        parent: Optional["Route"] = None,
        verbose: bool = False,
    ):
        self.receiver = data.get("receiver", "default")
        self.group_by = data.get("group_by", [])
        self.match = data.get("match", {})
        self.match_re = data.get("match_re", {})
        self.matchers = data.get("matchers", [])
        if parent is None:
            self.continue_flag = data.get("continue", True)
        else:
            self.continue_flag = data.get("continue", False)

        self.routes = [Route(r, self, verbose) for r in data.get("routes", [])]
        self.parent = parent
        self.verbose = verbose

    def print_verbose(self, message: str):
        if self.verbose:
            print(message)

    def matches_alert(self, alert_labels: Dict[str, str]) -> bool:
        """
        Checks if the current route matches the given alert based on its
        'match', 'match_re', and 'matchers' criteria.
        If 'verbose' is True, detailed matcher logs are printed.
        """
        # Check 'match' criteria (exact string match)
        for key, value in self.match.items():
            alert_value = alert_labels.get(key, "")
            if alert_value != value:
                return False

        # Check 'match_re' criteria (regex match)
        for key, pattern in self.match_re.items():
            alert_value = alert_labels.get(key, "")
            try:
                if not bool(re.search(pattern, alert_value)):
                    return False
            except re.error as e:
                print(
                    f"[red]Error: Invalid regex pattern '{pattern}' for label '{key}': {e}[/red]"
                )
                return False

        # Check 'matchers' criteria (parsed expressions)
        for matcher_str in self.matchers:
            if not self._evaluate_matcher_string(matcher_str, alert_labels):
                return False

        self.print_verbose("[green]✓[/green] All matchers matched successfully")

        return True

    def _evaluate_matcher_string(
        self, matcher_str: str, alert_labels: Dict[str, str]
    ) -> bool:
        """Evaluates a single Alertmanager matcher string (e.g., 'severity = "critical")."""
        match = re.match(
            r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*([=!~]+)\s*(.*)\s*$", matcher_str
        )
        if not match:
            self.print_verbose(
                f"[red]Invalid matcher format: '{matcher_str}'. Skipping.[/red]",
            )
            return False

        label, operator, pattern_or_value = match.groups()
        alert_value = alert_labels.get(label, "")

        # Remove quotes from value if present
        if pattern_or_value.startswith('"') and pattern_or_value.endswith('"'):
            pattern_or_value = pattern_or_value[1:-1]

        try:
            if operator == "=":
                result = alert_value == pattern_or_value
            elif operator == "!=":
                result = alert_value != pattern_or_value
            elif operator == "=~":
                result = bool(re.search(pattern_or_value, alert_value))
            elif operator == "!~":
                result = not bool(re.search(pattern_or_value, alert_value))
            else:
                self.print_verbose(
                    f"[red]Unknown operator '{operator}' in matcher: '{matcher_str}'. Skipping.[/red]",
                )
                return False
        except re.error as e:
            self.print_verbose(
                f"[red]Error: Invalid regex pattern '{pattern_or_value}' for label '{label}': {e}[/red]",
            )
            return False

        if result:  # Only log successful matches
            self.print_verbose(
                f'  [green]✓[/green] Matcher matched: [bold cyan]{label}[/bold cyan] {operator} [yellow]"{pattern_or_value}"[/yellow]',
            )
            self.print_verbose(
                f'    Label: [cyan]{label}[/cyan], Alert value: [yellow]"{alert_value}"[/yellow], Pattern: [yellow]"{pattern_or_value}"[/yellow]',
            )

        return result


class RouteEvaluator:
    def __init__(self, route_data: Dict[str, Any], verbose: bool = False):
        self.verbose = verbose
        self.root_route = Route(data=route_data, verbose=self.verbose)

    def evaluate_alert(self, alert_labels: Dict[str, str]) -> List[str]:
        matched_receivers = set()
        self._traverse_and_match_recursive(
            self.root_route, alert_labels, matched_receivers
        )
        return sorted(list(matched_receivers))

    def print_verbose(self, message: str):
        if self.verbose:
            print(message)

    def _traverse_and_match_recursive(
        self,
        current_route: Route,
        alert_labels: Dict[str, str],
        matched_receivers: set,
    ) -> bool:
        """
        Recursively traverses the routing tree. Returns True if this route (or one of its children)
        ultimately leads to a receiver being added *and* it doesn't have `continue: true` to its siblings.
        """
        # Print the route being evaluated

        self.print_verbose(
            f"[bold magenta]  Evaluating Route (Receiver: {current_route.receiver})[/bold magenta]",
        )
        if current_route.match or current_route.match_re or current_route.matchers:
            self.print_verbose(
                "[bold magenta]  Route Matchers Defined:[/bold magenta]",
            )
            if current_route.match:
                self.print_verbose(
                    f"    match: {current_route.match}",
                )
            if current_route.match_re:
                self.print_verbose(
                    f"    match_re: {current_route.match_re}",
                )
            if current_route.matchers:
                self.print_verbose(
                    f"    matchers: {current_route.matchers}",
                )
        else:
            self.print_verbose(
                "[bold magenta]  (No specific matchers, acts as catch-all for its children)[/bold magenta]",
            )
        self.print_verbose(
            f"[bold magenta]  Continue flag:[/bold magenta] {current_route.continue_flag}",
        )

        # Perform the match, passing verbose=True ONLY if this route matches
        route_matched = current_route.matches_alert(alert_labels)

        if not route_matched:
            self.print_verbose(
                f"[bold red]Route {current_route.receiver} did NOT match alert. Moving to next sibling/parent fallback.[/bold red]",
            )
            return False

        print(f"[bold green]Route {current_route.receiver} MATCHED alert.[/bold green]")

        child_handled_and_stopped = False
        for child_route in current_route.routes:
            # We're entering a child route, print a clear indicator
            self.print_verbose(
                f"\n[bold blue]Descending to Child Route (Receiver: {child_route.receiver})[/bold blue]",
            )
            if self._traverse_and_match_recursive(
                child_route, alert_labels, matched_receivers
            ):
                # A child (or grandchild etc.) handled the alert.
                # If that child's branch does *not* continue, then this current route's
                # receiver is suppressed.
                if not child_route.continue_flag:
                    print(
                        f"[bold yellow]  Child Route {child_route.receiver} handled alert and has continue: false.[/bold yellow]"
                    )
                    print(
                        "[bold yellow]  Stopping further evaluation of THIS branch's siblings.[/bold yellow]"
                    )
                    child_handled_and_stopped = True
                    break  # Stop looking at siblings of the child if it handled and stopped
                else:
                    print(
                        f"[bold purple]  Child Route {child_route.receiver} handled alert but has continue: true.[/bold purple]"
                    )
                    print(
                        "[bold purple]  Parent's receiver still considered, and parent's siblings will be checked if current route has continue: true. [/bold purple]"
                    )

        if not child_handled_and_stopped:
            # If no child handled and stopped, or if children handled but allowed continuation,
            # then this route's receiver is relevant.
            print(f"[bold green]Adding receiver: {current_route.receiver}[/bold green]")
            matched_receivers.add(current_route.receiver)
        else:
            print(
                f"[bold yellow]Skipping receiver {current_route.receiver} because a child handled and stopped.[/bold yellow]"
            )

        return True


def parse_alertmanager_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    if "route" in config:
        return config["route"]
    else:
        raise ValueError("No 'route' configuration found in the Alertmanager config.")


def evaluate(args: argparse.Namespace) -> int:
    try:
        # Parse configuration
        route_config = parse_alertmanager_config(args.file_path)

        # Parse alert
        if args.alert.endswith(".json"):
            with open(args.alert, "r") as f:
                alert_data_string = f.read().strip()
            alert_labels = json.loads(alert_data_string)
        print(alert_labels)
        # Create evaluator and evaluate alert
        evaluator = RouteEvaluator(route_data=route_config, verbose=args.verbose)

        console = Console()
        console.print("[bold underline]Alert Evaluation Process[/bold underline]")
        console.print("\n[bold]Alert Labels:[/bold]")
        for key, value in alert_labels.items():
            console.print(f"  [cyan]{key}[/cyan]: [yellow]{value}[/yellow]")
        console.print("\n" + "-" * 70 + "\n")

        matched_receivers = evaluator.evaluate_alert(alert_labels)

        # Print results
        console.print("\n" + "-" * 70 + "\n")
        console.print("[bold]Final Alert Evaluation Results[/bold]")
        console.print("\nMatched Receivers:")
        if matched_receivers:
            for receiver in matched_receivers:
                console.print(f"  [green]✓[/green] [bold blue]{receiver}[/bold blue]")
            console.print("\n" + "-" * 70 + "\n")
        else:
            console.print(
                "  [red]No matching receivers found (check default receiver or matchers)[/red]"
            )

    except FileNotFoundError as e:
        print(f"[red]Error: File not found: {e.filename}[/red]")
        return 1
    except yaml.YAMLError as e:
        print(f"[red]Error parsing YAML: {str(e)}[/red]")
        return 1
    except ValueError as e:
        print(f"[red]Configuration Error: {str(e)}[/red]")
        return 1
    except Exception as e:
        print(f"[red]An unexpected error occurred: {type(e).__name__}: {str(e)}[/red]")
        return 1

    return 0
