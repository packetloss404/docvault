import { APIRequestContext, expect } from '@playwright/test';

export const baseURL = process.env['E2E_BASE_URL'] || 'http://127.0.0.1:18086';
export const adminUsername = process.env['E2E_ADMIN_USERNAME'] || 'e2e-admin';
export const adminPassword = process.env['E2E_ADMIN_PASSWORD'] || 'E2e-only-password-123!';
export const userUsername = process.env['E2E_USER_USERNAME'] || 'e2e-user';
export const userPassword = process.env['E2E_USER_PASSWORD'] || 'E2e-only-password-123!';

export function authHeaders(token: string): { Authorization: string } {
  return { Authorization: `Token ${token}` };
}

export async function login(
  request: APIRequestContext,
  username = adminUsername,
  password = adminPassword,
): Promise<string> {
  const response = await request.post(`${baseURL}/api/v1/auth/login/`, {
    data: { username, password },
  });
  expect(response.ok(), `Login failed (${response.status()}): ${await response.text()}`).toBeTruthy();
  const result = await response.json();
  expect(result.token, 'Password login must return a token for the isolated E2E user').toBeTruthy();
  return result.token;
}

export function uniqueName(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}
