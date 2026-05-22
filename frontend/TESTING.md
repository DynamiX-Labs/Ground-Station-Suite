# Frontend Testing Guide

> **Quick Start**: New to testing? Jump to the [5-Minute Quick Start](#quick-start-5-minutes) to get running immediately!

This document describes the complete testing infrastructure for the Ground Station frontend application.

## Table of Contents

- [Quick Start (5 Minutes)](#quick-start-5-minutes)
- [Testing Stack](#testing-stack)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Test Utilities](#test-utilities)
- [Mocking](#mocking)
- [Coverage](#coverage)
- [Best Practices](#best-practices)
- [Debugging Tests](#debugging-tests)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)
- [Resources](#resources)

---

## Quick Start (5 Minutes)

Get up and running with tests in 5 minutes! 🚀

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Install Playwright Browsers (First Time Only)

```bash
npx playwright install
```

### 3. Run Your First Tests

**Unit Tests**

```bash
# Run all tests
npm test

# Watch mode (auto-rerun on file changes)
npm test -- --watch

# With UI (recommended for development)
npm run test:ui
```

**E2E Tests**

```bash
# Make sure your dev server is running first
npm run dev

# In another terminal:
npm run test:e2e

# Or run with interactive UI
npm run test:e2e:ui
```

### 4. Check Coverage

```bash
npm run test:coverage

# Open the HTML report
open coverage/index.html  # macOS
xdg-open coverage/index.html  # Linux
start coverage/index.html  # Windows
```

### 5. Writing Your First Test

Create a test file next to your component:

```jsx
// src/components/MySatellite/__tests__/MySatellite.test.jsx
import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../../../test/test-utils';
import MySatellite from '../MySatellite';

describe('MySatellite', () => {
  it('displays satellite name', () => {
    renderWithProviders(
      <MySatellite name="ISS" />
    );

    expect(screen.getByText('ISS')).toBeInTheDocument();
  });
});
```

Run it:

```bash
npm test -- MySatellite.test.jsx
```

### Quick Reference

| Command | Description |
|---------|-------------|
| `npm test` | Run unit tests |
| `npm run test:ui` | Run tests with UI |
| `npm run test:coverage` | Run with coverage |
| `npm run test:e2e` | Run E2E tests |
| `npm run test:e2e:ui` | Run E2E with UI |
| `npm run test:e2e:debug` | Debug E2E tests |

**Next**: Read the sections below for comprehensive testing documentation.

---

## Testing Stack

- **Vitest** - Fast unit test framework for Vite projects
- **React Testing Library** - Component testing utilities
- **Playwright** - End-to-end testing framework
- **@testing-library/jest-dom** - Custom matchers for DOM assertions
- **@testing-library/user-event** - User interaction simulation

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── **/__tests__/        # Component tests
│   └── test/
│       ├── setup.js              # Test environment setup
│       └── test-utils.jsx        # Custom test utilities
├── e2e/                          # E2E tests
│   ├── example.spec.js
│   └── satellite-tracking.spec.js
├── vitest.config.js              # Vitest configuration
└── playwright.config.js          # Playwright configuration
```

## Running Tests

### Unit & Component Tests

```bash
# Run all unit tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with UI
npm run test:ui

# Run with coverage
npm run test:coverage

# Run specific test file
npm test -- src/components/common/__tests__/login.test.jsx
```

### End-to-End Tests

```bash
# Run all E2E tests
npm run test:e2e

# Run E2E tests with UI (interactive mode)
npm run test:e2e:ui

# Run E2E tests in debug mode
npm run test:e2e:debug

# Run specific test file
npm run test:e2e -- e2e/satellite-tracking.spec.js

# Run tests for specific browser
npm run test:e2e -- --project=chromium
npm run test:e2e -- --project=firefox
npm run test:e2e -- --project=webkit

# Run in headed mode (see the browser)
npm run test:e2e -- --headed
```

## Writing Tests

### Component Tests

Create test files in `__tests__` directories next to your components:

```jsx
// src/components/common/__tests__/MyComponent.test.jsx
import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders, userEvent } from '../../../test/test-utils';
import MyComponent from '../MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    renderWithProviders(<MyComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('handles user interaction', async () => {
    const user = userEvent.setup();
    renderWithProviders(<MyComponent />);

    await user.click(screen.getByRole('button'));
    expect(screen.getByText('Clicked')).toBeInTheDocument();
  });
});
```

### Common Testing Patterns

#### Testing Redux-Connected Components

```jsx
import { renderWithProviders } from '../../../test/test-utils';

const { store } = renderWithProviders(<MyComponent />, {
  preloadedState: {
    satellites: {
      selected: 'ISS',
      list: [{ id: 1, name: 'ISS' }]
    }
  }
});
```

#### Testing User Interactions

```jsx
import { userEvent } from '../../../test/test-utils';

const user = userEvent.setup();
await user.click(screen.getByRole('button'));
await user.type(screen.getByLabelText('Search'), 'satellite');
```

#### Testing Async Operations

```jsx
import { waitFor } from '@testing-library/react';

await waitFor(() => {
  expect(screen.getByText('Loaded')).toBeInTheDocument();
});
```

### Redux Slice Tests

```javascript
// src/components/settings/__tests__/preferences-slice.test.js
import { describe, it, expect } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import preferencesReducer, { updatePreference } from '../preferences-slice';

describe('preferences slice', () => {
  it('updates preference value', () => {
    const store = configureStore({
      reducer: { preferences: preferencesReducer },
    });

    store.dispatch(updatePreference({ key: 'theme', value: 'dark' }));

    expect(store.getState().preferences.theme).toBe('dark');
  });
});
```

### E2E Tests

Create test files in the `e2e` directory:

```javascript
// e2e/my-feature.spec.js
import { test, expect } from '@playwright/test';

test.describe('My Feature', () => {
  test('should work correctly', async ({ page }) => {
    await page.goto('/my-feature');

    await page.click('button[aria-label="Start"]');

    await expect(page.locator('text=Success')).toBeVisible();
  });
});
```

## Test Utilities

### renderWithProviders

Renders a component with Redux, Router, and Theme providers:

```jsx
import { renderWithProviders } from '../../../test/test-utils';

const { store } = renderWithProviders(<MyComponent />, {
  preloadedState: {
    satellites: { list: [] }
  }
});
```

### createMockSocket

Creates a mock Socket.IO client for testing:

```javascript
import { createMockSocket } from '../../../test/test-utils';

const mockSocket = createMockSocket();
mockSocket.emit('connect');
mockSocket.triggerEvent('satellite-tracking', { data: {} });
```

## Mocking

### Mocking Modules

```javascript
import { vi } from 'vitest';

vi.mock('socket.io-client', () => ({
  default: vi.fn(() => mockSocket),
}));
```

### Mocking API Calls

```javascript
import { vi } from 'vitest';

global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    json: async () => ({ data: 'test' }),
  })
);
```

## Coverage

Coverage reports are generated in the `coverage/` directory:

- **HTML Report**: `coverage/index.html`
- **Text Summary**: Displayed in console
- **LCOV**: `coverage/lcov.info` (for CI/CD)

### Coverage Thresholds

Current thresholds (configured in `vitest.config.js`):
- Lines: 70%
- Functions: 70%
- Branches: 70%
- Statements: 70%

## Best Practices

1. **Test Behavior, Not Implementation**: Focus on what the component does, not how it does it
2. **Use Semantic Queries**: Prefer `getByRole`, `getByLabelText` over `getByTestId`
3. **Avoid Testing Redux Internals**: Test user-facing behavior instead
4. **Mock External Dependencies**: Socket.IO, APIs, browser APIs
5. **Clean Up**: Tests should not affect each other
6. **Async Operations**: Always await async operations
7. **Accessibility**: Use ARIA roles and labels for better testability

## Debugging Tests

### Vitest

```bash
# Run with UI (recommended)
npm run test:ui

# Run with --inspect-brk flag
node --inspect-brk ./node_modules/vitest/vitest.mjs run

# Then open chrome://inspect in Chrome
```

Then click on any test to see detailed execution.

### Playwright

```bash
# Run in headed mode (see the browser)
npm run test:e2e -- --headed

# Run with Playwright Inspector
npm run test:e2e:debug

# Generate tests with Codegen
npx playwright codegen http://localhost:5173
```

## CI/CD Integration

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

See `.github/workflows/tests.yml` for CI configuration.

## Troubleshooting

### Tests Not Running

1. Clear node_modules and reinstall:
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

2. Update Playwright browsers:
   ```bash
   npx playwright install --with-deps
   ```

3. Check for stale mocks or test state

### E2E Tests Timeout

- Increase timeout in `playwright.config.js`
- Check if backend is running (`npm run dev` in another terminal)
- Check network conditions
- Verify selectors are correct

### React 19 Compatibility

If you encounter issues with React 19:
- This is normal during the RC phase
- Tests should still work correctly
- Ensure all testing libraries are up to date
- Check for console warnings about deprecated features
- Update @testing-library/react when React 19 stable is released

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [Playwright Documentation](https://playwright.dev/)
- [Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)

---

**Happy Testing!** 🧪✨

For questions or issues with testing setup, check out example tests in `src/components/common/__tests__/` and `e2e/`.
