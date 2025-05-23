# Axe - Alertmanager Configuration Tool

A command-line interface tool for managing and troubleshooting Prometheus Alertmanager configurations. Built with Python, Axe helps you visualize, validate, and test your Alertmanager configurations with ease.

## Features

- **Visualize** your Alertmanager route tree structure
- **Evaluate** alert routing through your configuration
- **Render and validate** configurations before deploying
- **Detailed error reporting** for configuration issues

## Installation

### Prerequisites

- Python 3.13+
- pipenv (recommended) or pip

### Using pipenv (recommended)

Clone the repository

```bash
   git clone <repository-url>
   cd axe
```

Install dependencies:

```bash
   pipenv install --dev
```

Install the package in development mode:

```bash
   pipenv install -e .
```

### Using pip

```bash
pip install -e .
```

## Usage

### Viewing Route Tree

Display the route tree structure of your Alertmanager configuration:

```bash
# Using pipenv
pipenv run axe tree config/alertmanager.yaml

# Or if installed globally
axe tree config/alertmanager.yaml
```

### Evaluating Alert Routing

Test how an alert would be routed through your configuration:

```bash
# Basic evaluation
axe eval config/alertmanager.yaml --alert '{"labels":{"severity":"critical"}}'

# With verbose output
axe eval config/alertmanager.yaml --alert @alert.json --verbose
```

### Rendering Configuration

Render and validate your Alertmanager configuration:

```bash
# Basic rendering
axe render config/base.yaml

# With verbose output
axe render config/base.yaml --verbose
```

## Development

### Running Tests

```bash
# Run all tests
pipenv run pytest

# Run tests with coverage
pipenv run pytest --cov=axe

# Run a specific test file
pipenv run pytest tests/test_config_manager.py -v
```

### Code Style

This project uses `black` for code formatting:

```bash
pipenv run black .
```

## License

[Your License Here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
