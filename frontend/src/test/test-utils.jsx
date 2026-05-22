/**
 * Custom render function for testing React components with Redux and Router
 */

import { render } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { setupTheme } from '../theme';
import { vi } from 'vitest';

// Import your reducers
// You'll need to export these from your store.jsx
// import rootReducer from '../components/common/store';

/**
 * Create a test store with initial state
 */
export function createTestStore(preloadedState = {}) {
  return configureStore({
    reducer: {
      // Add your reducers here
      // For now, we'll use a simple placeholder
      test: (state = {}) => state,
    },
    preloadedState,
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: false,
      }),
  });
}

/**
 * Custom render function that wraps components with providers
 */
export function renderWithProviders(
  ui,
  {
    preloadedState = {},
    store = createTestStore(preloadedState),
    theme = setupTheme(),
    ...renderOptions
  } = {}
) {
  function Wrapper({ children }) {
    return (
      <Provider store={store}>
        <ThemeProvider theme={theme}>
          <BrowserRouter>{children}</BrowserRouter>
        </ThemeProvider>
      </Provider>
    );
  }

  return {
    store,
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
  };
}

/**
 * Mock socket.io client
 */
export function createMockSocket() {
  const eventHandlers = new Map();

  return {
    on: vi.fn((event, handler) => {
      eventHandlers.set(event, handler);
    }),
    off: vi.fn((event) => {
      eventHandlers.delete(event);
    }),
    emit: vi.fn((event, ...args) => {
      const handler = eventHandlers.get(event);
      if (handler) {
        handler(...args);
      }
    }),
    connect: vi.fn(),
    disconnect: vi.fn(),
    connected: true,
    id: 'test-socket-id',
    // Helper to trigger events in tests
    triggerEvent: (event, data) => {
      const handler = eventHandlers.get(event);
      if (handler) {
        handler(data);
      }
    },
  };
}

/**
 * Wait for async updates
 */
export const waitForAsync = () => new Promise(resolve => setTimeout(resolve, 0));

// Re-export everything from React Testing Library
export * from '@testing-library/react';
export { default as userEvent } from '@testing-library/user-event';
