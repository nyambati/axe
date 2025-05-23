#!/usr/bin/env python3

import unittest
from unittest.mock import patch, mock_open
from argparse import Namespace
from axe.config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.args = Namespace()
        self.config_manager = ConfigManager(self.args)

    def test_initialization(self):
        self.assertEqual(self.config_manager.args, self.args)
        self.assertEqual(self.config_manager.base_file, "base.yaml")
        self.assertEqual(self.config_manager.output_file, "alertmanager.yaml")
        self.assertEqual(len(self.config_manager.validation_issues), 0)

    @patch('builtins.open', new_callable=mock_open, read_data='key: value')
    def test_read_yaml_file(self, mock_file):
        result = self.config_manager.read_yaml_file('test.yaml')
        self.assertEqual(result, {'key': 'value'})
        mock_file.assert_called_once_with('test.yaml', 'r', encoding='utf-8')

    def test_add_receiver_to_master_list(self):
        receiver_data = {"name": "test_receiver"}
        source_file = "test.yaml"
        
        # Test successful addition
        self.config_manager._add_receiver_to_master_list(receiver_data, source_file)
        self.assertIn("test_receiver", self.config_manager.all_defined_receivers)
        self.assertEqual(
            self.config_manager.all_defined_receivers["test_receiver"],
            {"data": receiver_data, "source_file": source_file}
        )

        # Test duplicate receiver
        self.config_manager._add_receiver_to_master_list(receiver_data, "other.yaml")
        self.assertEqual(len(self.config_manager.validation_issues), 1)
        self.assertIn("Duplicate receiver name 'test_receiver'", self.config_manager.validation_issues[0])

    def test_validate_single_receiver_config(self):
        # Test valid webhook receiver
        receiver_data = {
            "name": "webhook_receiver",
            "webhook_configs": [{"url": "http://example.com"}]
        }
        self.config_manager._validate_single_receiver_config(receiver_data, "test.yaml")
        self.assertEqual(len(self.config_manager.validation_issues), 0)

        # Test invalid webhook receiver
        invalid_receiver = {
            "name": "invalid_receiver",
            "webhook_configs": [{"url": ""}]  # Empty URL
        }
        self.config_manager._validate_single_receiver_config(invalid_receiver, "test.yaml")
        self.assertEqual(len(self.config_manager.validation_issues), 1)
        self.assertIn("Error: Webhook config 0 for receiver 'invalid_receiver' in file 'test.yaml' is missing a 'url' or it's empty in 'test.yaml'.", self.config_manager.validation_issues[0])

    def test_validate_route_receiver_reference(self):
        route_node = {
            "receiver": "valid_receiver",
            "routes": [{"receiver": "nested_receiver"}]
        }
        
        # Add valid receivers to master list
        self.config_manager.all_defined_receivers = {
            "valid_receiver": {"data": {}, "source_file": "test.yaml"},
            "nested_receiver": {"data": {}, "source_file": "test.yaml"}
        }

        # Test valid route
        self.config_manager._validate_route_receiver_reference(route_node, "root", "test.yaml")
        self.assertEqual(len(self.config_manager.validation_issues), 0)

        # Test invalid route (missing receiver)
        invalid_route = {"receiver": "nonexistent_receiver"}
        self.config_manager._validate_route_receiver_reference(invalid_route, "root", "test.yaml")
        self.assertEqual(len(self.config_manager.validation_issues), 1)
        self.assertIn("Error: Receiver 'nonexistent_receiver' referenced at 'root' in file 'test.yaml' is not defined in any 'receivers' section.", self.config_manager.validation_issues[0])

if __name__ == '__main__':
    unittest.main()
