/**
 * Smoke tests for Ground Station
 * Quick, high-level tests to verify basic functionality
 */

import { test, expect } from '@playwright/test';

test.describe('Smoke Tests', () => {
  test('should navigate to tracking console', async ({ page }) => {
    await page.goto('/track');
    await page.waitForLoadState('networkidle');

    // Verify we're on the tracking page
    expect(page.url()).toContain('/track');
  });

  test('should navigate to waterfall view', async ({ page }) => {
    await page.goto('/waterfall');
    await page.waitForLoadState('networkidle');

    // Verify we're on the waterfall page
    expect(page.url()).toContain('/waterfall');
  });
});

test.describe('Responsive Design', () => {
  test('should work on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Check if the main content is rendered
    await expect(page.getByRole('main')).toBeVisible({ timeout: 15000 });
  });

  test('should work on tablet viewport', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });

    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Check if the main content is rendered
    await expect(page.getByRole('main')).toBeVisible({ timeout: 15000 });
  });
});
