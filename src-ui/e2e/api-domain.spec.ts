import { APIRequestContext, expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { authHeaders, login, uniqueName, userUsername, userPassword } from './support/api';
import { makePdf, sha256, uploadPdf } from './support/documents';

const api = '/api/v1';

async function json(request: APIRequestContext, token: string, method: string, path: string, data?: unknown, expected = 200): Promise<any> {
  const response = await request.fetch(`${api}${path}`, { method, headers: authHeaders(token), data });
  expect(response.status(), `${method} ${path}: ${await response.text()}`).toBe(expected);
  return expected === 204 ? null : response.json();
}

async function document(request: APIRequestContext, token: string) {
  return json(request, token, 'POST', '/documents/', { title: uniqueName('domain-document'), content: 'Domain acceptance evidence.' }, 201);
}

async function ingestText(request: APIRequestContext, token: string, fields: Record<string, string> = {}) {
  const content = Buffer.from(`Full stack acceptance ${uniqueName('content')}. This document was uploaded over HTTP and processed by the independent Celery worker.`);
  const filename = `${uniqueName('domain-upload')}.txt`;
  const upload = await request.post(`${api}/documents/upload/`, {
    headers: authHeaders(token), multipart: { ...fields, document: { name: filename, mimeType: 'text/plain', buffer: content } },
  });
  expect(upload.status(), await upload.text()).toBe(202);
  const taskId = (await upload.json()).task_id;
  let task: any;
  await expect.poll(async () => {
    const result = await json(request, token, 'GET', `/tasks/?page_size=100`);
    task = (result.results ?? result).find((item: any) => item.task_id === taskId);
    if (task?.status === 'failure') throw new Error(`Real ingestion failed: ${task.result}`);
    return task?.status;
  }, { timeout: 90_000, message: `Real Celery ingestion ${taskId}` }).toBe('success');
  expect(task.document, task.result).toBeTruthy();
  return { document: await json(request, token, 'GET', `/documents/${task.document}/`), content };
}

test('comments, annotations with replies, document locking, public password shares and revocation', async ({ request }) => {
  const token = await login(request, userUsername, userPassword);
  const { document: doc, content } = await ingestText(request, token);
  const comment = await json(request, token, 'POST', `/documents/${doc.id}/comments/`, { text: 'Review this original.' }, 201);
  await json(request, token, 'PATCH', `/documents/${doc.id}/comments/${comment.id}/`, { text: 'Reviewed original.' });
  expect((await json(request, token, 'GET', `/documents/${doc.id}/comments/`)).find((item: any) => item.id === comment.id).text).toBe('Reviewed original.');
  await json(request, token, 'DELETE', `/documents/${doc.id}/comments/${comment.id}/`, undefined, 204);

  for (const type of ['highlight', 'underline', 'strikethrough', 'sticky_note', 'freehand', 'rectangle', 'text_box', 'rubber_stamp']) {
    const annotation = await json(request, token, 'POST', `/documents/${doc.id}/annotations/`, {
      page: 1, annotation_type: type, coordinates: { x: 0.1, y: 0.2, width: 0.3, height: 0.1 }, content: type,
    }, 201);
    await json(request, token, 'POST', `/documents/${doc.id}/annotations/${annotation.id}/replies/`, { text: 'Confirmed annotation.' }, 201);
    const updated = await json(request, token, 'PATCH', `/documents/${doc.id}/annotations/${annotation.id}/`, { content: `Updated ${type}` });
    expect(updated.content).toBe(`Updated ${type}`);
    expect((await json(request, token, 'GET', `/documents/${doc.id}/annotations/${annotation.id}/replies/`))[0].text).toBe('Confirmed annotation.');
    await json(request, token, 'DELETE', `/documents/${doc.id}/annotations/${annotation.id}/`, undefined, 204);
  }
  await json(request, token, 'POST', `/documents/${doc.id}/checkout/`, { block_new_uploads: true }, 201);
  expect((await json(request, token, 'GET', `/documents/${doc.id}/checkout_status/`)).checked_out).toBe(true);
  await json(request, token, 'POST', `/documents/${doc.id}/checkout/`, {}, 409);
  await json(request, token, 'POST', `/documents/${doc.id}/checkin/`, {});
  expect((await json(request, token, 'GET', `/documents/${doc.id}/checkout_status/`)).checked_out).toBe(false);

  const share = await json(request, token, 'POST', `/documents/${doc.id}/share/`, { password: 'Share-acceptance-123!', expiration_hours: 1 }, 201);
  expect(share.has_password).toBe(true);
  expect(share.expiration).toBeTruthy();
  expect((await (await request.get(`${api}/share/${share.slug}/`)).json()).requires_password).toBe(true);
  expect((await request.get(`${api}/share/${share.slug}/download/`)).status()).toBe(403);
  expect((await request.post(`${api}/share/${share.slug}/`, { data: { password: 'wrong' } })).status()).toBe(403);
  const unlock = await request.post(`${api}/share/${share.slug}/`, { data: { password: 'Share-acceptance-123!' } });
  expect(unlock.status()).toBe(200);
  const proof = await unlock.json();
  const download = await request.get(`${api}/share/${share.slug}/download/?token=${encodeURIComponent(proof.download_token)}`);
  expect(download.status(), await download.text()).toBe(200);
  expect(await download.body()).toEqual(content);
  expect((await json(request, token, 'GET', '/share-links/')).find((item: any) => item.id === share.id).download_count).toBe(1);
  await json(request, token, 'DELETE', `/share-links/${share.id}/`, undefined, 204);
  expect((await request.get(`${api}/share/${share.slug}/`)).status()).toBe(404);
  const expiring = await json(request, token, 'POST', `/documents/${doc.id}/share/`, { expiration: new Date(Date.now() + 1000).toISOString() }, 201);
  expect((await request.get(`${api}/share/${expiring.slug}/`)).status()).toBe(200);
  await expect.poll(async () => (await request.get(`${api}/share/${expiring.slug}/`)).status()).toBe(404);
  expect((await request.get(`${api}/share/${expiring.slug}/download/`)).status()).toBe(404);
});

test('workflow states, all transition field types, conditions, state actions and audit log', async ({ request }) => {
  const admin = await login(request);
  const token = await login(request, userUsername, userPassword);
  const doc = await document(request, token);
  const tag = await json(request, admin, 'POST', '/tags/', { name: uniqueName('workflow-tag') }, 201);
  const workflow = await json(request, admin, 'POST', '/workflow-templates/', { label: uniqueName('acceptance-workflow') }, 201);
  const states = `/workflow-templates/${workflow.id}/states/`;
  const draft = await json(request, admin, 'POST', states, { label: 'Draft', initial: true }, 201);
  const done = await json(request, admin, 'POST', states, { label: 'Approved', final: true, completion: 100 }, 201);
  const transition = await json(request, admin, 'POST', `/workflow-templates/${workflow.id}/transitions/`, {
    label: 'Approve', origin_state: draft.id, destination_state: done.id, condition: "document.title != ''",
  }, 201);
  const fields = `/workflow-templates/${workflow.id}/transitions/${transition.id}/fields/`;
  for (const [name, field_type] of [['reason', 'char'], ['notes', 'text'], ['count', 'integer'], ['confirmed', 'boolean'], ['date', 'date'], ['choice', 'select']]) {
    const created = await json(request, admin, 'POST', fields, {
      name, label: name, field_type, required: true, ...(field_type === 'select' ? { choices: ['approve', 'reject'] } : {}),
    }, 201);
    if (field_type === 'select') expect(created.choices).toEqual(['approve', 'reject']);
  }
  await json(request, admin, 'POST', `${states}${done.id}/actions/`, {
    label: 'Tag approved document', when: 'on_entry', backend_path: 'workflows.actions.tags.AddTagAction', backend_data: { tag_ids: [tag.id] },
  }, 201);
  const instance = await json(request, token, 'POST', `/documents/${doc.id}/workflows/launch/`, { workflow_template_id: workflow.id }, 201);
  const base = `/documents/${doc.id}/workflows/${instance.id}`;
  expect((await json(request, token, 'GET', `${base}/available-transitions/`))[0].id).toBe(transition.id);
  await json(request, token, 'POST', `${base}/transitions/${transition.id}/execute/`, {}, 400);
  const values = { reason: 'Reviewed', notes: 'Evidence', count: 0, confirmed: false, date: '2026-01-02', choice: 'approve' };
  await json(request, token, 'POST', `${base}/transitions/${transition.id}/execute/`, { field_values: { ...values, count: 'invalid' } }, 400);
  const completed = await json(request, token, 'POST', `${base}/transitions/${transition.id}/execute/`, { field_values: values, comment: 'Approved live' });
  expect(completed.is_complete).toBe(true);
  expect(completed.context).toMatchObject(values);
  expect((await json(request, token, 'GET', `/documents/${doc.id}/`)).tag_ids).toContain(tag.id);
  expect((await json(request, token, 'GET', `${base}/log/`)).some((entry: any) => entry.comment === 'Approved live')).toBe(true);
});

test('automatic workflow escalation is performed by the independent scheduled worker', async ({ request }) => {
  const admin = await login(request);
  const doc = await document(request, admin);
  const workflow = await json(request, admin, 'POST', '/workflow-templates/', { label: uniqueName('escalation-workflow') }, 201);
  const states = `/workflow-templates/${workflow.id}/states/`;
  const pending = await json(request, admin, 'POST', states, { label: 'Waiting', initial: true }, 201);
  const overdue = await json(request, admin, 'POST', states, { label: 'Escalated', final: true }, 201);
  const transition = await json(request, admin, 'POST', `/workflow-templates/${workflow.id}/transitions/`, { label: 'Escalate', origin_state: pending.id, destination_state: overdue.id }, 201);
  await json(request, admin, 'POST', `${states}${pending.id}/escalations/`, { transition: transition.id, amount: 0, unit: 'minutes' }, 201);
  const instance = await json(request, admin, 'POST', `/documents/${doc.id}/workflows/launch/`, { workflow_template_id: workflow.id }, 201);
  await expect.poll(async () => (await json(request, admin, 'GET', `/documents/${doc.id}/workflows/`)).find((item: any) => item.id === instance.id).current_state, { timeout: 30_000 }).toBe(overdue.id);
});

test('consumption, creation, update and scheduled rules apply real document automation', async ({ request }) => {
  const admin = await login(request);
  const tag = await json(request, admin, 'POST', '/tags/', { name: uniqueName('consumption-tag') }, 201);
  const type = await json(request, admin, 'POST', '/document-types/', { name: uniqueName('consumption-type') }, 201);
  const correspondent = await json(request, admin, 'POST', '/correspondents/', { name: uniqueName('consumption-correspondent') }, 201);
  const path = await json(request, admin, 'POST', '/storage-paths/', { name: uniqueName('consumption-path'), path: 'automation/{{ title }}' }, 201);
  const workflow = await json(request, admin, 'POST', '/workflow-templates/', { label: uniqueName('auto-launch'), auto_launch: true, document_type_ids: [type.id] }, 201);
  await json(request, admin, 'POST', `/workflow-templates/${workflow.id}/states/`, { label: 'Automatic start', initial: true }, 201);
  const rule = await json(request, admin, 'POST', '/workflow-rules/', { name: uniqueName('consumption-rule') }, 201);
  await json(request, admin, 'POST', `/workflow-rules/${rule.id}/triggers/`, { type: 'consumption', filter_filename: 'domain-upload-*.txt' }, 201);
  for (const [actionType, configuration] of [
    ['add_tag', { tag_ids: [tag.id] }], ['set_document_type', { document_type_id: type.id }],
    ['set_correspondent', { correspondent_id: correspondent.id }], ['set_storage_path', { storage_path_id: path.id }],
  ] as const) await json(request, admin, 'POST', `/workflow-rules/${rule.id}/actions/`, { type: actionType, configuration }, 201);
  try {
    const { document: ingested, content } = await ingestText(request, admin);
    expect(ingested).toMatchObject({ document_type: type.id, correspondent: correspondent.id, storage_path: path.id });
    expect(ingested.tag_ids).toContain(tag.id);
    expect(ingested.filename).toMatch(/^automation\//);
    expect(await (await request.get(`${api}/documents/${ingested.id}/download/`, { headers: authHeaders(admin) })).body()).toEqual(content);
    expect((await json(request, admin, 'GET', `/documents/${ingested.id}/workflows/`)).some((item: any) => item.workflow === workflow.id)).toBe(true);
  } finally {
    await json(request, admin, 'PATCH', `/workflow-rules/${rule.id}/`, { enabled: false });
    await json(request, admin, 'PATCH', `/workflow-templates/${workflow.id}/`, { auto_launch: false });
  }
  const title = uniqueName('creation-action');
  const field = await json(request, admin, 'POST', '/custom-fields/', { name: uniqueName('rule-field'), data_type: 'integer' }, 201);
  const creation = await json(request, admin, 'POST', '/workflow-rules/', { name: uniqueName('creation-rule') }, 201);
  await json(request, admin, 'POST', `/workflow-rules/${creation.id}/triggers/`, { type: 'document_added', match_pattern: title, matching_algorithm: 3 }, 201);
  await json(request, admin, 'POST', `/workflow-rules/${creation.id}/actions/`, { type: 'set_custom_field', configuration: { field_id: field.id, value: 42 } }, 201);
  const created = await json(request, admin, 'POST', '/documents/', { title }, 201);
  expect((await json(request, admin, 'GET', `/documents/${created.id}/custom-fields/`)).find((item: any) => item.field === field.id).value).toBe(42);
  const update = await json(request, admin, 'POST', '/workflow-rules/', { name: uniqueName('update-rule') }, 201);
  let scheduled: any;
  try {
    await json(request, admin, 'POST', `/workflow-rules/${update.id}/triggers/`, { type: 'document_updated', match_pattern: title, matching_algorithm: 3 }, 201);
    await json(request, admin, 'POST', `/workflow-rules/${update.id}/actions/`, { type: 'set_custom_field', configuration: { field_id: field.id, value: 43 } }, 201);
    await json(request, admin, 'PATCH', `/documents/${created.id}/`, { content: 'Trigger the real update rule.' });
    expect((await json(request, admin, 'GET', `/documents/${created.id}/custom-fields/`)).find((item: any) => item.field === field.id).value).toBe(43);
    const scheduledType = await json(request, admin, 'POST', '/document-types/', { name: uniqueName('scheduled-only-type') }, 201);
    await json(request, admin, 'PATCH', `/documents/${created.id}/`, { document_type: scheduledType.id });
    scheduled = await json(request, admin, 'POST', '/workflow-rules/', { name: uniqueName('scheduled-rule') }, 201);
    await json(request, admin, 'POST', `/workflow-rules/${scheduled.id}/triggers/`, { type: 'scheduled', filter_has_document_type: scheduledType.id }, 201);
    await json(request, admin, 'POST', `/workflow-rules/${scheduled.id}/actions/`, { type: 'set_custom_field', configuration: { field_id: field.id, value: 44 } }, 201);
    await expect.poll(async () => (await json(request, admin, 'GET', `/documents/${created.id}/custom-fields/`)).find((item: any) => item.field === field.id).value, { timeout: 30_000, message: 'Real Beat/worker must run the scheduled automation rule.' }).toBe(44);
  } finally {
    for (const rule of [creation, update, scheduled].filter(Boolean)) await json(request, admin, 'PATCH', `/workflow-rules/${rule.id}/`, { enabled: false });
  }
});

test('organization hierarchy, depth limits, cabinet movement and all custom field data types', async ({ request }) => {
  const admin = await login(request);
  const token = await login(request, userUsername, userPassword);
  const doc = await document(request, token);
  let parent: any = null;
  for (let level = 0; level < 5; level++) parent = await json(request, token, 'POST', '/tags/', { name: uniqueName(`level-${level}`), parent: parent?.id, color: '#aabbcc' }, 201);
  await json(request, token, 'POST', '/tags/', { name: uniqueName('too-deep'), parent: parent.id }, 400);
  const cabinet = await json(request, token, 'POST', '/cabinets/', { name: uniqueName('cabinet') }, 201);
  const child = await json(request, token, 'POST', '/cabinets/', { name: uniqueName('cabinet-child') }, 201);
  expect((await json(request, token, 'POST', `/cabinets/${child.id}/move/`, { parent: cabinet.id })).parent).toBe(cabinet.id);
  const sibling = await json(request, token, 'POST', '/cabinets/', { name: `z-${uniqueName('cabinet-sibling')}`, parent: cabinet.id }, 201);
  expect((await json(request, token, 'POST', `/cabinets/${sibling.id}/move/`, { target: child.id, position: 'left' })).parent).toBe(cabinet.id);
  const reordered = (await json(request, token, 'GET', '/cabinets/tree/')).find((item: any) => item.id === cabinet.id);
  expect(reordered.children.map((item: any) => item.id)).toEqual([sibling.id, child.id]);
  await json(request, token, 'POST', `/cabinets/${cabinet.id}/move/`, { target: child.id, position: 'last-child' }, 400);
  const correspondent = await json(request, token, 'POST', '/correspondents/', { name: uniqueName('correspondent') }, 201);
  const storage = await json(request, token, 'POST', '/storage-paths/', { name: uniqueName('autocomplete-path'), path: 'documents/{{ title }}' }, 201);
  expect((await json(request, token, 'GET', `/storage-paths/autocomplete/?q=${encodeURIComponent(storage.name)}`))[0].id).toBe(storage.id);
  await json(request, token, 'POST', '/bulk-assign/', { document_ids: [doc.id], tag_ids: [parent.id], cabinet_id: child.id, correspondent_id: correspondent.id });
  expect(await json(request, token, 'GET', `/documents/${doc.id}/`)).toMatchObject({ cabinet: child.id, correspondent: correspondent.id });
  const type = await json(request, admin, 'POST', '/document-types/', { name: uniqueName('document-type') }, 201);
  const values: Record<string, any> = { string: 'Text', longtext: 'Longer text', url: 'https://example.com/document', date: '2026-01-02', datetime: '2026-01-02T03:04:05Z', boolean: false, integer: 0, float: 1.25, monetary: '12.3400', documentlink: [doc.id], select: ['first'], multiselect: ['first', 'second'] };
  for (const [data_type, value] of Object.entries(values)) {
    const field = await json(request, token, 'POST', '/custom-fields/', { name: uniqueName(data_type), data_type, extra_data: { options: ['first', 'second'] } }, 201);
    await json(request, admin, 'POST', `/document-types/${type.id}/custom-fields/`, { document_type: type.id, custom_field: field.id, required: true }, 201);
    const instance = await json(request, token, 'POST', `/documents/${doc.id}/custom-fields/`, { document: doc.id, field: field.id, value }, 201);
    const read = await json(request, token, 'GET', `/documents/${doc.id}/custom-fields/${instance.id}/`);
    if (data_type === 'datetime') expect(new Date(read.value).toISOString()).toBe('2026-01-02T03:04:05.000Z');
    else if (data_type === 'monetary') expect(Number(read.value)).toBe(12.34);
    else expect(read.value).toEqual(value);
  }
});

test('supersession relationship updates obsolete state and graph, then reverses on deletion', async ({ request }) => {
  const admin = await login(request);
  const token = await login(request, userUsername, userPassword);
  const old = await document(request, token);
  const replacement = await document(request, token);
  const types = await json(request, token, 'GET', '/relationship-types/');
  const supersedes = types.find((item: any) => item.slug === 'supersedes') ?? await json(request, admin, 'POST', '/relationship-types/', { slug: 'supersedes', label: 'Supersedes', is_directional: true }, 201);
  const relationship = await json(request, token, 'POST', `/documents/${replacement.id}/relationships/`, { target_document: old.id, relationship_type: supersedes.id }, 201);
  expect((await json(request, token, 'GET', `/documents/${old.id}/`)).is_obsolete).toBe(true);
  const graph = await json(request, token, 'GET', `/documents/${replacement.id}/relationship-graph/`);
  expect(graph.nodes.map((item: any) => item.id)).toEqual(expect.arrayContaining([old.id, replacement.id]));
  expect(graph.edges).toHaveLength(1);
  await json(request, token, 'DELETE', `/documents/${replacement.id}/relationships/${relationship.id}/`, undefined, 204);
  expect((await json(request, token, 'GET', `/documents/${old.id}/`)).is_obsolete).toBe(false);
});

test('legal hold preserves a document, notifies its custodian, records acknowledgment and releases', async ({ request }) => {
  const admin = await login(request);
  const token = await login(request, userUsername, userPassword);
  const user = await json(request, token, 'GET', '/auth/profile/');
  const doc = await document(request, token);
  const hold = await json(request, admin, 'POST', '/legal-holds/', { name: uniqueName('acceptance-hold'), criteria: [{ criteria_type: 'specific_documents', value: { document_ids: [doc.id] } }], custodian_ids: [user.id] }, 201);
  expect((await json(request, admin, 'POST', `/legal-holds/${hold.id}/activate/`, {})).documents_captured).toBe(1);
  expect((await json(request, token, 'GET', `/documents/${doc.id}/`)).is_held).toBe(true);
  await json(request, admin, 'DELETE', `/legal-holds/${hold.id}/`, undefined, 400);
  await json(request, token, 'PATCH', `/documents/${doc.id}/`, { title: 'Forbidden mutation' }, 409);
  await json(request, token, 'DELETE', `/documents/${doc.id}/`, undefined, 409);
  const field = await json(request, token, 'POST', '/custom-fields/', { name: uniqueName('held-field'), data_type: 'string' }, 201);
  await json(request, token, 'POST', `/documents/${doc.id}/custom-fields/`, { document: doc.id, field: field.id, value: 'Forbidden' }, 409);
  await json(request, token, 'POST', '/bulk-set-custom-fields/', { document_ids: [doc.id], field_id: field.id, value: 'Forbidden' }, 409);
  await json(request, token, 'POST', '/bulk-assign/', { document_ids: [doc.id], cabinet_id: null }, 409);
  await expect.poll(async () => (await json(request, admin, 'GET', `/legal-holds/${hold.id}/custodians/`))[0]?.notified_at, { timeout: 30_000 }).toBeTruthy();
  expect((await json(request, token, 'POST', `/legal-holds/${hold.id}/acknowledge/`, {})).status).toBe('acknowledged');
  const snapshot = await json(request, admin, 'GET', `/legal-holds/${hold.id}/export/`);
  expect(snapshot.documents[0].document).toBe(doc.id);
  expect(snapshot.custodians[0].acknowledged).toBe(true);
  await json(request, admin, 'POST', `/legal-holds/${hold.id}/release/`, { reason: 'Matter resolved.' });
  expect((await json(request, token, 'PATCH', `/documents/${doc.id}/`, { title: 'Released document' })).is_held).toBe(false);
});

test('physical location hierarchy, overdue loan, barcode return cycle and destruction certificate PDF', async ({ request }) => {
  const token = await login(request, userUsername, userPassword);
  const doc = await document(request, token);
  let parent: any = null;
  for (const location_type of ['building', 'room', 'cabinet', 'shelf', 'box']) parent = await json(request, token, 'POST', '/physical-locations/', { name: uniqueName(location_type), location_type, parent: parent?.id }, 201);
  const record = await json(request, token, 'POST', '/physical-records/', { document: doc.id, location: parent.id, barcode: uniqueName('barcode'), condition: 'good' }, 201);
  await json(request, token, 'POST', `/documents/${doc.id}/charge-out/`, { expected_return: new Date(Date.now() - 86_400_000).toISOString() }, 201);
  await expect.poll(async () => (await json(request, token, 'GET', '/charge-outs/overdue/')).find((item: any) => item.physical_record === record.id)?.status, { timeout: 30_000 }).toBe('overdue');
  await json(request, token, 'POST', `/physical-records/${record.id}/barcode-checkout/`, { barcode: record.barcode, expected_return: new Date(Date.now() + 86_400_000).toISOString() }, 400);
  await json(request, token, 'POST', `/documents/${doc.id}/charge-in/`, {});
  await json(request, token, 'POST', `/physical-records/${record.id}/barcode-checkout/`, { barcode: record.barcode, expected_return: new Date(Date.now() + 86_400_000).toISOString() }, 201);
  await json(request, token, 'POST', `/documents/${doc.id}/charge-in/`, {});
  const certificate = await json(request, token, 'POST', `/physical-records/${record.id}/destruction-certificate/`, { method: 'shredding', witness: 'Acceptance Witness' }, 201);
  expect(certificate.certificate_pdf).toBeTruthy();
  const pdf = await request.get(`${api}/physical-records/${record.id}/destruction-certificates/${certificate.id}/download/`, { headers: authHeaders(token) });
  expect(pdf.status(), await pdf.text()).toBe(200);
  expect((await pdf.body()).subarray(0, 5).toString()).toBe('%PDF-');
});

test('public portal upload, document request, real ingestion approval and request deadlines', async ({ request }) => {
  const admin = await login(request);
  const portal = await json(request, admin, 'POST', '/portals/', { name: uniqueName('portal'), slug: uniqueName('portal'), welcome_text: 'Upload acceptance documents', require_email: true, require_name: true, allowed_mime_types: ['text/plain'] }, 201);
  expect((await (await request.get(`${api}/portal/${portal.slug}/`)).json()).welcome_text).toBe('Upload acceptance documents');
  const content = Buffer.from(uniqueName('portal-ingestion-original'));
  const file = { name: `${uniqueName('portal')}.txt`, mimeType: 'text/plain', buffer: content };
  expect((await request.post(`${api}/portal/${portal.slug}/upload/`, { multipart: { file } })).status()).toBe(400);
  const upload = await request.post(`${api}/portal/${portal.slug}/upload/`, { multipart: { file, email: 'contributor@example.test', name: 'Contributor' } });
  expect(upload.status(), await upload.text()).toBe(201);
  const submission = await upload.json();
  await json(request, admin, 'PATCH', `/portal-submissions/${submission.id}/review/`, { status: 'approved', review_notes: 'Approved over real HTTP' });
  let accepted: any;
  await expect.poll(async () => {
    accepted = (await json(request, admin, 'GET', `/portal-submissions/?portal=${portal.id}`)).find((item: any) => item.id === submission.id);
    return accepted?.ingested_document;
  }, { timeout: 90_000, message: 'Portal approval links the independently ingested document' }).toBeTruthy();
  const download = await request.get(`${api}/documents/${accepted.ingested_document}/download/`, { headers: authHeaders(admin) });
  expect(download.status()).toBe(200);
  expect(await download.body()).toEqual(content);
  const requested = await json(request, admin, 'POST', '/document-requests/', { portal: portal.id, title: uniqueName('request'), assignee_email: 'contributor@example.test', assignee_name: 'Contributor', deadline: new Date(Date.now() + 86_400_000).toISOString() }, 201);
  await json(request, admin, 'POST', `/document-requests/${requested.id}/send/`, {});
  await json(request, admin, 'POST', `/document-requests/${requested.id}/remind/`, {});
  expect((await request.get(`${api}/request/${requested.token}/`)).status()).toBe(200);
  const requestUpload = await request.post(`${api}/request/${requested.token}/upload/`, { multipart: { file: { ...file, buffer: Buffer.from(uniqueName('requested-upload')) } } });
  expect(requestUpload.status(), await requestUpload.text()).toBe(201);
  expect((await json(request, admin, 'GET', `/document-requests/${requested.id}/`)).status).toBe('partially_fulfilled');
  const expired = await json(request, admin, 'POST', '/document-requests/', { portal: portal.id, title: uniqueName('expired-request'), assignee_email: 'contributor@example.test', deadline: new Date(Date.now() - 86_400_000).toISOString() }, 201);
  expect((await request.post(`${api}/request/${expired.token}/upload/`, { multipart: { file } })).status()).toBe(400);
});

test('notifications stay user-scoped, preferences persist, read flags update and quotas block new uploads', async ({ request }) => {
  const admin = await login(request);
  const token = await login(request, userUsername, userPassword);
  const user = await json(request, token, 'GET', '/auth/profile/');
  const doc = await document(request, token);
  const result = await json(request, token, 'GET', '/notifications/?page_size=100');
  const notification = (result.results ?? result).find((item: any) => item.document === doc.id);
  expect(notification).toBeTruthy();
  await json(request, admin, 'GET', `/notifications/${notification.id}/`, undefined, 404);
  expect((await json(request, token, 'POST', `/notifications/${notification.id}/read/`, {})).read).toBe(true);
  await json(request, token, 'POST', '/notifications/read_all/', {});
  expect((await json(request, token, 'GET', '/notifications/unread_count/')).count).toBe(0);
  const existing = await json(request, token, 'GET', '/notification-preferences/');
  const preference = (existing.results ?? existing).find((item: any) => item.event_type === 'document_added' && item.channel === 'email');
  const saved = preference ? await json(request, token, 'PATCH', `/notification-preferences/${preference.id}/`, { enabled: false }) : await json(request, token, 'POST', '/notification-preferences/', { event_type: 'document_added', channel: 'email', enabled: false }, 201);
  expect(saved.enabled).toBe(false);
  const usage = await json(request, token, 'GET', '/quotas/usage/');
  const quota = await json(request, admin, 'POST', '/quotas/', { user: user.id, max_documents: usage.document_count }, 201);
  try {
    const blocked = await request.post(`${api}/documents/upload/`, { headers: authHeaders(token), multipart: { document: { name: 'quota-blocked.txt', mimeType: 'text/plain', buffer: Buffer.from('quota') } } });
    expect(blocked.status(), await blocked.text()).toBe(429);
    expect((await json(request, token, 'GET', '/quotas/usage/')).documents_remaining).toBe(0);
  } finally {
    await json(request, admin, 'DELETE', `/quotas/${quota.id}/`, undefined, 204);
  }
});

for (const signing_order of ['sequential', 'parallel']) {
  test(`${signing_order} public signatures enforce order and required fields, generate PDF certificate and audit`, async ({ request }) => {
    const token = await login(request);
    const { doc } = await uploadPdf(request, token, uniqueName('signed-document'), 2);
    const fieldTypes = ['signature', 'initials', 'date', 'checkbox', 'text'];
    const signature = await json(request, token, 'POST', `/documents/${doc.id}/signature-request/`, {
      title: uniqueName(`${signing_order}-signature`), signing_order,
      signers: [{ name: 'First Signer', email: 'first@example.test', order: 0 }, { name: 'Second Signer', email: 'second@example.test', order: 1 }],
      fields: fieldTypes.map((field_type, index) => ({ signer_index: index < 4 ? 0 : 1, page: 0, x: 0.1, y: 0.1 + index * 0.1, width: 0.2, height: 0.05, field_type, required: true })),
    }, 201);
    await json(request, token, 'POST', `/signature-requests/${signature.id}/send/`, {});
    const [first, second] = signature.signers;
    const fields = (signer: any) => signature.fields_data.filter((item: any) => item.signer === signer.id).map((field: any) => ({ field_id: field.id, value: field.field_type === 'date' ? '2026-01-02' : field.field_type === 'checkbox' ? 'true' : 'Acceptance Signature' }));
    if (signing_order === 'sequential') {
      expect((await request.post(`${api}/sign/${second.token}/complete/`, { data: { fields: fields(second) } })).status()).toBe(400);
      expect((await request.get(`${api}/sign/${second.token}/preview/?page=1`)).status()).toBe(403);
    }
    for (const signer of [first, second]) {
      expect((await request.get(`${api}/sign/${signer.token}/`)).status()).toBe(200);
      const preview = await request.get(`${api}/sign/${signer.token}/preview/?page=1`);
      expect(preview.status(), await preview.text()).toBe(200);
      expect(preview.headers()['content-type']).toContain('image/png');
      expect((await preview.body()).subarray(0, 8)).toEqual(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]));
      expect((await request.post(`${api}/sign/${signer.token}/view_page/`, { data: { page: 0 } })).status()).toBe(200);
      expect((await request.post(`${api}/sign/${signer.token}/complete/`, { data: { fields: [{ field_id: fields(signer)[0].field_id, value: '' }] } })).status()).toBe(400);
      const complete = await request.post(`${api}/sign/${signer.token}/complete/`, { data: { fields: fields(signer) } });
      expect(complete.status(), await complete.text()).toBe(200);
    }
    await expect.poll(async () => (await json(request, token, 'GET', `/signature-requests/${signature.id}/`)).certificate_pdf, { timeout: 30_000 }).toBeTruthy();
    const certificate = await request.get(`${api}/signature-requests/${signature.id}/certificate/`, { headers: authHeaders(token) });
    expect(certificate.status(), await certificate.text()).toBe(200);
    expect((await certificate.body()).subarray(0, 5).toString()).toBe('%PDF-');
    const audit = await json(request, token, 'GET', `/signature-requests/${signature.id}/audit/`);
    expect(audit.filter((event: any) => event.event_type === 'signed')).toHaveLength(2);
    expect(audit.some((event: any) => event.event_type === 'completed')).toBe(true);
    expect((await request.get(`${api}/sign/${first.token}/`)).status()).toBe(410);
  });
}

test('public signing expiry and cancellation close tokens, and SMS-protected review requires verification', async ({ request }) => {
  const token = await login(request);
  const { doc } = await uploadPdf(request, token, uniqueName('signature-lifecycle'));
  const create = (extra: Record<string, unknown> = {}) => json(request, token, 'POST', `/documents/${doc.id}/signature-request/`, {
    title: uniqueName('signature-lifecycle'),
    signers: [{ name: 'Verified signer', email: 'verify@example.test', order: 0, verification_method: 'sms' }],
    fields: [{ signer_index: 0, page: 0, x: 0.1, y: 0.1, width: 0.2, height: 0.1, field_type: 'signature', required: true }],
    ...extra,
  }, 201);
  const protectedRequest = await create();
  await json(request, token, 'POST', `/signature-requests/${protectedRequest.id}/send/`, {});
  const signer = protectedRequest.signers[0];
  expect((await request.get(`${api}/sign/${signer.token}/preview/?page=1`)).status()).toBe(403);
  expect((await request.post(`${api}/sign/${signer.token}/complete/`, { data: { fields: [{ field_id: protectedRequest.fields_data[0].id, value: 'Attempted unverified signature' }] } })).status()).toBe(400);
  expect((await request.post(`${api}/esignatures/verify/`, { data: { token: signer.token, code: 'wrong' } })).status()).toBe(400);
  await json(request, token, 'POST', `/signature-requests/${protectedRequest.id}/cancel/`, {});
  expect((await request.get(`${api}/sign/${signer.token}/`)).status()).toBe(410);
  expect((await request.get(`${api}/sign/${signer.token}/preview/?page=1`)).status()).toBe(410);

  const expiring = await create({ expiration: new Date(Date.now() + 1500).toISOString() });
  await expect.poll(async () => (await json(request, token, 'GET', `/signature-requests/${expiring.id}/`)).status, { timeout: 30_000 }).toBe('expired');
  expect((await request.get(`${api}/sign/${expiring.signers[0].token}/`)).status()).toBe(410);
});

test('scheduled retention purges only eligible unheld documents in the explicitly enabled isolated profile', async ({ request }) => {
  const admin = await login(request);
  const user = await login(request, userUsername, userPassword);
  const type = await json(request, admin, 'POST', '/document-types/', { name: uniqueName('retention-policy') }, 201);
  const preserved = await json(request, user, 'POST', '/documents/', { title: uniqueName('preserved-by-hold'), document_type: type.id }, 201);
  const temporary = await json(request, user, 'POST', '/documents/', { title: uniqueName('eligible-for-retention'), document_type: type.id }, 201);
  const hold = await json(request, admin, 'POST', '/legal-holds/', { name: uniqueName('retention-hold'), criteria: [{ criteria_type: 'specific_documents', value: { document_ids: [preserved.id] } }] }, 201);
  await json(request, admin, 'POST', `/legal-holds/${hold.id}/activate/`, {});
  try {
    await json(request, admin, 'PATCH', `/document-types/${type.id}/`, { trash_time_period: 0, trash_time_unit: 'days', delete_time_period: 0, delete_time_unit: 'days' });
    await expect.poll(async () => (await request.get(`${api}/documents/${temporary.id}/`, { headers: authHeaders(user) })).status(), { timeout: 30_000 }).toBe(404);
    await expect.poll(async () => {
      const trash = await json(request, user, 'GET', '/documents/deleted/?page_size=100');
      return (trash.results ?? trash).some((item: any) => item.id === temporary.id);
    }, { timeout: 30_000 }).toBe(false);
    expect((await json(request, user, 'GET', `/documents/${preserved.id}/`)).is_held).toBe(true);
  } finally {
    await json(request, admin, 'PATCH', `/document-types/${type.id}/`, { trash_time_period: null, delete_time_period: null });
    await json(request, admin, 'POST', `/legal-holds/${hold.id}/release/`, { reason: 'Isolated retention test finished.' });
  }
});

test('signing freezes active v2 bytes across sequential signers and certifies the same hash after v1 reactivation', async ({ request }) => {
  const token = await login(request);
  const { doc, bytes: original } = await uploadPdf(request, token, uniqueName('snapshot-v1'));
  const second = makePdf(uniqueName('snapshot-v2-contract'), 2);
  const upload = await request.post(`${api}/documents/${doc.id}/files/`, {
    headers: authHeaders(token), multipart: { document: { name: 'version-two.pdf', mimeType: 'application/pdf', buffer: second } },
  });
  expect(upload.status(), await upload.text()).toBe(201);
  expect((await upload.json()).version_number).toBe(2);
  const signature = await json(request, token, 'POST', `/documents/${doc.id}/signature-request/`, {
    title: uniqueName('frozen-version-request'), signing_order: 'sequential',
    signers: [{ name: 'First version reviewer', email: 'snapshot-first@example.test', order: 0 }, { name: 'Second version reviewer', email: 'snapshot-second@example.test', order: 1 }],
    fields: [0, 1].map((signer_index) => ({ signer_index, page: 2, x: 0.1, y: 0.2, width: 0.3, height: 0.1, field_type: 'signature', required: true })),
  }, 201);
  await json(request, token, 'POST', `/signature-requests/${signature.id}/send/`, {});
  const frozen = await json(request, token, 'GET', `/signature-requests/${signature.id}/`);
  expect(frozen.document_snapshot.source_version_number).toBe(2);
  expect(frozen.document_snapshot.source_checksum).toBe(sha256(second));
  expect(frozen.document_snapshot.review_page_count).toBe(2);
  const [first, next] = signature.signers;
  const firstSource = await request.get(`${api}/sign/${first.token}/document/`);
  expect(firstSource.status()).toBe(200);
  expect(sha256(await firstSource.body())).toBe(sha256(second));
  const firstPreview = await request.get(`${api}/sign/${first.token}/preview/?page=2`);
  expect(firstPreview.status()).toBe(200);
  const previewHash = sha256(await firstPreview.body());
  const values = (signer: any) => signature.fields_data.filter((field: any) => field.signer === signer.id).map((field: any) => ({ field_id: field.id, value: signer.name }));
  const firstComplete = await request.post(`${api}/sign/${first.token}/complete/`, { data: { fields: values(first) } });
  expect(firstComplete.status(), await firstComplete.text()).toBe(200);

  const versions = await json(request, token, 'GET', `/documents/${doc.id}/versions/`);
  const firstVersion = versions.find((version: any) => version.version_number === 1);
  await json(request, token, 'POST', `/documents/${doc.id}/versions/${firstVersion.id}/activate/`, {});
  await json(request, token, 'PATCH', `/documents/${doc.id}/`, { title: uniqueName('changed-after-first-signature') });
  const liveSource = await request.get(`${api}/documents/${doc.id}/download/`, { headers: authHeaders(token) });
  expect(sha256(await liveSource.body())).toBe(sha256(original));
  const nextSource = await request.get(`${api}/sign/${next.token}/document/`);
  expect(nextSource.status()).toBe(200);
  expect(sha256(await nextSource.body())).toBe(sha256(second));
  const nextPreview = await request.get(`${api}/sign/${next.token}/preview/?page=2`);
  expect(nextPreview.status()).toBe(200);
  expect(sha256(await nextPreview.body())).toBe(previewHash);
  const other = await document(request, token);
  await json(request, token, 'PATCH', `/signature-requests/${signature.id}/`, { document: other.id }, 400);
  const nextComplete = await request.post(`${api}/sign/${next.token}/complete/`, { data: { fields: values(next) } });
  expect(nextComplete.status(), await nextComplete.text()).toBe(200);
  await expect.poll(async () => (await json(request, token, 'GET', `/signature-requests/${signature.id}/`)).certificate_pdf, { timeout: 30_000 }).toBeTruthy();
  const certificate = await request.get(`${api}/signature-requests/${signature.id}/certificate/`, { headers: authHeaders(token) });
  expect(certificate.status()).toBe(200);
  const text = execFileSync('docker', [
    'compose', '-f', '../deploy/compose.e2e.yml', 'exec', '-T', 'web', 'python', '-c',
    "import sys,pymupdf; pdf=pymupdf.open(stream=sys.stdin.buffer.read(),filetype='pdf'); print('\\n'.join(page.get_text() for page in pdf))",
  ], { input: await certificate.body(), encoding: 'utf8', timeout: 30_000 });
  const compact = text.replace(/\s/g, '');
  expect(compact).toContain(sha256(second));
  expect(compact).not.toContain(sha256(original));
  expect(text).toContain(doc.title);
});
