# Contributing Guide

Thank you for your interest in contributing to MyWifiPass System. This guide outlines the process for submitting contributions.

---

## Code of Conduct

- Be respectful and constructive in all interactions
- Focus on the technical merits of contributions
- Follow the existing code style and patterns

---

## Getting Started

1. **Read the documentation** - Start with [Architecture](architecture.md) and [Development Guide](development.md)
2. **Check existing issues** - Look for open issues or feature requests in the [GitHub Issues](https://github.com/Pablodiz/mywifipass_system/issues)
3. **Open an issue first** - For significant changes, open an issue to discuss the approach before writing code

---

## Pull Request Process

### 1. Fork and Branch

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/mywifipass_system.git
cd mywifipass_system
git checkout -b feat/your-feature-name
# or
git checkout -b fix/bug-description
```

### 2. Make Your Changes

- Follow the [code style](#code-style) guidelines
- Add tests for new functionality
- Update documentation if needed (files in `docs/`)

### 3. Test Before Submitting

```bash
# Run tests
cd mywifipass
python manage.py test

# Check for syntax errors
python -m py_compile $(find . -name "*.py" -not -path "./venv/*" -not -path "./.git/*")

# Verify migrations
python manage.py makemigrations --check --dry-run
```

### 4. Submit the PR

- Use the [Pull Request Template](https://github.com/Pablodiz/mywifipass_system/blob/main/.github/pull_request_template.md)
- Include:
  - Clear description of the change
  - Related issue number(s)
  - Screenshots for UI changes
  - Testing notes

### 5. Review Process

- A maintainer will review your PR
- Address review feedback with additional commits
- CI checks must pass before merging

---

## Code Style

### Python

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- **4 spaces** for indentation (no tabs)
- Keep lines under **100 characters** where reasonable
- Use descriptive variable names

### Django Models

```python
class MyModel(models.Model):
    """
    Docstring describing the model's purpose.
    """
    name = models.CharField(max_length=64)
    related = models.ForeignKey(
        OtherModel,
        on_delete=models.CASCADE,
        related_name='my_models',
        help_text="Description of the relationship"
    )

    class Meta:
        verbose_name = "My Model"
        verbose_name_plural = "My Models"
        ordering = ['name']
```

### API ViewSets

- Define `get_serializer_class()` and `get_permissions()` for action-based serialization and auth
- Use `@swagger_auto_schema(tags=...)` for Swagger grouping
- Specify `throttle_classes` for rate-limited actions
- Follow the existing pattern in `api/users.py`:

```python
class MyViewSet(ModelViewSet):
    lookup_field = 'uuid'

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateSerializer
        elif self.action == 'list':
            return ListSerializer
        return DetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

    @action(detail=True, methods=['post'], permission_classes=[AllowAny], throttle_classes=[MyThrottle])
    def my_action(self, request, **kwargs):
        ...
```

### Imports

- Group imports: standard library → third-party → local
- Use **lazy imports** to avoid circular dependencies:

```python
# Inside a method, not at module level:
def my_method(self):
    from mywifipass.utils import send_mail
    from mywifipass.radius.radius_certs import export_certificates
```

### Docstrings

- Use triple-quoted docstrings for all public functions, methods, and classes
- Describe parameters, return values, and raised exceptions:

```python
def my_function(param1: str, param2: int) -> bool:
    """
    Brief description of what the function does.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of the return value

    Raises:
        ValueError: When param1 is invalid
    """
```

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short description>

<optional body>

<optional footer>
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code restructuring without behavior change
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks, dependency updates

**Examples:**
```
feat: add support for scheduled CRL export
fix(models): correct timezone handling in certificate expiry
docs: update installation guide for Docker 24+
refactor: extract email sending to dedicated service
test: add CSR validation unit tests
```

---

## Reporting Bugs

Use the [Bug Report Template](https://github.com/Pablodiz/mywifipass_system/issues/new?template=bug_report.md). Include:

- Docker / Python version
- Relevant logs (`docker compose logs mywifipass`)
- Steps to reproduce
- Expected vs. actual behavior

### Security Vulnerabilities

If you discover a security vulnerability, please **do not** open a public issue. Contact the maintainer directly.

---

## Feature Requests

Use the [Feature Request Template](https://github.com/Pablodiz/mywifipass_system/issues/new?template=feature_request.md). Describe:

- The problem you're trying to solve
- Your proposed solution
- Alternative approaches you've considered

---

## Documentation Contributions

Documentation lives in the `docs/` folder. To contribute:

1. Edit the relevant Markdown file
2. Run a local preview (any Markdown renderer works)
3. Verify internal links work
4. Submit a PR

---

## License

By contributing, you agree that your contributions will be licensed under the [BSD 3-Clause License](../LICENSE).

The project retains the original copyright notices from the `django-x509` community (`Copyright (c) 2015, Federico Capoano / OpenWISP`) alongside the MyWifiPass copyright (`Copyright (c) 2025, Pablo Diz de la Cruz`).

---

## Questions?

Open a [Question issue](https://github.com/Pablodiz/mywifipass_system/issues/new?template=question.md) or start a discussion.
