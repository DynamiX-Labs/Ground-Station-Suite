# Contributing to DynamiX-Labs Ground Station Suite

Thank you for your interest in contributing to the DynamiX-Labs Ground Station Suite. We welcome contributions from researchers, software engineers, telemetry experts, and space amateurs. Our goal is to maintain a state-of-the-art, premium open-source ground station system. To ensure high code quality, security, and stability, all contributors must follow the guidelines outlined below.

## Code of Conduct

By participating in this project, you agree to maintain a professional, respectful, and collaborative environment. All communications, code reviews, and discussions must remain constructive and focused on technical excellence.

## Technical Contribution Pathways

### Reporting Security Vulnerabilities
If you discover a security vulnerability, please do not open a public issue. Instead, email security@dynamix-labs.org or contact the core maintainers privately.

### Reporting Bugs and System Deficiencies
1.  **Search Existing Issues:** Ensure the bug has not been reported or resolved.
2.  **Use the Issue Template:** Provide a clear, descriptive title.
3.  **Include Technical Details:**
    *   System architecture (e.g., OS version, CPU, memory).
    *   SDR hardware configuration (e.g., RTL-SDR, HackRF, PlutoSDR).
    *   SDR-Hardware-Benchmark tool outputs if relevant to signal capture issues.
    *   Detailed reproduction steps and minimal working examples.
    *   Expected vs. actual behavior with log traces from the backend or frontend console errors.

### Requesting Features and Architecture Enhancements
We encourage innovation and extensions to support new satellite decoders, tracking protocols, and DSP algorithms.
1.  **Draft a Proposal:** Open a feature request issue.
2.  **Describe the Use Case:** Explain how this enhancement benefits the wider CubeSat or radio amateur community.
3.  **Architectural Alignment:** Detail how the proposed change fits into our L0-L4 multi-layer architecture.

## Development and Coding Standards

To maintain an elite, professional codebase, we enforce strict styling and quality controls across both backend and frontend components.

### Python Backend Standards
*   **Style Guide:** Adhere strictly to PEP 8.
*   **Auto-Formatting:** Use Black with a maximum line length of 100 characters.
*   **Import Sorting:** Use isort to organize and group imports logically.
*   **Static Analysis:** Ensure code passes pre-commit checks, Flake8, and mypy type checks where applicable.
*   **Testing:** Write comprehensive unit and integration tests using pytest. Maintain or improve test coverage in areas of code changes.

### Frontend Javascript and React Standards
*   **Style Guide:** Adhere to modern React design patterns and TypeScript/ES6+ standards.
*   **Code Formatting:** Use Prettier for formatting and ESLint for static analysis.
*   **Styling System:** Utilize Vanilla CSS within standard guidelines. Avoid unauthorized third-party styling frameworks.
*   **Testing:** Write unit and component tests using Vitest/React Testing Library, and E2E tests using Playwright.

## Workflow and Pull Request Guidelines

All development must be conducted on branches branched from `main` (or the current active release branch).

### Branch Naming Conventions
*   `feature/feature-name` for new components or features.
*   `bugfix/bug-description` for bug fixes.
*   `docs/docs-update` for documentation changes.
*   `refactor/refactor-name` for code improvements without functional changes.

### Preparing Your Pull Request
1.  **Synchronize with Main:** Rebase or merge the latest `main` branch into your working branch.
2.  **Execute Local Validation:**
    *   Run `pre-commit run --all-files` to ensure linters and code formatters pass.
    *   Execute backend tests: `pytest` from the `backend` directory.
    *   Execute frontend tests: `npm test` from the `frontend` directory.
3.  **Commit Log Standards:** Write clear, concise, and emoji-free commit messages. Use the imperative mood (e.g., "Implement Doppler correction queue" instead of "implemented Doppler correction queue").

### Submitting the Pull Request
1.  **Detailed Description:** Describe the changes made, the rationale behind design choices, and how the changes were verified.
2.  **Link Related Issues:** Reference the issues closed or resolved by this PR (e.g., `Closes #101`).
3.  **Visual Proof:** If you are modifying the UI or adding visualization capabilities, provide high-quality screenshots or recordings demonstrating the verified changes.
4.  **Review Process:** At least one core maintainer must review and approve your code before merging. Respond promptly to feedback and requested changes.

## Intellectual Property and Licensing

By contributing code to the DynamiX-Labs Ground Station Suite, you agree to license your contributions under the GNU GPL v3.
*   All new source files must contain the standard DynamiX-Labs copyright header:
    ```text
    Copyright (C) 2025-2026 Efstratios Goudelis
    Modifications and extensions Copyright (C) 2026 DynamiX-Labs
    Licensed under the GNU General Public License v3.
    ```
*   Ensure that any external libraries or snippets included are compatible with GNU GPL v3.

