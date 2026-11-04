# Contributing Guidelines

Thank you for your interest in contributing to **P-Downloader**! We welcome bug reports, feature enhancements, documentation improvements, and architectural optimizations.

---

## 1. Development Workflow

### 1.1 Fork & Clone
1. Fork the repository on GitHub: [`https://github.com/pkgtm2419/p-downloader`](https://github.com/pkgtm2419/p-downloader).
2. Clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/p-downloader.git
   cd p-downloader
   ```

### 1.2 Branching Strategy
- `master`: Mainline production branch. All releases are tagged against `master`.
- Feature branches: Create descriptive branches off `master`:
  - `feature/adaptive-concurrency-tuning`
  - `fix/range-header-trailing-slash`
  - `docs/update-architecture-diagram`

```bash
git checkout -b feature/my-new-feature
```

---

## 2. Coding & Quality Standards

Before submitting a Pull Request, ensure your changes satisfy our quality checklist:

### 2.1 Python Code Formatting
We adhere to PEP 8 standards with a maximum line length of 120 characters:
```powershell
# Run flake8 linter
flake8 core gui tests --max-line-length=120
```

### 2.2 Testing
All new functionality must be accompanied by automated tests:
```powershell
# Run unit and integration tests
python -m pytest tests/test_adaptive_concurrency.py tests/test_block_scheduler.py tests/test_retry_policy.py
```
- Ensure zero regression on existing tests.
- For network transfer features, use the `FaultOrigin` mock fixture (`tests/support/http_origin.py`) rather than hitting real external websites.

### 2.3 Thread Safety
- **Strict Prohibition**: Never interact with PyQt6 UI widgets directly from worker threads. Always emit Qt signals (`pyqtSignal`) to marshal state transitions back to the main GUI thread.
- Ensure all loops in worker threads check cooperative cancellation flags (`stop_requested.is_set()`).

### 2.4 Security & Privacy
- Never log plain credentials, bearer tokens, or session cookies.
- Wrap all diagnostic URL logs with `core/http_errors.py:redact_secrets()`.

---

## 3. Commit Message Conventions

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat(engine)`: Add support for DASH dynamic stream manifests
- `fix(range)`: Handle servers returning 200 instead of 206 gracefully
- `docs(api)`: Document BlockScheduler API and claim methods
- `refactor(gui)`: Optimize table cell repaints during high-speed transfers
- `test(chaos)`: Add simulated 429 rate limit backoff test cases

---

## 4. Pull Request Checklist

When opening a Pull Request:
1. Provide a concise summary of the changes and the motivation.
2. Link any relevant issue numbers (e.g., `Closes #42`).
3. Confirm that all local tests pass.
4. Update or add corresponding documentation in `docs/`.
5. Maintain a clean, rebased commit history against upstream `master`.

---

## 5. Licensing

By contributing to P-Downloader, you agree that your contributions will be licensed under the project's [MIT License](file:///LICENSE).

