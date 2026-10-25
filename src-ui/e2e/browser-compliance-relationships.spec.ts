import { test, expect } from '@playwright/test';
import { authHeaders, baseURL, login, uniqueName } from './support/api';
import { authenticatePage, expectRenderedDocument, uploadPdf } from './support/documents';

test('a legal-hold banner belongs only to the preserved document and disappears after release', async ({ page, request }) => {
  test.setTimeout(240_000);
  const token = await login(request);
  const { doc: held } = await uploadPdf(request, token, uniqueName('Held browser record'));
  const { doc: unheld } = await uploadPdf(request, token, uniqueName('Unheld browser record'));
  const headers = authHeaders(token);
  const created = await request.post(`${baseURL}/api/v1/legal-holds/`, {
    headers, data: {
      name: uniqueName('Browser preservation'),
      criteria: [{ criteria_type: 'specific_documents', value: { document_ids: [held.id] } }],
    },
  });
  expect(created.status(), await created.text()).toBe(201);
  const hold = await created.json();
  const activated = await request.post(`${baseURL}/api/v1/legal-holds/${hold.id}/activate/`, { headers, data: {} });
  expect(activated.status(), await activated.text()).toBe(200);
  expect((await activated.json()).documents_captured).toBe(1);
  try {
    await authenticatePage(page, token);
    await page.goto(`/documents/${held.id}`);
    await expectRenderedDocument(page);
    await expect(page.getByRole('alert').filter({ hasText: 'legal hold active' })).toBeVisible();
    await page.goto(`/documents/${unheld.id}`);
    await expectRenderedDocument(page);
    await expect(page.getByRole('heading', { name: unheld.title, exact: true })).toBeVisible();
    await expect(page.getByText('legal hold active', { exact: true })).toHaveCount(0);
  } finally {
    const released = await request.post(`${baseURL}/api/v1/legal-holds/${hold.id}/release/`, { headers, data: { reason: 'Browser acceptance finished.' } });
    expect(released.status(), await released.text()).toBe(200);
  }
  await page.goto(`/documents/${held.id}`);
  await expectRenderedDocument(page);
  await expect(page.getByText('legal hold active', { exact: true })).toHaveCount(0);
});

test('a real relationship renders two graph nodes and its connecting edge in the browser', async ({ page, request }) => {
  const token = await login(request);
  const headers = authHeaders(token);
  const documents: { id: number; title: string }[] = [];
  for (const label of ['Graph source', 'Graph target']) {
    const response = await request.post(`${baseURL}/api/v1/documents/`, { headers, data: { title: uniqueName(label) } });
    expect(response.status(), await response.text()).toBe(201);
    documents.push(await response.json());
  }
  const typeResponse = await request.post(`${baseURL}/api/v1/relationship-types/`, {
    headers, data: { slug: uniqueName('browser-link'), label: 'Browser reference', is_directional: true },
  });
  expect(typeResponse.status(), await typeResponse.text()).toBe(201);
  const type = await typeResponse.json();
  const relationship = await request.post(`${baseURL}/api/v1/documents/${documents[0].id}/relationships/`, {
    headers, data: { target_document: documents[1].id, relationship_type: type.id },
  });
  expect(relationship.status(), await relationship.text()).toBe(201);
  await authenticatePage(page, token);
  await page.goto(`/documents/${documents[0].id}/graph`);
  await expect(page.getByRole('heading', { name: 'Relationship graph', exact: true })).toBeVisible();
  await expect(page.locator('.rg__node')).toHaveCount(2);
  await expect(page.locator('.rg__svg > line')).toHaveCount(1);
  await expect(page.locator('.rg__edgelabel')).toHaveText('Browser reference');
  for (const document of documents) {
    const node = page.locator('.rg__node').filter({ has: page.locator('.rg__id', { hasText: String(document.id) }) });
    await expect(node.locator('circle')).toBeVisible();
    await expect(node.locator('.rg__label')).toContainText(document.title.slice(0, 20));
  }
  const line = page.locator('.rg__svg > line');
  await expect.poll(() => line.evaluate((element) => Math.hypot(
    Number(element.getAttribute('x2')) - Number(element.getAttribute('x1')),
    Number(element.getAttribute('y2')) - Number(element.getAttribute('y1')),
  ))).toBeGreaterThan(20);
  const minimumAnimatedLength = await line.evaluate((element) => new Promise<number>((resolve) => {
    let frames = 0;
    let minimum = Infinity;
    const sample = () => {
      minimum = Math.min(minimum, Math.hypot(
        Number(element.getAttribute('x2')) - Number(element.getAttribute('x1')),
        Number(element.getAttribute('y2')) - Number(element.getAttribute('y1')),
      ));
      if (++frames === 120) resolve(minimum);
      else requestAnimationFrame(sample);
    };
    requestAnimationFrame(sample);
  }));
  expect(minimumAnimatedLength).toBeGreaterThan(20);
});
