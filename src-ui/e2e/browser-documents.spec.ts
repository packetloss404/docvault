import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { authHeaders, baseURL, login, uniqueName } from './support/api';
import { authenticatePage, expectRenderedDocument, makePdf, sha256, uploadPdf, waitForIngestion } from './support/documents';

test('UI upload processes a multipage PDF and renders pages, OCR text and checksum-correct downloads', async ({ page, request }) => {
  test.setTimeout(240_000);
  const token = await login(request);
  const name = uniqueName('browser-pdf');
  const bytes = makePdf(`Acceptance ${name}`, 2);
  await authenticatePage(page, token);
  const socketPromise = page.waitForEvent('websocket', { predicate: (socket) => socket.url().includes('/ws/status/') });
  await page.goto('/');
  const socket = await socketPromise;
  const frames: { task_id: string; status: string }[] = [];
  socket.on('framereceived', ({ payload }) => {
    frames.push(JSON.parse(payload.toString()));
  });
  const [chooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    page.getByRole('button', { name: /^Upload/ }).click(),
  ]);
  const uploadResponse = page.waitForResponse((response) => response.url().endsWith('/api/v1/documents/upload/') && response.request().method() === 'POST');
  await chooser.setFiles({ name: `${name}.pdf`, mimeType: 'application/pdf', buffer: bytes });
  const response = await uploadResponse;
  expect(response.status(), await response.text()).toBe(202);
  const taskId = (await response.json()).task_id;
  const doc = await waitForIngestion(request, token, taskId);
  await expect.poll(() => frames.some((frame) => frame.task_id === taskId && frame.status === 'success')).toBe(true);
  await expect(page.getByText(`${name}.pdf`, { exact: true }).first()).toBeVisible();
  expect(doc.content).toContain(name);
  expect(doc.page_count).toBe(2);
  await page.goto(`/documents/${doc.id}`);
  await expectRenderedDocument(page);
  const firstPage = await page.locator('.dd-image').getAttribute('src');
  await page.getByRole('button', { name: 'Next page', exact: true }).click();
  await expect(page.getByAltText('Document preview, page 2')).toBeVisible();
  await expectRenderedDocument(page);
  await expect(page.locator('.dd-image')).not.toHaveAttribute('src', firstPage!);
  await page.getByRole('button', { name: 'Zoom in', exact: true }).click();
  await expect(page.getByTitle('Reset zoom', { exact: true })).toHaveText('125%');
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Download', exact: true }).click();
  const download = await downloadPromise;
  expect(sha256(await readFile((await download.path())!))).toBe(sha256(bytes));
  expect(doc.checksum).toBe(sha256(bytes));
  expect(doc.archive_filename, 'Real OCR processing must produce the advertised PDF archive').toBeTruthy();
  const archivePromise = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Archive', exact: true }).click();
  const archive = await archivePromise;
  expect(sha256(await readFile((await archive.path())!))).toBe(doc.archive_checksum);
  await page.getByRole('tab', { name: 'Content', exact: true }).click();
  await expect(page.locator('pre')).toContainText(name);
  const newVersion = await request.post(`${baseURL}/api/v1/documents/${doc.id}/files/`, {
    headers: authHeaders(token),
    multipart: { document: { name: `${name}-new.pdf`, mimeType: 'application/pdf', buffer: makePdf(`${name} revised`, 3) }, comment: 'Browser three-page version' },
  });
  expect(newVersion.status(), await newVersion.text()).toBe(201);
  await page.reload();
  await expect(page.locator('.dd-pages')).toContainText('1 / 3');
  await page.getByRole('button', { name: 'Next page', exact: true }).click();
  await page.getByRole('button', { name: 'Next page', exact: true }).click();
  await expect(page.getByAltText('Document preview, page 3')).toBeVisible();
  await expectRenderedDocument(page);
  await page.getByRole('tab', { name: 'Versions', exact: true }).click();
  const firstVersion = page.locator('.dd-version').filter({ has: page.getByText('v1', { exact: true }) });
  await firstVersion.getByRole('button', { name: 'activate', exact: true }).click();
  await expect(page.locator('.dd-pages')).toContainText('1 / 2');
  await expectRenderedDocument(page);
  const restored = await request.get(`${baseURL}/api/v1/documents/${doc.id}/download/`, { headers: authHeaders(token) });
  expect(sha256(await restored.body())).toBe(sha256(bytes));
});

test('real drag-and-drop image upload runs OCR and produces a rendered document', async ({ page, request, browser }) => {
  test.setTimeout(240_000);
  const token = await login(request);
  const name = uniqueName('browser-image');
  const imagePage = await browser.newPage();
  await imagePage.setContent(`<html><body style="margin:0;background:white;font:36px Arial;padding:60px;width:1000px;height:600px"><h1>Invoice ${name}</h1><p>Acceptance image document</p><p>Total amount 123 dollars</p></body></html>`);
  const bytes = await imagePage.screenshot({ type: 'png' });
  await imagePage.close();
  await authenticatePage(page, token);
  await page.goto('/');
  const uploadResponse = page.waitForResponse((response) => response.url().endsWith('/api/v1/documents/upload/') && response.request().method() === 'POST');
  await page.evaluate(({ data, filename }) => {
    const transfer = new DataTransfer();
    transfer.items.add(new File([new Uint8Array(data)], filename, { type: 'image/png' }));
    document.dispatchEvent(new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer: transfer }));
    document.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: transfer }));
  }, { data: Array.from(bytes), filename: `${name}.png` });
  const response = await uploadResponse;
  expect(response.status(), await response.text()).toBe(202);
  const doc = await waitForIngestion(request, token, (await response.json()).task_id);
  expect(doc.content.toLowerCase()).toContain('acceptance image document');
  await page.goto(`/documents/${doc.id}`);
  await expectRenderedDocument(page);
  const original = await request.get(`${baseURL}/api/v1/documents/${doc.id}/download/`, { headers: authHeaders(token) });
  expect(sha256(await original.body())).toBe(sha256(bytes));
});

test('organize screens create taxonomy and document edits persist through the real API', async ({ page, request }) => {
  test.setTimeout(240_000);
  const token = await login(request);
  const { doc } = await uploadPdf(request, token);
  const tag = uniqueName('Browser tag');
  const correspondent = uniqueName('Browser sender');
  const cabinet = uniqueName('Browser cabinet');
  await authenticatePage(page, token);
  for (const [path, selector, name] of [
    ['/tags', '#tag-name', tag], ['/correspondents', '#corr-name', correspondent], ['/cabinets', '#cab-name', cabinet],
  ]) {
    await page.goto(path);
    await page.getByRole('button', { name: '+ New', exact: true }).click();
    await page.locator(selector).fill(name);
    await page.getByRole('button', { name: 'Save', exact: true }).click();
    await expect(page.getByText(name, { exact: true }).first()).toBeVisible();
  }
  const parentResponse = await request.get(`${baseURL}/api/v1/cabinets/`, { headers: authHeaders(token), params: { search: cabinet } });
  expect(parentResponse.ok()).toBeTruthy();
  const parent = (await parentResponse.json()).results.find((item: { name: string }) => item.name === cabinet);
  expect(parent).toBeTruthy();
  const childNames = [`${cabinet} child A`, `${cabinet} child B`];
  const children: { id: number; parent: number }[] = [];
  for (const name of childNames) {
    await page.getByRole('button', { name: '+ New', exact: true }).click();
    await page.getByLabel('name', { exact: true }).fill(name);
    await page.getByLabel('parent cabinet', { exact: true }).selectOption({ label: cabinet });
    const created = page.waitForResponse((response) => response.url().endsWith('/api/v1/cabinets/') && response.request().method() === 'POST');
    await page.getByRole('button', { name: 'Save', exact: true }).click();
    const response = await created;
    expect(response.status(), await response.text()).toBe(201);
    const child = await response.json();
    expect(child.parent).toBe(parent.id);
    children.push(child);
    await expect(page.locator('.cab-list').getByText(name, { exact: true })).toBeVisible();
  }
  const source = page.locator('.cab-list .cab-row').filter({ has: page.locator('.cab-name', { hasText: childNames[1] }) }).locator('.cab-handle');
  const target = page.locator('.cab-list .cab-row').filter({ has: page.locator('.cab-name', { hasText: childNames[0] }) });
  await source.scrollIntoViewIfNeeded();
  const from = (await source.boundingBox())!;
  const to = (await target.boundingBox())!;
  const moved = page.waitForResponse((response) => response.url().endsWith(`/api/v1/cabinets/${children[1].id}/move/`) && response.request().method() === 'POST', { timeout: 15_000 });
  await source.hover();
  await page.mouse.down();
  await page.mouse.move(from.x + from.width / 2 + 8, from.y + from.height / 2, { steps: 3 });
  await page.mouse.move(to.x + 20, to.y + to.height / 4, { steps: 12 });
  await page.mouse.up();
  const moveResponse = await moved;
  expect(moveResponse.status(), await moveResponse.text()).toBe(200);
  await page.reload();
  await expect.poll(async () => {
    const response = await request.get(`${baseURL}/api/v1/cabinets/`, { headers: authHeaders(token), params: { search: cabinet } });
    expect(response.ok()).toBeTruthy();
    const saved: { id: number; parent: number | null }[] = (await response.json()).results;
    expect(saved.filter((item) => children.some((child) => child.id === item.id)).every((item) => item.parent === parent.id)).toBe(true);
    return saved.filter((item) => children.some((child) => child.id === item.id)).map((item) => item.id);
  }).toEqual([children[1].id, children[0].id]);
  await expect(page.locator('.cab-list').getByText(childNames[1], { exact: true })).toBeVisible();
  const displayed = await page.locator('.cab-list .cab-name').allTextContents();
  expect(displayed.indexOf(childNames[1])).toBeLessThan(displayed.indexOf(childNames[0]));
  await page.goto(`/documents/${doc.id}`);
  await page.getByRole('button', { name: 'Edit', exact: true }).click();
  const title = uniqueName('Edited title');
  await page.getByLabel('title', { exact: true }).fill(title);
  await page.getByLabel('correspondent', { exact: true }).selectOption({ label: correspondent });
  await page.getByLabel('cabinet', { exact: true }).selectOption({ label: cabinet });
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
  await page.getByRole('button', { name: '+ tag', exact: true }).click();
  await page.getByRole('button', { name: tag, exact: true }).click();
  await expect(page.getByRole('button', { name: `Remove tag ${tag}`, exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
  await expect(page.getByText(correspondent, { exact: true })).toBeVisible();
  await expect(page.getByText(cabinet, { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: `Remove tag ${tag}`, exact: true })).toBeVisible();
});
