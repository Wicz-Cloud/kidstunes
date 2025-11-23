# Contributing to KidsTunes

Thank you for your interest in contributing to KidsTunes! This document provides guidelines and information for contributors.

## Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors. By participating, you agree to:

- Be respectful and inclusive
- Focus on constructive feedback
- Accept responsibility for mistakes
- Show empathy towards other contributors

## How to Contribute

### Reporting Bugs

1. Check the [Issues](https://github.com/woczcloud/kidstunes/issues) page to see if the bug has already been reported
2. If not, create a new issue with:
   - A clear title describing the bug
   - Steps to reproduce the issue
   - Expected vs. actual behavior
   - Your environment (OS, Python version, etc.)
   - Any relevant logs or error messages

### Suggesting Features

1. Check existing issues to see if the feature has been suggested
2. Create a new issue with:
   - A clear title for the feature
   - Detailed description of the proposed feature
   - Use case or problem it solves
   - Any implementation ideas

### Contributing Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes following the coding standards
4. Add tests for new functionality
5. Ensure all tests pass: `pytest`
6. Format code: `black . && isort .`
7. Check type hints: `mypy kidstunes/`
8. Commit your changes: `git commit -m "Add your feature"`
9. Push to your fork: `git push origin feature/your-feature-name`
10. Create a Pull Request

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/woczcloud/kidstunes.git
   cd kidstunes
   ```

2. Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

4. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

5. Copy and configure:
   ```bash
   cp config.yaml.example config.yaml
   # Edit config.yaml with your settings
   ```

## Coding Standards

### Python Style
- Follow PEP 8
- Use type hints for all function parameters and return values
- Write docstrings for all modules, classes, and functions
- Keep line length under 88 characters (Black default)

### Code Quality Tools
This project uses several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **mypy**: Type checking
- **flake8**: Linting
- **pytest**: Testing

Run all checks with:
```bash
black .
isort .
mypy kidstunes/
flake8 kidstunes/
pytest
```

### Commit Messages
- Use clear, descriptive commit messages
- Start with a verb in imperative mood (e.g., "Add", "Fix", "Update")
- Keep the first line under 50 characters
- Add a blank line and detailed description if needed

### Testing
- Write tests for all new functionality
- Maintain test coverage above 80%
- Use descriptive test names
- Test both success and failure cases

## Project Structure

```
kid_tunz/
├── kidstunes/          # Main package
│   ├── __init__.py
│   ├── main.py         # Entry point
│   ├── bot.py          # Discord bot logic
│   ├── downloader.py   # YouTube download and AI
│   ├── database.py     # Database operations
│   ├── config.py       # Configuration
│   └── models.py       # Data models
├── tests/              # Test suite
├── docs/               # Documentation
├── .github/            # GitHub configuration
├── pyproject.toml      # Package configuration
├── requirements.txt    # Runtime dependencies
├── requirements-dev.txt # Development dependencies
├── .gitignore
├── LICENSE
├── README.md
└── CONTRIBUTING.md
```

## Pull Request Process

1. Ensure your PR includes:
   - Clear description of changes
   - Reference to related issues
   - Tests for new functionality
   - Updated documentation if needed

2. PRs will be reviewed for:
   - Code quality and style
   - Test coverage
   - Documentation
   - Breaking changes

3. Once approved, a maintainer will merge your PR

## License

By contributing to KidsTunes, you agree that your contributions will be licensed under the MIT License.

## Questions?

If you have questions about contributing, feel free to:
- Open a discussion on GitHub
- Ask in the project's Discord server (if available)
- Contact the maintainers

Thank you for contributing to KidsTunes! 🎵
