import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { login, uniqueName } from './support/api';
import { authenticatePage, expectRenderedDocument, uploadPdf } from './support/documents';

test('all visual annotation tools persist on the rendered page, with replies, deletion and JSON export', async ({ page, request }) => {
  test.setTimeout(240_000);
  const token = await login(request);
  const { doc } = await uploadPdf(request, token);
  await authenticatePage(page, token);
  await page.goto(`/documents/${doc.id}`);
  await expectRenderedDocument(page);
  const text = uniqueName('Browser annotation');
  for (const [label, pointTool] of [
    ['Sticky note', true], ['Text box', true], ['Rubber stamp', true],
    ['Highlight', false], ['Underline', false], ['Strikethrough', false],
    ['Rectangle', false], ['Freehand', false],
  ] as const) {
    await page.getByRole('button', { name: label, exact: true }).click();
    await page.getByLabel('annotation text', { exact: true }).fill(`${text} ${label}`);
    const responsePromise = page.waitForResponse((response) => response.url().endsWith(`/documents/${doc.id}/annotations/`) && response.request().method() === 'POST', { timeout: 15_000 });
    const surface = page.locator('.dd-page-wrap');
    if (pointTool) {
      await surface.click({ position: { x: 100, y: 100 } });
    } else {
      await surface.hover({ position: { x: 100, y: 100 } });
      const bounds = (await surface.boundingBox())!;
      await page.mouse.down();
      await page.mouse.move(bounds.x + 250, bounds.y + 160, { steps: 6 });
      await page.mouse.up();
    }
    const response = await responsePromise;
    expect(response.status(), await response.text()).toBe(201);
    expect((await response.json()).content).toBe(`${text} ${label}`);
  }
  await expect(page.locator('.dd-note')).toHaveCount(3);
  await expect(page.locator('svg.dd-drawing polyline')).toHaveAttribute('points', /,/);
  await page.getByRole('tab', { name: 'Notes', exact: true }).click();
  const annotation = page.locator('.ap__item').filter({ hasText: `${text} Sticky note` });
  await expect(annotation).toBeVisible();
  await annotation.getByLabel('Add a reply', { exact: true }).fill('Browser reply persisted');
  await annotation.getByRole('button', { name: 'Post reply', exact: true }).click();
  await annotation.getByRole('button', { name: /1 reply/ }).click();
  await expect(annotation.getByText('Browser reply persisted', { exact: true })).toBeVisible();
  page.once('dialog', (dialog) => dialog.accept());
  await annotation.getByRole('button', { name: 'Delete annotation', exact: true }).click();
  await expect(annotation).toHaveCount(0);
  await expect(page.locator('.dd-note')).toHaveCount(2);
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: '↓ export', exact: true }).click();
  const download = await downloadPromise;
  const exported = JSON.parse(await readFile((await download.path())!, 'utf8'));
  expect(exported.document_id).toBe(doc.id);
  expect(exported.annotation_count).toBe(7);
  await page.reload();
  await expect(page.locator('.dd-note')).toHaveCount(2);
});
