from axe.tree import parse_alertmanager_config
from unittest.mock import patch, mock_open


def test_parse_alertmanager_config():
    """Test parsing of alertmanager configuration."""
    config_yaml = """
    route:
      receiver: 'default-receiver'
      group_by: ['alertname']
      routes:
      - receiver: 'critical-receiver'
        match:
          severity: 'critical'
    """

    with patch("builtins.open", mock_open(read_data=config_yaml)):
        config = parse_alertmanager_config("test.yaml")
        assert config["route"]["receiver"] == "default-receiver"
        assert config["route"]["group_by"] == ["alertname"]
        assert config["route"]["routes"][0]["receiver"] == "critical-receiver"
