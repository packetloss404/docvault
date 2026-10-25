import { test, expect } from '@playwright/test';
import { login, uniqueName } from './support/api';
import { authenticatePage, uploadPdf } from './support/documents';

test('real document chat renders the known PDF fact and cites its source through the configured LLM', async ({ page, request }) => {
  test.skip(process.env['E2E_INTEGRATIONS'] !== '1', 'Run the real Ollama integration profile to verify AI answers.');
  test.setTimeout(240_000);
  const token = await login(request);
  const { doc } = await uploadPdf(request, token, `Alice Johnson visited Chicago. Invoice identifier ORBIT73491 ${uniqueName('Browser AI')}`);
  await authenticatePage(page, token);
  await page.goto(`/documents/${doc.id}`);
  await page.getByRole('tab', { name: 'Ask AI', exact: true }).click();
  await page.getByLabel('Ask about this document', { exact: true }).fill('What is the invoice identifier? Reply with its exact value.');
  await page.getByRole('button', { name: 'Ask', exact: true }).click();
  const answer = page.locator('.ch__turn.dv-callout .ch__body');
  await expect(answer).toContainText('ORBIT73491', { timeout: 120_000 });
  await expect(page.locator('.ch__cites')).toContainText(doc.title);
  await expect(answer).not.toContainText('An error occurred.');
  await page.goto('/entity-browser');
  await page.getByLabel('Filter entities by value', { exact: true }).fill('Alice Johnson');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  const entity = page.locator('.eb-row').filter({ hasText: 'Alice Johnson' }).first();
  await expect(entity).toBeVisible();
  await entity.click();
  await expect(page.getByText('Co-occurring entities', { exact: true })).toBeVisible();
  await expect(page.locator('.eb-cooc')).toContainText(/Chicago/i);
});
