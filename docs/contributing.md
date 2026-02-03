# Contributing to FILAMENT

Thank you for your interest in contributing to the FILAMENT project! This document provides guidelines and instructions for contributing.

## 🎯 Code of Conduct

This project is dedicated to providing a harassment-free experience for everyone. Be respectful and constructive in all interactions.

## 🚀 Getting Started

### Development Environment Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/filament.git
   cd filament
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e .  # Install in development mode
   ```

4. **Set up pre-commit hooks**
   ```bash
   pre-commit install
   ```

5. **Configure your environment**
   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

### Database Setup

See [docs/tech_stack.md](docs/tech_stack.md) for detailed database setup instructions.

## 📝 Development Guidelines

### Code Style

- **Python**: Follow PEP 8. We use `black` for formatting and `ruff` for linting.
- **Docstrings**: Use Google-style docstrings for all public functions and classes.
- **Type hints**: Use type annotations for function parameters and return values.

```python
def find_matches(
    query: str,
    threshold: float = 0.75,
    limit: int = 10
) -> list[MatchResult]:
    """Find potential matches using vector similarity search.
    
    Args:
        query: The search query text.
        threshold: Minimum similarity score (0.0 to 1.0).
        limit: Maximum number of results to return.
        
    Returns:
        List of MatchResult objects sorted by similarity score.
        
    Raises:
        DatabaseError: If the vector search fails.
    """
    ...
```

### Git Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** with clear, atomic commits

3. **Write tests** for new functionality

4. **Run the test suite**
   ```bash
   pytest tests/ -v
   ```

5. **Submit a pull request** with a clear description

### Commit Messages

Follow conventional commits format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

Example: `feat(search): add semantic similarity boosting for Canadian slang`

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_extraction.py -v
```

### Writing Tests

- Place tests in the `tests/` directory
- Mirror the source code structure
- Use descriptive test function names
- Include both positive and negative test cases

## 📖 Documentation

- Update documentation when adding new features
- Keep the README.md current
- Add docstrings to all public APIs
- Update relevant docs in `docs/` directory

## 🔒 Privacy Considerations

When contributing, keep in mind:

- **Never commit real case data** - Use synthetic data for testing
- **Review all output** - Ensure no PII leaks into logs or errors
- **Test with mock data** - Create realistic but fictional test cases

## 📋 Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Code follows the project style guidelines
- [ ] All tests pass locally
- [ ] New code has appropriate test coverage
- [ ] Documentation is updated
- [ ] Commit messages follow conventions
- [ ] No sensitive data in commits

## 💬 Questions?

Open an issue for questions or discussion about features and improvements.
