import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from axe.tree import Route, tree
from rich.tree import Tree
from unittest.mock import patch, mock_open, MagicMock


def test_route_creation():
    """Test Route object creation with basic configuration."""
    config = {
        "receiver": "default-receiver",
        "group_by": ["alertname"],
        "routes": [
            {"receiver": "critical-receiver", "match": {"severity": "critical"}}
        ],
    }

    route = Route(config)
    assert route.receiver == "default-receiver"
    assert route.group_by == ["alertname"]
    assert len(route.routes) == 1
    assert route.routes[0].receiver == "critical-receiver"


def test_route_to_tree():
    """Test conversion of Route to rich.Tree."""
    config = {
        "receiver": "default-receiver",
        "group_by": ["alertname"],
        "match": {"severity": "warning"},
        "match_re": {"instance": ".*"},
        "matchers": [{"name": "region", "value": "us-east-1", "isRegex": False}],
        "continue": True,
        "group_wait": "30s",
        "group_interval": "5m",
        "repeat_interval": "3h",
        "routes": [
            {"receiver": "critical-receiver", "match": {"severity": "critical"}}
        ],
    }

    route = Route(config)
    tree = Tree("Test")
    route.to_tree(tree)

    # We can't directly compare the tree output, but we can check the structure
    assert len(tree.children) == 1  # Main route node
    assert len(tree.children[0].children) > 0  # Should have multiple children
    assert len(tree.children[0].children[-1].children) == 1  # Child route


def test_tree_command_success():
    """Test tree command with valid configuration."""
    config_yaml = """
    route:
      receiver: 'default-receiver'
      group_by: ['alertname']
      routes:
      - receiver: 'critical-receiver'
        match:
          severity: 'critical'
    """

    mock_args = MagicMock()
    mock_args.file_path = "test.yaml"

    with patch("builtins.open", mock_open(read_data=config_yaml)):
        with patch("axe.tree.print") as mock_print:
            exit_code = tree(mock_args)
            assert exit_code == 0
            mock_print.assert_called_once()


def test_tree_command_file_not_found():
    """Test tree command with non-existent file."""
    mock_args = MagicMock()
    mock_args.file_path = "nonexistent.yaml"

    with patch("builtins.open", mock_open()) as mock_file:
        mock_file.side_effect = FileNotFoundError
        with patch("axe.tree.print") as mock_print:
            exit_code = tree(mock_args)
            assert exit_code == 1
            mock_print.assert_called_once_with(
                "[red]Error: Config file not found: nonexistent.yaml[/red]"
            )


def test_tree_command_yaml_error():
    """Test tree command with invalid YAML."""
    mock_args = MagicMock()
    mock_args.file_path = "invalid.yaml"

    with patch("builtins.open", mock_open(read_data="invalid:yaml")):
        with patch("axe.tree.print") as mock_print:
            exit_code = tree(mock_args)
            assert exit_code == 1
            mock_print.assert_called_once_with(
                "[red]No route configuration found in the YAML file[/red]"
            )


def test_route_tree_structure():
    """Test the core logic of route tree visualization."""
    # Create a route with various configurations
    data = {
        "receiver": "default",
        "group_by": ["alertname"],
        "match": {"severity": "critical"},
        "match_re": {"job": ".*"},
        "continue": True,
        "routes": [{"receiver": "email"}],
    }

    route = Route(data)
    tree = Tree("Root")
    route.to_tree(tree)

    # Verify the tree structure
    assert len(tree.children) == 1  # One root route
    root_node = tree.children[0]
    assert "default" in str(root_node.label)  # Receiver is displayed correctly

    # Verify child nodes exist for different configurations
    assert any("Group By" in str(child.label) for child in root_node.children)
    assert any("Match" in str(child.label) for child in root_node.children)
    assert any("Match RE" in str(child.label) for child in root_node.children)
    assert any("Continue" in str(child.label) for child in root_node.children)
    assert any(
        "email" in str(child.label) for child in root_node.children
    )  # Nested route

    # Verify the continue flag is properly displayed
    continue_node = next(
        (c for c in root_node.children if "Continue" in str(c.label)), None
    )
    assert continue_node is not None
    assert "true" in str(continue_node.label)

    # Verify nested route structure
    email_node = next((c for c in root_node.children if "email" in str(c.label)), None)
    assert email_node is not None
    assert len(email_node.children) == 0  # No further nesting in this example


def test_route_tree_structure_with_matchers():
    """Test route tree structure with matchers."""
    data = {"receiver": "default", "matchers": ["instance =~ ^.*$", "job =~ ^.*$"]}
    route = Route(data)
    tree = Tree("Root")
    route.to_tree(tree)

    # Verify matchers are displayed correctly
    root_node = tree.children[0]
    matchers_node = next(
        (c for c in root_node.children if "Matchers" in str(c.label)), None
    )
    assert matchers_node is not None
    assert len(matchers_node.children) == 2  # Two matchers
    assert any("instance =~ ^.*$" in str(c.label) for c in matchers_node.children)
    assert any("job =~ ^.*$" in str(c.label) for c in matchers_node.children)
