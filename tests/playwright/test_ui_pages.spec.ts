import { test, expect } from '@playwright/test';

const UI_BASE_URL = 'http://localhost:3001';

test.describe('UI Pages Tests', () => {
  test.describe('Dashboard Page', () => {
    test('should load dashboard and display KPI cards', async ({ page }) => {
      await page.goto(UI_BASE_URL);

      // Wait for page to load
      await expect(page.locator('h1')).toContainText('Dashboard');

      // Check for KPI cards
      await expect(page.getByText('Total Books')).toBeVisible();
      await expect(page.getByText('Total Products')).toBeVisible();
      await expect(page.getByText('Completed')).toBeVisible();
      await expect(page.getByText('Processing')).toBeVisible();
    });

    test('should display navigation sidebar', async ({ page }) => {
      await page.goto(UI_BASE_URL);

      // Check sidebar links
      await expect(page.getByRole('link', { name: /Dashboard/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /Upload/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /Price Books/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /Diff Review/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /Export Center/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /Publish/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /Settings/i })).toBeVisible();
    });

    test('should have theme toggle', async ({ page }) => {
      await page.goto(UI_BASE_URL);

      // Theme toggle should be visible in topbar
      const themeButton = page.locator('button').filter({ hasText: /Light|Dark|System/i }).first();
      await expect(themeButton).toBeVisible();
    });
  });

  test.describe('Upload Page', () => {
    test('should navigate to upload page', async ({ page }) => {
      await page.goto(UI_BASE_URL);
      await page.getByRole('link', { name: /Upload/i }).click();

      await expect(page).toHaveURL(`${UI_BASE_URL}/upload`);
      await expect(page.locator('h1')).toContainText('Upload Price Book');
    });

    test('should display 3-step wizard', async ({ page }) => {
      await page.goto(`${UI_BASE_URL}/upload`);

      // Check for step indicators
      await expect(page.getByText('Select & Upload')).toBeVisible();
      await expect(page.getByText('Parse')).toBeVisible();
      await expect(page.getByText('Summary')).toBeVisible();
    });

    test('should have manufacturer selection', async ({ page }) => {
      await page.goto(`${UI_BASE_URL}/upload`);

      // Check for manufacturer dropdown
      const manufacturerSelect = page.locator('select').first();
      await expect(manufacturerSelect).toBeVisible();
    });

    test('should have file upload area', async ({ page }) => {
      await page.goto(`${UI_BASE_URL}/upload`);

      // Check for drop zone or file input
      await expect(page.getByText(/Drag.*drop.*PDF/i)).toBeVisible();
    });
  });

  test.describe('Price Books List Page', () => {
    test('should navigate to price books page', async ({ page }) => {
      await page.goto(UI_BASE_URL);
      await page.getByRole('link', { name: /Price Books/i }).click();

      await expect(page).toHaveURL(`${UI_BASE_URL}/books`);
      await expect(page.locator('h1')).toContainText('Price Books');
    });

    test('should display stats cards', async ({ page }) => {
      await page.goto(`${UI_BASE_URL}/books`);

      await expect(page.getByText('Total Books')).toBeVisible();
      await expect(page.getByText('Completed')).toBeVisible();
      await expect(page.getByText('Processing')).toBeVisible();
      await expect(page.getByText('Total Products')).toBeVisible();
    });

    test('should have data table with search', async ({ page }) => {
      await page.goto(`${UI_BASE_URL}/books`);

      // Wait a bit for data to load
      await page.waitForTimeout(1000);

      // Check for search input (if there are books)
      const searchInput = page.getByPlaceholder(/Search by manufacturer/i);
      if (await searchInput.count() > 0) {
        await expect(searchInput).toBeVisible();
      }
    });

    test('should have density and column visibility controls', async ({ page }) => {
      await page.goto(`${UI_BASE_URL}/books`);
      await page.waitForTimeout(1000);

      // Look for toolbar buttons (if table is present)
      const densityButton = page.getByRole('button', { name: /Density/i });
      const columnsButton = page.getByRole('button', { name: /Columns/i });

      if (await densityButton.count() > 0) {
        await expect(densityButton).toBeVisible();
        await expect(columnsButton).toBeVisible();
      }
    });
  });

  test.describe('Diff Review Page', () => {
    test('should navigate to diff review page', async ({ page }) => {
      await page.goto(UI_BASE_URL);
      await page.getByRole('link', { name: /Diff Review/i }).click();

      await expect(page).toHaveURL(`${UI_BASE_URL}/diff`);
      await expect(page.locator('h1')).toContainText('Diff Review');
    });

    test('should have price book selection dropdowns', async ({ page }) => {
      await page.goto(`${UI_BASE_URL}/diff`);

      await expect(page.getByText('Old Price Book')).toBeVisible();
      await expect(page.getByText('New Price Book')).toBeVisible();

      // Check for select elements
      const selects = page.locator('select');
      await expect(selects).toHaveCount(2);
    });

    test('should have compare button', async ({ page }) => {
      await page.goto(`${UI_BASE_URL}/diff`);

      const compareButton = page.getByRole('button', { name: /Compare/i });
      await expect(compareButton).toBeVisible();
    });
  });

  test.describe('Export Center Page', () => {
    test('should navigate to export center', async ({ page }) => {
      await page.goto(UI_BASE_URL);
      await page.getByRole('link', { name: /Export Center/i }).click();

      await expect(page).toHaveURL(`${UI_BASE_URL}/export-center`);
      await expect(page.locator('h1')).toContainText('Export Center');
    });

    test('should display format option cards', async ({ page }) => {
      await page.goto(`${UI_BASE_URL}/export-center`);

      await expect(page.getByText('Excel (XLSX)')).toBeVisible();
      await expect(page.getByText('CSV')).toBeVisible();
      await expect(page.getByText('JSON')).toBeVisible();
    });

    test('should show format features', async ({ page }) => {
      await page.goto(`${UI_BASE_URL}/export-center`);

      await expect(page.getByText(/Multiple sheets/i)).toBeVisible();
      await expect(page.getByText(/Universal compatibility/i)).toBeVisible();
      await expect(page.getByText(/API-ready format/i)).toBeVisible();
    });
  });

  test.describe('Publish Page', () => {
    test('should navigate to publish page', async ({ page }) => {
      await page.goto(UI_BASE_URL);
      await page.getByRole('link', { name: /Publish/i }).click();

      await expect(page).toHaveURL(`${UI_BASE_URL}/publish`);
      await expect(page.locator('h1')).toContainText('Publish to Baserow');
    });

    test('should have price book selection', async ({ page }) => {
      await page.goto(`${UI_BASE_URL}/publish`);

      await expect(page.getByText('Select Price Book')).toBeVisible();
      const select = page.locator('select').first();
      await expect(select).toBeVisible();
    });

    test('should have dry run checkbox', async ({ page }) => {
      await page.goto(`${UI_BASE_URL}/publish`);

      const dryRunCheckbox = page.locator('input[type="checkbox"]#dry-run');
      await expect(dryRunCheckbox).toBeVisible();
      await expect(page.getByText(/Dry run.*preview/i)).toBeVisible();
    });

    test('should have publish button', async ({ page }) => {
      await page.goto(`${UI_BASE_URL}/publish`);

      const publishButton = page.getByRole('button', { name: /Run Dry Run|Publish to Baserow/i });
      await expect(publishButton).toBeVisible();
    });
  });

  test.describe('Settings Page', () => {
    test('should navigate to settings page', async ({ page }) => {
      await page.goto(UI_BASE_URL);
      await page.getByRole('link', { name: /Settings/i }).click();

      await expect(page).toHaveURL(`${UI_BASE_URL}/settings`);
      await expect(page.locator('h1')).toContainText('Settings');
    });

    test('should have theme switcher', async ({ page }) => {
      await page.goto(`${UI_BASE_URL}/settings`);

      await expect(page.getByText(/Theme Preference/i)).toBeVisible();
      await expect(page.getByText('Light')).toBeVisible();
      await expect(page.getByText('Dark')).toBeVisible();
      await expect(page.getByText('System')).toBeVisible();
    });

    test('should have table density options', async ({ page }) => {
      await page.goto(`${UI_BASE_URL}/settings`);

      await expect(page.getByText(/Table Density/i)).toBeVisible();
      await expect(page.getByText(/Comfortable/i)).toBeVisible();
      await expect(page.getByText(/Dense/i)).toBeVisible();
    });

    test('should have keyboard shortcuts reference', async ({ page }) => {
      await page.goto(`${UI_BASE_URL}/settings`);

      await expect(page.getByText(/Keyboard Shortcuts/i)).toBeVisible();
    });

    test('should have reset button', async ({ page }) => {
      await page.goto(`${UI_BASE_URL}/settings`);

      const resetButton = page.getByRole('button', { name: /Reset.*Settings/i });
      await expect(resetButton).toBeVisible();
    });
  });

  test.describe('Accessibility', () => {
    test('should have proper heading hierarchy on dashboard', async ({ page }) => {
      await page.goto(UI_BASE_URL);

      const h1 = page.locator('h1');
      await expect(h1).toHaveCount(1);
      await expect(h1).toContainText('Dashboard');
    });

    test('should have focus visible on buttons', async ({ page }) => {
      await page.goto(UI_BASE_URL);

      const uploadButton = page.getByRole('button', { name: /Upload/i }).first();
      if (await uploadButton.count() > 0) {
        await uploadButton.focus();
        // Button should have visible focus state
        await expect(uploadButton).toBeFocused();
      }
    });

    test('should support keyboard navigation', async ({ page }) => {
      await page.goto(UI_BASE_URL);

      // Press Tab to navigate
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');

      // Some element should have focus
      const focusedElement = page.locator(':focus');
      await expect(focusedElement).toBeVisible();
    });
  });

  test.describe('Dark Mode', () => {
    test('should toggle dark mode', async ({ page }) => {
      await page.goto(`${UI_BASE_URL}/settings`);

      // Click Dark theme
      const darkButton = page.getByRole('button', { name: 'Dark' });
      await darkButton.click();

      // Check if dark class is applied
      const html = page.locator('html');
      await expect(html).toHaveClass(/dark/);

      // Switch back to light
      const lightButton = page.getByRole('button', { name: 'Light' });
      await lightButton.click();

      // Dark class should be removed
      await expect(html).not.toHaveClass(/dark/);
    });
  });

  test.describe('Responsive Design', () => {
    test('should be responsive on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(UI_BASE_URL);

      // Page should still be visible and functional
      await expect(page.locator('h1')).toBeVisible();
    });

    test('should be responsive on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(UI_BASE_URL);

      await expect(page.locator('h1')).toBeVisible();
    });
  });
});
