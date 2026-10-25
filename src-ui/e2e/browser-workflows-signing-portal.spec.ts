import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { authHeaders, baseURL, login, uniqueName } from './support/api';
import { authenticatePage, expectRenderedDocument, makePdf, sha256, uploadPdf } from './support/documents';

test('document workflow launch and transition collect real text, integer, boolean, date and select fields', async ({ page, request }) => {
  test.setTimeout(240_000);
  const token = await login(request);
  const { doc } = await uploadPdf(request, token);
  const create = async (path: string, data: object) => {
    const response = await request.post(`${baseURL}/api/v1${path}`, { headers: authHeaders(token), data });
    expect(response.status(), await response.text()).toBe(201);
    return response.json();
  };
  const workflow = await create('/workflow-templates/', { label: uniqueName('Browser approval') });
  const states = `/workflow-templates/${workflow.id}/states/`;
  const draft = await create(states, { label: 'Browser draft', initial: true });
  const done = await create(states, { label: 'Browser approved', final: true, completion: 100 });
  const transition = await create(`/workflow-templates/${workflow.id}/transitions/`, {
    label: 'Browser approve', origin_state: draft.id, destination_state: done.id,
  });
  const fields = `/workflow-templates/${workflow.id}/transitions/${transition.id}/fields/`;
  for (const [name, type] of [['Reason', 'text'], ['Count', 'integer'], ['Confirmed', 'boolean'], ['Date', 'date'], ['Decision', 'select']]) {
    await create(fields, { name: name.toLowerCase(), label: name, field_type: type, required: true,
      ...(type === 'select' ? { choices: ['approve', 'reject'] } : {}) });
  }
  await authenticatePage(page, token);
  await page.goto(`/documents/${doc.id}`);
  await page.getByRole('tab', { name: 'Workflows', exact: true }).click();
  await page.getByLabel('launch workflow', { exact: true }).selectOption({ label: workflow.label });
  await page.getByRole('button', { name: 'Launch', exact: true }).click();
  await expect(page.getByText('Browser draft', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /^Browser approve/ }).click();
  const dialog = page.getByRole('dialog', { name: 'Browser approve', exact: true });
  await dialog.getByLabel('Reason').fill('Reviewed in the real browser');
  await dialog.getByLabel('Count').fill('0');
  await dialog.getByLabel('Confirmed').selectOption('false');
  await dialog.getByLabel('Date').fill('2026-01-02');
  await dialog.getByLabel('Decision').selectOption('approve');
  await dialog.getByLabel('comment', { exact: true }).fill('Browser transition evidence');
  await dialog.getByRole('button', { name: 'Execute transition ↵', exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByText('Browser approved', { exact: true })).toBeVisible();
  await expect(page.getByText('Browser transition evidence', { exact: true })).toBeVisible();
});

test('create/send a signature request in the UI, review actual anonymous pages, sign and download the certificate', async ({ page, request, browser }) => {
  test.setTimeout(240_000);
  const token = await login(request);
  const { doc } = await uploadPdf(request, token, uniqueName('Browser contract'), 2);
  await authenticatePage(page, token);
  await page.goto(`/documents/${doc.id}`);
  await page.getByRole('button', { name: 'Request signature', exact: true }).click();
  await page.getByLabel('signer name', { exact: true }).fill('Browser Signer');
  await page.getByLabel('signer email', { exact: true }).fill('browser-signer@example.test');
  const createdResponse = page.waitForResponse((response) => response.url().endsWith(`/documents/${doc.id}/signature-request/`) && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Create signature request', exact: true }).click();
  const response = await createdResponse;
  expect(response.status(), await response.text()).toBe(201);
  const signatureRequest = await response.json();
  await expect(page).toHaveURL(new RegExp(`/signature-requests/${signatureRequest.id}$`));
  await page.getByRole('button', { name: 'Send →', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Remind', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: signatureRequest.title, exact: true })).toBeVisible();
  await page.goto('/signature-requests');
  await expect(page.getByRole('link', { name: signatureRequest.title, exact: true })).toBeVisible();
  const requestCard = page.locator('.sr-card').filter({ has: page.getByRole('link', { name: signatureRequest.title, exact: true }) });
  await expect(requestCard.getByText('Browser Signer', { exact: true })).toBeVisible();
  const context = await browser.newContext();
  const signer = await context.newPage();
  await signer.goto(`${baseURL}/sign/${signatureRequest.signers[0].token}`);
  const image = signer.getByAltText('Signing document, page 1');
  await expect(image).toBeVisible();
  await expect.poll(() => image.evaluate((element: HTMLImageElement) => element.complete && element.naturalWidth > 100)).toBe(true);
  await signer.getByTitle('View page 2', { exact: true }).click();
  await expect(signer.getByAltText('Signing document, page 2')).toBeVisible();
  await expect(signer.getByText('2 of 2 marked', { exact: true })).toBeVisible();
  await signer.getByRole('button', { name: 'Click to sign', exact: true }).click();
  await signer.getByRole('button', { name: 'Sign & complete →', exact: true }).click();
  await expect(signer.getByText('Thank you! Your signature has been recorded.', { exact: true })).toBeVisible();
  await context.close();
  await page.goto(`/signature-requests/${signatureRequest.id}`);
  const certificatePromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download certificate', exact: true }).click();
  const certificate = await certificatePromise;
  expect((await readFile((await certificate.path())!)).subarray(0, 5).toString()).toBe('%PDF-');
});

test('create a branded portal, submit a real public document and approve it into a rendered managed document', async ({ page, request, browser }) => {
  test.setTimeout(240_000);
  const token = await login(request);
  const portalName = uniqueName('Browser portal');
  const slug = uniqueName('browser-portal').toLowerCase();
  await authenticatePage(page, token);
  await page.goto('/portals');
  await page.getByRole('button', { name: '+ New portal', exact: true }).click();
  await page.getByLabel('name', { exact: true }).fill(portalName);
  await page.getByLabel('slug', { exact: true }).fill(slug);
  await page.getByLabel('welcome text', { exact: true }).fill('Submit acceptance documents here.');
  await page.getByRole('checkbox', { name: 'require name', exact: true }).check();
  await page.getByRole('checkbox', { name: 'require email', exact: true }).check();
  const createdPortal = page.waitForResponse((response) => response.url().endsWith('/api/v1/portals/') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Create', exact: true }).click();
  const portalResponse = await createdPortal;
  expect(portalResponse.status(), await portalResponse.text()).toBe(201);
  expect(await portalResponse.json()).toMatchObject({ require_name: true, require_email: true });
  await expect(page.getByText(portalName, { exact: true })).toBeVisible();
  const context = await browser.newContext();
  const publicPage = await context.newPage();
  await publicPage.goto(`${baseURL}/portal/${slug}`);
  await expect(publicPage.getByText('Submit acceptance documents here.', { exact: true })).toBeVisible();
  await publicPage.getByLabel('your name').fill('External Browser Submitter');
  await publicPage.getByLabel('your email').fill('external-browser@example.test');
  const name = `${uniqueName('public-browser-upload')}.pdf`;
  const bytes = makePdf(name);
  await publicPage.locator('input[type=file]').setInputFiles({ name, mimeType: 'application/pdf', buffer: bytes });
  await publicPage.getByRole('button', { name: 'Upload →', exact: true }).click();
  await expect(publicPage.getByText('Your document has been uploaded. Thank you.', { exact: true })).toBeVisible();
  await context.close();
  await page.goto('/submission-review');
  const submission = page.locator('.sv-row').filter({ hasText: name });
  await expect(submission).toBeVisible();
  page.once('dialog', (dialog) => dialog.accept());
  await submission.getByRole('button', { name: 'Accept', exact: true }).click();
  await expect(async () => {
    await page.getByRole('button', { name: '↻ Refresh', exact: true }).click();
    await expect(submission.getByRole('link', { name: 'Document', exact: true })).toBeVisible({ timeout: 5000 });
  }).toPass({ timeout: 180_000, intervals: [1000, 2000] });
  await submission.getByRole('link', { name: 'Document', exact: true }).click();
  await expectRenderedDocument(page);
  await expect(page.getByRole('heading').filter({ hasText: name.replace(/\.pdf$/, '') })).toBeVisible();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Download', exact: true }).click();
  const download = await downloadPromise;
  expect(sha256(await readFile((await download.path())!))).toBe(sha256(bytes));
});
