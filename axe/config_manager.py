#!/usr/bin/env python3
import copy
import yaml
import os
import logging

from typing import List, Dict, Any, Union
from argparse import Namespace


class UniqueList:
    def __init__(self, initial_list: list = None, key_attribute: str = "name"):
        """
        Initializes the manager for a list of objects with unique keys.

        Args:
            initial_list: An optional list of items to initialize with.
            key_attribute: The name of the attribute (string key for dictionaries)
                           that should be unique.
        """
        self.items_list = []
        self.unique_keys = set()
        self.key_attribute = key_attribute

        if initial_list:
            for item in initial_list:
                self.add_item(item)

    def add_item(self, item):
        """
        Adds an item to the list, ensuring its key_attribute is unique.
        Raises a ValueError if the key already exists.
        """
        if not isinstance(item, dict):
            raise ValueError(
                f"Error: Expected dictionary item, but got {type(item).__name__}."
            )

        key_value = item.get(self.key_attribute)
        if key_value is None:
            raise ValueError(
                f"Error: Item does not have a '{self.key_attribute}' key or its value is None."
            )

        if not isinstance(key_value, str) or not key_value:
            raise ValueError(
                f"Error: '{self.key_attribute}' value '{key_value}' is invalid or empty."
            )

        if key_value in self.unique_keys:
            raise ValueError(
                f"Error: An item with '{self.key_attribute}' '{key_value}' already exists."
            )

        self.items_list.append(item)
        self.unique_keys.add(key_value)
        logging.debug(f"Added item with {self.key_attribute}: {key_value}")

    def get_all_items(self) -> List[Dict[str, Any]]:
        return self.items_list

    def has_key(self, key_value: str) -> bool:
        """Checks if a key value already exists in the manager."""
        return key_value in self.unique_keys

    def get_item_by_key(self, key_value: str) -> Union[Dict[str, Any], None]:
        """Retrieves an item by its key value."""
        for item in self.items_list:
            if item.get(self.key_attribute) == key_value:
                return item
        return None


class ConfigManager:
    def __init__(
        self,
        args: Namespace,
        base_file: str = "base.yaml",
        output_file: str = "alertmanager.yaml",
    ):
        self.args: Namespace = args
        self.base_file: str = base_file
        self.output_file: str = output_file
        # New: Stores all defined receivers from all files, including their source.
        # Format: {"receiver_name": {"data": {...}, "source_file": "path/to/file.yaml"}}
        self.all_defined_receivers: Dict[str, Dict[str, Any]] = {}
        self.validation_issues: List[str] = []  # Collect all validation issues

    def _add_receiver_to_master_list(
        self, receiver_data: Dict[str, Any], source_file: str
    ):
        """
        Adds a receiver to the master list, handling duplicates and reporting issues.
        """
        receiver_name = receiver_data.get("name")
        if not receiver_name:
            self.validation_issues.append(
                f"Error: Receiver definition in '{source_file}' is missing the 'name' key."
            )
            return

        if not isinstance(receiver_name, str) or not receiver_name:
            self.validation_issues.append(
                f"Error: Receiver name '{receiver_name}' in '{source_file}' is invalid or empty."
            )
            return

        if receiver_name in self.all_defined_receivers:
            existing_source = self.all_defined_receivers[receiver_name]["source_file"]
            self.validation_issues.append(
                f"Error: Duplicate receiver name '{receiver_name}' found. "
                f"First defined in '{existing_source}', duplicated in '{source_file}'."
            )
        else:
            self.all_defined_receivers[receiver_name] = {
                "data": receiver_data,
                "source_file": source_file,
            }
            logging.debug(
                f"Added receiver '{receiver_name}' from '{source_file}' to master list."
            )
            # Perform immediate validation for receiver config itself (e.g., webhook URL)
            self._validate_single_receiver_config(receiver_data, source_file)

    def _validate_single_receiver_config(
        self, receiver_data: Dict[str, Any], source_file: str
    ):
        """
        Performs specific validations on an individual receiver configuration.
        """
        receiver_name = receiver_data.get(
            "name", "N/A"
        )  # Use N/A if name is missing earlier

        if "webhook_configs" in receiver_data:
            if not isinstance(receiver_data["webhook_configs"], list):
                self.validation_issues.append(
                    f"Error: 'webhook_configs' for receiver '{receiver_name}' in file '{source_file}' must be a list."
                )
            else:
                for i, webhook_config in enumerate(receiver_data["webhook_configs"]):
                    if not isinstance(webhook_config, dict):
                        self.validation_issues.append(
                            f"Error: Webhook config {i} for receiver '{receiver_name}' in file '{source_file}' is not a dictionary."
                        )
                        continue
                    if "url" not in webhook_config or not webhook_config["url"]:
                        self.validation_issues.append(
                            f"Error: Webhook config {i} for receiver '{receiver_name}' in file '{source_file}' is missing a 'url' or it's empty in '{source_file}'."
                        )
        # Add more specific validations here for other receiver types (email, slack etc.)
        # Example:
        # if 'email_configs' in receiver_data:
        #     if not isinstance(receiver_data['email_configs'], list):
        #         self.validation_issues.append(f"Error: 'email_configs' for receiver '{receiver_name}' in file '{source_file}' must be a list.")
        #     else:
        #         for i, email_config in enumerate(receiver_data['email_configs']):
        #             if 'to' not in email_config or not email_config['to']:
        #                 self.validation_issues.append(f"Error: Email config {i} for receiver '{receiver_name}' missing 'to' address in '{source_file}'.")

    def _validate_route_receiver_reference(
        self, route_node: Dict[str, Any], path: str, source_file: str
    ):
        """
        Validates that a receiver referenced in a route exists in the master list.
        """
        if "receiver" in route_node:
            receiver_name = route_node["receiver"]
            if not isinstance(receiver_name, str) or not receiver_name:
                self.validation_issues.append(
                    f"Error: Invalid or empty receiver name at '{path}.receiver' in file '{source_file}'."
                )
                return

            if receiver_name not in self.all_defined_receivers:
                self.validation_issues.append(
                    f"Error: Receiver '{receiver_name}' referenced at '{path}' "
                    f"in file '{source_file}' is not defined in any 'receivers' section."
                )

        if "routes" in route_node:
            if not isinstance(route_node["routes"], list):
                self.validation_issues.append(
                    f"Error: 'routes' at '{path}.routes' in file '{source_file}' must be a list."
                )
                return
            for i, sub_route in enumerate(route_node["routes"]):
                if not isinstance(sub_route, dict):
                    self.validation_issues.append(
                        f"Error: Sub-route at '{path}.routes[{i}]' in file '{source_file}' is not a dictionary."
                    )
                    continue
                self._validate_route_receiver_reference(
                    sub_route, f"{path}.routes[{i}]", source_file
                )

    def read_yaml_file(self, file_path: str) -> Union[Dict[str, Any], List[Any], None]:
        """
        Reads a YAML file safely.

        Args:
            file_path (str): The path to the YAML file.

        Returns:
            Union[Dict[str, Any], List[Any], None]: The loaded YAML content,
                                                    or None if an error occurs.
        """
        logging.debug(f"Attempting to read YAML file: {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = yaml.safe_load(file)
                logging.debug(f"Successfully loaded YAML from {file_path}")
                return self.replace_env_vars(content)
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
            return None
        except yaml.YAMLError as e:
            logging.error(f"Error parsing YAML file {file_path}: {e}")
            self.validation_issues.append(f"Error parsing YAML file {file_path}: {e}")
            return None
        except Exception as e:
            logging.error(
                f"An unexpected error occurred while reading {file_path}: {e}"
            )
            self.validation_issues.append(
                f"An unexpected error occurred while reading {file_path}: {e}"
            )
            return None

    def find_and_load_routing_configs(self, base_folder: str) -> Dict[str, Any]:
        """
        Recursively searches for and loads YAML files containing routing components.
        Performs incremental validation of receivers and route references.

        Args:
            base_folder (str): The root folder to start the search from.

        Returns:
            Dict[str, Any]: A dictionary containing lists of loaded receivers, routes, and time_intervals.
        """
        logging.info(
            f"Searching for routes and receivers config in '{base_folder}' directory"
        )

        routing_config = {"receivers": [], "routes": [], "time_intervals": []}

        processed_files = set()

        for root, _, files in os.walk(base_folder):
            for file_name in files:
                if (
                    file_name
                    and file_name.endswith((".yaml", ".yml"))
                    and file_name != self.base_file
                ):
                    file_path = os.path.join(root, file_name)
                    abs_file_path = os.path.abspath(file_path)

                    if abs_file_path in processed_files:
                        logging.debug(f"Skipping already processed file: {file_path}")
                        continue

                    processed_files.add(abs_file_path)

                    logging.info(f"Processing configuration file: {file_path}")
                    config = self.read_yaml_file(file_path)

                    if config is None:
                        logging.warning(
                            f"Skipping file {file_path} due to previous error."
                        )
                        continue

                    if not isinstance(config, dict):
                        self.validation_issues.append(
                            f"Error: Skipping {file_path}: Expected a dictionary at root, but got {type(config).__name__}. File content: {config}"
                        )
                        continue

                    found_expected_component = False
                    for component_name in ["receivers", "routes", "time_intervals"]:
                        if component_name in config:
                            found_expected_component = True
                            component_data = config.get(component_name)

                            if not isinstance(component_data, list):
                                if component_name == "routes" and isinstance(
                                    component_data, dict
                                ):
                                    # For a single route dictionary, wrap it in a list
                                    routing_config[component_name].append(
                                        component_data
                                    )
                                    logging.info(
                                        f"Found a single route dictionary in {file_path}, adding..."
                                    )
                                    # Validate this single route's receiver reference
                                    self._validate_route_receiver_reference(
                                        component_data, "route", file_path
                                    )
                                else:
                                    self.validation_issues.append(
                                        f"Error: Expected a list for '{component_name}' in {file_path}, but got {type(component_data).__name__}. "
                                    )
                                    break  # Critical error for this file, stop processing its components

                            if component_name == "receivers":
                                for receiver in component_data:
                                    self._add_receiver_to_master_list(
                                        receiver, file_path
                                    )
                                logging.info(
                                    f"Found {len(component_data)} receivers in {file_path}, adding and validating..."
                                )
                            elif component_name == "routes":
                                for i, route_node in enumerate(component_data):
                                    self._validate_route_receiver_reference(
                                        route_node, f"routes[{i}]", file_path
                                    )
                                logging.info(
                                    f"Found {len(component_data)} routes in {file_path}, validating references..."
                                )

                            logging.info(
                                f"Found {len(component_data)} valid {component_name}, adding..."
                            )
                            routing_config[component_name].extend(component_data)

                    if not found_expected_component:
                        logging.warning(
                            f"Skipping {file_path}: No expected root keys ('receivers', 'routes', 'time_intervals') found."
                        )

        return routing_config

    def write_yaml_file(self, data: Dict[str, Any], file_path: str) -> int:
        """
        Writes data to a YAML file.

        Args:
            data (Dict[str, Any]): The dictionary to write to the YAML file.
            file_path (str): The path to the output YAML file.

        Returns:
            int: 0 on success, 1 on failure.
        """
        logging.info(f"Attempting to write combined configuration to: {file_path}")
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                yaml.dump(
                    data=data,
                    stream=file,
                    indent=2,
                    default_flow_style=False,
                    sort_keys=False,  # Preserve order if needed, or set to True for consistent output
                )
            logging.info(f"Successfully generated {file_path}")
            return 0
        except IOError as e:
            logging.critical(f"Error writing to output file {file_path}: {e}. Exiting.")
            return 1
        except Exception as e:
            logging.critical(
                f"An unexpected error occurred while writing {file_path}: {e}. Exiting."
            )
            return 1

    def replace_env_vars(self, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: self.replace_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.replace_env_vars(elem) for elem in data]
        elif isinstance(data, str) and data.startswith("$"):
            env_var_name = data[1:].upper()
            if env_var_name in os.environ:
                return os.environ[env_var_name]
            else:
                self.validation_issues.append(
                    f"Error: Required environment variable '{env_var_name}' not found for string '{data}'."
                )
                return data  # Return original string or raise an error immediately if you want to fail hard

        return data

    def render(self) -> int:
        """
        Main function to orchestrate the Alertmanager configuration generation.
        Returns:
            int: Exit code (0 for success, non-zero for failure).
        """
        logging.info("Starting alertmanager configuration generation process.")
        base_config_path = os.path.join(self.args.file_path, self.base_file)
        output_file_path = os.path.join(self.args.file_path, self.output_file)

        if os.path.exists(output_file_path):
            os.remove(output_file_path)

        # --- Load Base Configuration ---
        base_config = self.read_yaml_file(base_config_path)
        if base_config is None:
            logging.critical(
                f"Failed to load base configuration from {base_config_path}. Cannot proceed."
            )
            return 1

        if not isinstance(base_config, dict):
            self.validation_issues.append(
                f"Error: Invalid format for {base_config_path}: "
                f"Expected a dictionary at root, but got {type(base_config).__name__}. Cannot proceed."
            )
            return 1

        alertmanager_config: Dict[str, Any] = copy.deepcopy(base_config)
        logging.info(f"Base configuration loaded successfully from {base_config_path}.")

        # --- Populate master receiver list with base config receivers ---
        if "receivers" in base_config:
            if not isinstance(base_config["receivers"], list):
                self.validation_issues.append(
                    f"Error: 'receivers' in '{base_config_path}' must be a list."
                )
            else:
                for receiver in base_config["receivers"]:
                    self._add_receiver_to_master_list(receiver, base_config_path)

        # --- Process additional routing configurations ---
        routing_config_from_folders = self.find_and_load_routing_configs(
            self.args.file_path
        )

        if not isinstance(routing_config_from_folders, dict):
            logging.critical(
                "Internal error: find_and_load_routing_configs returned unexpected type",
                f"Expected dict, got {type(routing_config_from_folders).__name__}. Exiting.",
            )
            return 1

        # --- Integrate Components into Main Config ---
        # Receivers were already processed and added to `self.all_defined_receivers`
        # Now, consolidate the receivers from `self.all_defined_receivers` into the final config.
        alertmanager_config["receivers"] = [
            data["data"] for data in self.all_defined_receivers.values()
        ]
        logging.debug(
            f"Final receivers list consolidated. Total: {len(alertmanager_config['receivers'])} items."
        )

        # Integrate routes and time_intervals (already validated for references during load)
        if "route" not in alertmanager_config or not isinstance(
            alertmanager_config["route"], dict
        ):
            logging.warning(
                f"Key 'route' not found or not a dictionary in {base_config_path}. "
                "Initializing 'route' as an empty dictionary."
            )
            alertmanager_config["route"] = {}

        if "routes" not in alertmanager_config["route"] or not isinstance(
            alertmanager_config["route"]["routes"], list
        ):
            logging.warning(
                f"Key 'route.routes' not found or not a list in {base_config_path}. "
                "Initializing 'route.routes' as an empty list."
            )
            alertmanager_config["route"]["routes"] = []

        # Add routes collected from sub-files
        if routing_config_from_folders.get("routes"):
            # Ensure the root route's receiver is also checked if it exists and is not 'default' or similar.
            # This check for the base route's receiver is crucial.
            if "receiver" in alertmanager_config["route"]:
                root_receiver = alertmanager_config["route"]["receiver"]
                if not isinstance(root_receiver, str) or not root_receiver:
                    self.validation_issues.append(
                        f"Error: Invalid or empty receiver name at 'route.receiver' in file '{base_config_path}'."
                    )
                elif root_receiver not in self.all_defined_receivers:
                    self.validation_issues.append(
                        f"Error: Root receiver '{root_receiver}' referenced at 'route.receiver' "
                        f"in file '{base_config_path}' is not defined in any 'receivers' section."
                    )

            alertmanager_config["route"]["routes"].extend(
                routing_config_from_folders["routes"]
            )
            logging.debug(
                f"Successfully extended 'routes' under 'route' with {len(routing_config_from_folders['routes'])} new items."
            )

        if "time_intervals" not in alertmanager_config or not isinstance(
            alertmanager_config["time_intervals"], list
        ):
            logging.warning(
                f"Key 'time_intervals' not found or not a list in {base_config_path}. "
                "Initializing 'time_intervals' as an empty list."
            )
            alertmanager_config["time_intervals"] = []

        if routing_config_from_folders.get("time_intervals"):
            # Ensure uniqueness for time_intervals
            existing_intervals = UniqueList(
                initial_list=alertmanager_config["time_intervals"], key_attribute="name"
            )
            for interval in routing_config_from_folders["time_intervals"]:
                try:
                    existing_intervals.add_item(interval)
                except ValueError as e:
                    self.validation_issues.append(
                        f"Error adding time_interval from file: {e}"
                    )
                    # Don't return here; collect all errors first
            alertmanager_config["time_intervals"] = existing_intervals.get_all_items()
            logging.debug(
                f"Successfully merged 'time_intervals'. Total: {len(alertmanager_config['time_intervals'])} items."
            )

        # --- Final Validation Check (Collect all errors) ---
        if self.validation_issues:
            logging.error("Configuration generation failed with the following issues:")
            has_fatal_errors = False
            for issue in self.validation_issues:
                logging.error(f"- {issue}")
                if issue.startswith("Error:"):
                    has_fatal_errors = True

            if has_fatal_errors:
                logging.critical(
                    "Fatal errors found during validation. Aborting configuration generation."
                )
                return 1
            else:
                logging.warning(
                    "Validation completed with warnings. Proceeding with configuration generation."
                )
        else:
            logging.info("Configuration passed all validation checks.")

        # --- Write Final Configuration ---
        logging.debug(
            "All components processed. Writing final alertmanager configuration."
        )
        return self.write_yaml_file(alertmanager_config, output_file_path)


def render(args: Namespace) -> int:
    try:
        config = ConfigManager(args)
        return config.render()
    except Exception as e:
        logging.critical(f"Error rendering configuration: {e}")
        return 1
