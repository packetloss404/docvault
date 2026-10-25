import { APIRequestContext, expect, Page } from '@playwright/test';
import { createHash } from 'node:crypto';
import { authHeaders, baseURL, uniqueName } from './api';

export function makePdf(text: string, pages = 1): Buffer {
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    `<< /Type /Pages /Kids [${Array.from({ length: pages }, (_, i) => `${4 + i * 2} 0 R`).join(' ')}] /Count ${pages} >>`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ];
  for (let i = 0; i < pages; i++) {
    const content = `BT /F1 14 Tf 72 720 Td (${`${text} page ${i + 1}`.replace(/[\\()]/g, '\\$&')}) Tj ET`;
    objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents ${5 + i * 2} 0 R >>`);
    objects.push(`<< /Length ${Buffer.byteLength(content)} >>\nstream\n${content}\nendstream`);
  }
  let pdf = '%PDF-1.4\n';
  const offsets = [0];
  objects.forEach((object, i) => {
    offsets.push(Buffer.byteLength(pdf));
    pdf += `${i + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xref = Buffer.byteLength(pdf);
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  pdf += offsets.slice(1).map((offset) => `${offset.toString().padStart(10, '0')} 00000 n \n`).join('');
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(pdf);
}

export function sha256(bytes: Buffer): string {
  return createHash('sha256').update(bytes).digest('hex');
}

export async function waitForIngestion(request: APIRequestContext, token: string, taskId: string) {
  let documentId: number | undefined;
  await expect.poll(async () => {
    const response = await request.get(`${baseURL}/api/v1/tasks/?page_size=100`, { headers: authHeaders(token) });
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    const task = (body.results || body).find((item: { task_id: string }) => item.task_id === taskId);
    if (task?.status === 'failure') throw new Error(`Ingestion failed: ${task.result}`);
    documentId = task?.document;
    return task?.status;
  }, { timeout: 180_000, intervals: [500, 1000, 2000], message: `Task ${taskId} must complete through Celery` }).toBe('success');
  expect(documentId).toBeTruthy();
  const response = await request.get(`${baseURL}/api/v1/documents/${documentId}/`, { headers: authHeaders(token) });
  expect(response.ok()).toBeTruthy();
  return response.json();
}

export async function uploadPdf(request: APIRequestContext, token: string, title = uniqueName('Browser document'), pages = 1) {
  const bytes = makePdf(title, pages);
  const response = await request.post(`${baseURL}/api/v1/documents/upload/`, {
    headers: authHeaders(token),
    multipart: { title, document: { name: `${title}.pdf`, mimeType: 'application/pdf', buffer: bytes } },
  });
  expect(response.status(), await response.text()).toBe(202);
  const doc = await waitForIngestion(request, token, (await response.json()).task_id);
  return { doc, bytes };
}

export async function authenticatePage(page: Page, token: string) {
  await page.addInitScript((value) => {
    if (!sessionStorage.getItem('e2e-auth-initialized')) {
      localStorage.setItem('docvault_token', value);
      sessionStorage.setItem('e2e-auth-initialized', 'true');
    }
  }, token);
}

export async function expectRenderedDocument(page: Page) {
  const image = page.locator('.dd-image');
  await expect(image).toBeVisible();
  await expect.poll(() => image.evaluate((element: HTMLImageElement) => element.complete && element.naturalWidth > 100)).toBe(true);
  await expect(image).toHaveAttribute('src', /^blob:/);
}
