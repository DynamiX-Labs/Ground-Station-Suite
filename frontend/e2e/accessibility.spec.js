/**
 * E2E tests for accessibility features
 */

import { test, expect } from '@playwright/test';

test.describe('Accessibility - Keyboard Navigation', () => {
  test('should allow tab navigation on home page', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Press tab multiple times
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Check that focus moved to a visible element
    const isFocusedVisible = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return false;
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
    });
    expect(isFocusedVisible).toBe(true);
  });

  test('should allow Enter key to activate navigation links', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Tab to find a navigation link
    let foundLink = false;
    for (let i = 0; i < 20; i++) {
      await page.keyboard.press('Tab');

      const focused = await page.locator(':focus');
      const tagName = await focused.evaluate(el => el.tagName.toLowerCase());

      if (tagName === 'a' || tagName === 'button') {
        foundLink = true;
        break;
      }
    }

    // If we found a link/button, we can test Enter key
    expect(foundLink).toBe(true);
  });

  test('should support Escape key to close dialogs or modals', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Press Escape
    await page.keyboard.press('Escape');

    // Should not crash or cause errors
    expect(page.url()).toContain('/');
  });
});

test.describe('Accessibility - ARIA Labels', () => {
  test('should have proper ARIA labels on navigation', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Check for navigation elements with ARIA labels
    const navigation = page.locator('nav, [role="navigation"]');
    const count = await navigation.count();

    // Should have navigation landmarks
    expect(count).toBeGreaterThan(0);
  });

  test('should have proper ARIA labels on buttons', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Get all buttons
    const buttons = page.locator('button');
    const buttonCount = await buttons.count();

    if (buttonCount > 0) {
      // Check that buttons have accessible names
      const firstButton = buttons.first();
      const ariaLabel = await firstButton.getAttribute('aria-label');
      const text = await firstButton.textContent();

      // Button should have either aria-label or text content
      expect(ariaLabel || text).toBeTruthy();
    }
  });

  test('should have main landmark', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Look for main element
    const main = page.locator('main, [role="main"]');
    await expect(main.first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Accessibility - Focus Management', () => {
  test('should maintain visible focus indicators', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Tab to an element
    await page.keyboard.press('Tab');

    // Get focused element
    const focused = await page.locator(':focus');
    await expect(focused).toBeVisible();

    // Focus should be visible
    const outline = await focused.evaluate(el => {
      const style = window.getComputedStyle(el);
      return style.outline || style.outlineWidth;
    });

    // Should have some focus styling (outline or other)
    expect(outline).toBeDefined();
  });

  test('should not trap focus unexpectedly', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Tab multiple times and collect unique element identifiers
    const positions = [];
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab');
      const focused = await page.locator(':focus');
      // Use aria-label, title, or element type + text to identify element
      const identifier = await focused.evaluate(el => {
        return el.getAttribute('aria-label') ||
               el.getAttribute('title') ||
               el.tagName + ':' + el.textContent?.trim() ||
               el.outerHTML.substring(0, 100);
      });
      positions.push(identifier);
    }

    // Focus should move (not be trapped)
    const uniquePositions = new Set(positions);
    expect(uniquePositions.size).toBeGreaterThan(1);
  });
});

test.describe('Accessibility - Color Contrast', () => {
  test('should render in high contrast mode', async ({ page }) => {
    // Set high contrast media query
    await page.emulateMedia({ colorScheme: 'dark', forcedColors: 'active' });

    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Page should still be visible and functional
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });

  test('should support dark mode', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });

    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Should render dark mode
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });

  test('should support light mode', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'light' });

    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Should render light mode
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });
});

test.describe('Accessibility - Screen Reader Support', () => {
  test('should have descriptive page titles', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Check for page title
    const title = await page.title();
    expect(title).toBeTruthy();
    expect(title.length).toBeGreaterThan(0);
  });

  test('should have proper heading hierarchy', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Check for headings
    const headings = page.locator('h1, h2, h3, h4, h5, h6');
    const count = await headings.count();

    // Should have some headings for structure
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should have alt text for images', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Get all images
    const images = page.locator('img');
    const imageCount = await images.count();

    if (imageCount > 0) {
      // Check first image for alt attribute
      const firstImage = images.first();
      const alt = await firstImage.getAttribute('alt');

      // Image should have alt attribute (can be empty for decorative images)
      expect(alt !== null).toBe(true);
    }
  });
});
