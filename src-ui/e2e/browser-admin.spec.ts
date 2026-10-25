import { test, expect } from '@playwright/test';
import { adminUsername, authHeaders, baseURL, login, uniqueName } from './support/api';
import { authenticatePage } from './support/documents';
import { totp } from './support/totp';

test('TOTP enrollment, real authenticator login, one-use backup recovery and disable work through browser controls', async ({ page, request }) => {
  const admin = await login(request);
  const username = uniqueName('browser-otp');
  const password = 'Browser-otp-only-493!';
  const created = await request.post(`${baseURL}/api/v1/users/`, { headers: authHeaders(admin), data: { username, password } });
  expect(created.status(), await created.text()).toBe(201);
  const token = await login(request, username, password);
  await authenticatePage(page, token);
  await page.goto('/otp-setup');
  await page.getByRole('button', { name: 'Enable 2FA', exact: true }).click();
  const secret = await page.getByLabel('secret (manual entry)', { exact: true }).inputValue();
  await expect(page.getByAltText('TOTP enrolment QR code')).toBeVisible();
  await page.getByLabel('6-digit code from your app', { exact: true }).fill(totp(secret));
  await page.getByRole('button', { name: 'Verify & activate →', exact: true }).click();
  await expect(page.locator('.ot-codes code')).toHaveCount(8);
  const backup = (await page.locator('.ot-codes code').first().textContent())!.trim();
  await page.goto('/profile');
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await page.getByLabel('username', { exact: true }).fill(username);
  await page.getByLabel('password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Two-factor authentication', exact: true })).toBeVisible();
  const code = totp(secret);
  for (let index = 0; index < code.length; index++) {
    await page.getByLabel(`Digit ${index + 1}`, { exact: true }).fill(code[index]);
  }
  await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible();
  await page.goto('/profile');
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await page.getByLabel('username', { exact: true }).fill(username);
  await page.getByLabel('password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.getByRole('button', { name: 'Use a backup code', exact: true }).click();
  await page.getByLabel('backup code', { exact: true }).fill(backup);
  await page.getByRole('button', { name: 'Verify code' }).click();
  await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible();
  const reuse = await request.post(`${baseURL}/api/v1/auth/login/`, { data: { username, password, otp_code: backup } });
  expect(reuse.status()).toBe(400);
  await page.goto('/otp-setup');
  await page.getByLabel('current password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Disable 2FA', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Enable 2FA', exact: true })).toBeVisible();
});

test('administrator user, group and role creation persists with real permission and group assignments', async ({ page, request }) => {
  const token = await login(request);
  await authenticatePage(page, token);
  await page.goto('/admin/users');
  await expect(page.getByText(adminUsername, { exact: true }).first()).toBeVisible();
  await page.getByRole('button', { name: '+ Invite user', exact: true }).click();
  const username = uniqueName('browser-invited');
  await page.locator('#au-username').fill(username);
  await page.locator('#au-email').fill(`${username}@example.test`);
  await page.locator('#au-password').fill('Browser-invite-only-293!');
  await page.getByRole('button', { name: 'Create user', exact: true }).click();
  await expect(page.getByText(username, { exact: true })).toBeVisible();
  await page.goto('/admin/groups');
  await page.getByRole('button', { name: /New group|Create group|New/, exact: false }).first().click();
  const group = uniqueName('Browser group');
  await page.locator('#ag-name').fill(group);
  const groupResponse = page.waitForResponse((response) => response.url().endsWith('/api/v1/groups/') && response.request().method() === 'POST');
  await page.getByRole('button', { name: /Create|Save/, exact: true }).click();
  const createdGroup = await (await groupResponse).json();
  await expect(page.getByText(group, { exact: true })).toBeVisible();
  const permissions = await request.get(`${baseURL}/api/v1/permissions/`, { headers: authHeaders(token) });
  const permission = (await permissions.json()).find((item: { codename: string; namespace: string }) => item.namespace === 'documents' && item.codename === 'view_document');
  expect(permission).toBeTruthy();
  await page.goto('/admin/roles');
  await page.getByRole('button', { name: '+ New role', exact: true }).click();
  const role = uniqueName('Browser role');
  await page.locator('#ar-name').fill(role);
  await page.locator(`#rperm-${permission.id}`).check();
  await page.locator(`#rgroup-${createdGroup.id}`).check();
  const roleResponse = page.waitForResponse((response) => response.url().endsWith('/api/v1/roles/') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Create role', exact: true }).click();
  const createdRole = await (await roleResponse).json();
  expect(createdRole.permissions.some((item: { id: number }) => item.id === permission.id)).toBe(true);
  expect(createdRole.groups).toContain(createdGroup.id);
  const card = page.locator('.ar-card').filter({ hasText: role });
  await card.getByRole('button', { name: 'edit', exact: true }).click();
  await expect(page.locator(`#rperm-${permission.id}`)).toBeChecked();
  await expect(page.locator(`#rgroup-${createdGroup.id}`)).toBeChecked();
});

const screens = [
  ['/admin/roles', '/api/v1/roles/'],
  ['/admin/permissions', '/api/v1/permissions/'],
  ['/admin/storage', '/api/v1/storage/config/'],
  ['/sources', '/api/v1/sources/'],
  ['/classifier', '/api/v1/classifier/status/'],
  ['/barcode-config', '/api/v1/barcode/config/'],
  ['/ai-config', '/api/v1/ai/config/'],
  ['/zone-ocr', '/api/v1/zone-ocr-templates/'],
  ['/entity-browser', '/api/v1/entities/'],
  ['/search-analytics', '/api/v1/search/analytics/'],
  ['/synonyms', '/api/v1/search/synonyms/'],
  ['/curations', '/api/v1/search/curations/'],
  ['/audit-log', '/api/v1/audit-log/'],
  ['/scanner', '/api/v1/sources/scanners/'],
  ['/legal-holds', '/api/v1/legal-holds/'],
  ['/physical-locations', '/api/v1/physical-locations/tree/'],
  ['/charge-outs', '/api/v1/charge-outs/'],
  ['/notifications', '/api/v1/notifications/'],
  ['/notification-preferences', '/api/v1/notification-preferences/'],
] as const;

for (const [path, api] of screens) {
  test(`advertised configuration screen ${path} renders using its live API`, async ({ page, request }) => {
    await authenticatePage(page, await login(request));
    const errors: string[] = [];
    page.on('pageerror', (error) => errors.push(error.message));
    const response = page.waitForResponse((response) => new URL(response.url()).pathname === api && response.request().method() === 'GET', { timeout: 15_000 });
    await page.goto(path);
    if (path === '/scanner') await page.getByRole('button', { name: 'Discover scanners', exact: true }).click();
    const loaded = await response;
    expect(loaded.status(), `${api}: ${await loaded.text()}`).toBe(200);
    await expect(page.locator('.dv-screen')).toBeVisible();
    await expect(page.locator('.dv-screen')).not.toHaveText('');
    await page.waitForLoadState('networkidle');
    expect(errors).toEqual([]);
  });
}
