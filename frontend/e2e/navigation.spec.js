/**
 * E2E tests for navigation functionality
 */

import { test, expect } from '@playwright/test';

test.describe('Navigation State', () => {
  test('should maintain navigation state after refresh', async ({ page }) => {
    await page.goto('/settings/preferences');
    await page.waitForLoadState('networkidle');

    // Refresh the page
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Should still be on preferences page
    expect(page.url()).toContain('/settings/preferences');
  });
});
