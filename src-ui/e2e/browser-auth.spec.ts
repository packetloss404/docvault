import { test, expect } from '@playwright/test';
import { adminUsername, adminPassword, login, userUsername, userPassword } from './support/api';
import { authenticatePage } from './support/documents';

test('password login, applied CSS, dashboard, theme, profile and logout', async ({ page }) => {
  await page.goto('/login');
  await expect(page.locator('.dv-auth')).toHaveCSS('position', 'fixed');
  await page.getByLabel('username', { exact: true }).fill(adminUsername);
  await page.getByLabel('password', { exact: true }).fill('Incorrect-browser-password');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('alert')).toContainText(/invalid credentials|login failed/i);
  await page.getByLabel('password', { exact: true }).fill(adminPassword);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible();
  await expect(page.getByText('Recent documents', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Admin', exact: true })).toBeVisible();
  const theme = await page.getByRole('button', { name: 'Toggle theme' }).getAttribute('title');
  await page.getByRole('button', { name: 'Toggle theme' }).click();
  await expect(page.getByRole('button', { name: 'Toggle theme' })).not.toHaveAttribute('title', theme!);
  await page.goto('/profile');
  await expect(page.getByRole('heading', { name: adminUsername })).toBeVisible();
  await expect(page.getByText(/^(superuser|staff)$/).first()).toBeVisible();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect.poll(() => page.evaluate(() => localStorage.getItem('docvault_token'))).toBeNull();
});

test('ordinary users have role-aware navigation and cannot load admin screens', async ({ page, request }) => {
  await authenticatePage(page, await login(request, userUsername, userPassword));
  await page.goto('/');
  await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Admin', exact: true })).toHaveCount(0);
  await page.goto('/admin/users');
  await expect(page).toHaveURL(/\/403$/);
  await expect(page.getByText(/access denied|permission|forbidden/i).first()).toBeVisible();
});
