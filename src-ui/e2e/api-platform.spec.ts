import { APIRequestContext, APIResponse, expect, test } from '@playwright/test';
import { createHash, createHmac } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { authHeaders, login, uniqueName, userPassword, userUsername } from './support/api';
import { makePdf } from './support/documents';

const api = '/api/v1';
const modelRequestTimeout = 90_000;
const fixtures = resolve(process.cwd(), '../documents/tests/fixtures');

function stackPython(script: string, payload: Record<string, unknown> = {}): string {
  const guarded = 'import os\nassert os.environ.get("DOCVAULT_E2E") == "1", "Isolated test stack required"\n' + script;
  return execFileSync('docker', [
    'compose', '-f', resolve(process.cwd(), '../deploy/compose.e2e.yml'), 'exec', '-T', 'web',
    'python', '-c', guarded, JSON.stringify(payload),
  ], { timeout: 90_000, encoding: 'utf8', stdio: 'pipe' }).trim();
}

function logSourceFailure(sourceId: number, owner: number, folder: string, filename: string): void {
  try {
    const snapshot = stackPython(String.raw`
import django; django.setup()
import json, re, stat, sys
from pathlib import Path
from django.db.models import Q
from documents.models import Document
from processing.models import ProcessingTask
from sources.models import Source, WatchFolderSource

p = json.loads(sys.argv[1])
source = Source.objects.get(pk=p["source_id"], owner_id=p["owner_id"])
assert source.source_type in {"watch_folder", "staging"}
folder = Path(p["folder"]).resolve()
assert folder.parent == Path("/data/consume").resolve()
assert re.fullmatch(r"(?:watch_folder|staging)-[0-9]{13}-[0-9a-f]{6}", folder.name)
assert p["filename"] == folder.name + ".txt"
watch = WatchFolderSource.objects.filter(source_id=source.pk).first()
configured_path = watch.path if watch else source.configuration.get("path")
assert configured_path and Path(configured_path).resolve() == folder

file_state = {"exists": False, "size": None, "regular_file": False}
try:
    info = (folder / p["filename"]).lstat()
    file_state.update(exists=True, size=info.st_size, regular_file=stat.S_ISREG(info.st_mode))
except FileNotFoundError:
    pass

documents = list(Document.all_objects.filter(original_filename=p["filename"]).values(
    "id", "original_filename", "owner_id", "document_type_id", "created_at", "deleted_at", "is_held",
)[:10])
document_ids = [item["id"] for item in documents]
marker = Path(p["filename"]).stem
tasks = ProcessingTask.objects.filter(
    Q(document_id__in=document_ids) | Q(owner_id=p["owner_id"], result__contains=marker),
).order_by("created_at")
task_rows = list(tasks.values(
    "task_id", "owner_id", "document_id", "status", "result", "created_at", "started_at", "completed_at",
)[:10])
for row in task_rows:
    row["result"] = re.sub(r"://[^/@\s]+:[^/@\s]+@", "://[redacted]@", row["result"][:1500])
print(json.dumps({
    "source": {"id": source.pk, "owner_id": source.owner_id, "source_type": source.source_type,
               "enabled": source.enabled, "created_at": source.created_at, "updated_at": source.updated_at,
               "last_polled": None, "polling_interval": watch.polling_interval if watch else None},
    "filename": p["filename"], "file": file_state, "documents_including_trash": documents,
    "matching_processing_tasks": task_rows,
    "source_logs": {"available": False, "reason": "SourceLog is not implemented"},
    "unavailable": ["Source.last_polled is not implemented",
                    "Pending tasks have no persisted source or filename relation and cannot be attributed exactly"],
}, default=str))
`, { source_id: sourceId, owner_id: owner, folder, filename });
    console.error(`SOURCE_INGESTION_DIAGNOSTICS ${snapshot}`);
  } catch {
    console.error('SOURCE_INGESTION_DIAGNOSTICS {"diagnostic_error":"Scoped snapshot could not be collected"}');
  }
}

async function body(response: APIResponse, status = 200): Promise<any> {
  expect(response.status(), `${response.url()}: ${await response.text()}`).toBe(status);
  return status === 204 ? null : response.json();
}

async function call(request: APIRequestContext, token: string, method: string, path: string, data?: unknown, status = 200, timeout?: number) {
  return body(await request.fetch(`${api}${path}`, { method, headers: authHeaders(token), data, timeout }), status);
}

async function createDocument(request: APIRequestContext, token: string, fields: Record<string, unknown> = {}) {
  return call(request, token, 'POST', '/documents/', {
    title: uniqueName('platform-document'), content: 'Acceptance document content.', ...fields,
  }, 201);
}

async function uploadedDocument(request: APIRequestContext, token: string, filename: string, buffer: Buffer, mimeType: string, fields: Record<string, string> = {}) {
  const response = await request.post(`${api}/documents/upload/`, {
    headers: authHeaders(token), multipart: { document: { name: filename, mimeType, buffer }, ...fields },
  });
  const queued = await body(response, 202);
  let task: any;
  await expect.poll(async () => {
    const listing = await call(request, token, 'GET', '/tasks/?page_size=100');
    task = (listing.results ?? listing).find((item: any) => item.task_id === queued.task_id);
    if (task?.status === 'failure') throw new Error(`Real ingestion failed: ${task.result}`);
    return task?.status;
  }, { timeout: 150_000, message: `Independent worker must complete task ${queued.task_id}` }).toBe('success');
  expect(task.document, task.result).toBeTruthy();
  return call(request, token, 'GET', `/documents/${task.document}/`);
}

function totp(secret: string): string {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '';
  for (const char of secret.replace(/=+$/, '').toUpperCase()) bits += alphabet.indexOf(char).toString(2).padStart(5, '0');
  const key = Buffer.from(bits.match(/.{8}/g)!.map((byte) => parseInt(byte, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30_000)));
  const digest = createHmac('sha1', key).update(counter).digest();
  const offset = digest[digest.length - 1] & 15;
  return ((digest.readUInt32BE(offset) & 0x7fffffff) % 1_000_000).toString().padStart(6, '0');
}

test('scanned PDF traverses real queue, OCR, PDF/A, barcode, NER, zone extraction and storage template', async ({ request }) => {
  test.setTimeout(220_000);
  const admin = await login(request);
  const user = await login(request, userUsername, userPassword);
  const path = await call(request, admin, 'POST', '/storage-paths/', {
    name: uniqueName('archive-path'), path: 'acceptance/{{ title }}',
  }, 201);
  const template = await body(await request.post(`${api}/zone-ocr-templates/`, {
    headers: authHeaders(admin), multipart: {
      name: `000-${uniqueName('invoice-zone')}`, page_number: '1', is_active: 'true',
      sample_page_image: { name: 'invoice-reference.png', mimeType: 'image/png', buffer: readFileSync(join(fixtures, 'e2e-invoice-scan.png')) },
    },
  }), 201);
  try {
    const previous = await call(request, admin, 'GET', '/documents/?archive_serial_number=73491001');
    for (const fixture of previous.results ?? previous) {
      if (fixture.title.startsWith('ocr-evidence')) {
        await call(request, admin, 'PATCH', `/documents/${fixture.id}/`, { archive_serial_number: null });
      }
    }
    await call(request, admin, 'POST', `/zone-ocr-templates/${template.id}/fields/`, {
      template: template.id, name: 'Invoice total', field_type: 'monetary',
      bounding_box: { x: 4, y: 17, width: 90, height: 5 }, preprocessing: 'numeric_only',
    }, 201);
    const scan = Buffer.concat([readFileSync(join(fixtures, 'e2e-invoice-scan.pdf')), Buffer.from(`\n% ${uniqueName('scan')}\n`)]);
    const document = await uploadedDocument(request, user, uniqueName('scanned-invoice') + '.pdf', scan, 'application/pdf', {
      title: uniqueName('ocr-evidence'), storage_path: String(path.id),
    });
    expect(document.content).toContain('1234.56');
    expect(document.content).toMatch(/Barack Obama/);
    expect(document.page_count).toBe(1);
    expect(document.archive_serial_number).toBe(73491001);
    expect(document.filename).toMatch(/^acceptance\//);
    expect(document.archive_filename).toBeTruthy();
    const original = await request.get(`${api}/documents/${document.id}/download/`, { headers: authHeaders(user) });
    expect(original.ok()).toBeTruthy();
    expect(await original.body()).toEqual(scan);
    const archive = await request.get(`${api}/documents/${document.id}/download/?version=archive`, { headers: authHeaders(user) });
    expect(archive.ok()).toBeTruthy();
    const archivedBytes = await archive.body();
    expect(archivedBytes.subarray(0, 5).toString()).toBe('%PDF-');
    expect(archivedBytes.toString('latin1')).toMatch(/pdfaid:part|pdfaid:conformance/);
    const preview = await request.get(`${api}/documents/${document.id}/preview/`, { headers: authHeaders(user) });
    expect(preview.status()).toBe(200);
    expect(preview.headers()['cache-control']).toContain('no-store');
    expect(preview.headers()['content-type']).toBe('image/webp');
    const label = await request.get(`${api}/documents/${document.id}/barcode-label/`, { headers: authHeaders(user) });
    expect(label.status()).toBe(200);
    expect((await label.body()).subarray(0, 8)).toEqual(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]));
    const entities = await call(request, user, 'GET', `/documents/${document.id}/entities/`);
    expect((entities.results ?? entities).some((entity: any) => /Barack Obama/i.test(entity.value))).toBeTruthy();
    const neighbors = await call(request, user, 'GET', '/entities/PERSON/Barack%20Obama/cooccurrence/');
    expect(neighbors.some((neighbor: any) => neighbor.entity.value === 'London' && neighbor.count >= 1)).toBe(true);
    const exactTitle = encodeURIComponent(JSON.stringify([{ field: 'title', operator: 'equals', value: document.title }]));
    await expect.poll(async () => {
      const search = await call(request, user, 'GET', `/search/?filter_rules=${exactTitle}`);
      return search.facets.entities?.some((facet: any) => facet.key === 'Barack Obama' && facet.count === 1) ?? false;
    }, { timeout: 60_000 }).toBe(true);
    const zones = await call(request, user, 'GET', `/zone-ocr-results/?document_id=${document.id}&template_id=${template.id}`);
    const result = (zones.results ?? zones)[0];
    expect(result.extracted_value).toContain('1234.56');
    expect(result.confidence).toBeGreaterThan(0.7);
    await call(request, user, 'PATCH', `/zone-ocr-results/${result.id}/`, { corrected_value: '1234.56', reviewed: true });
    const mismatched = stackPython([
      'import base64', 'from io import BytesIO', 'from PIL import Image',
      'image=Image.new("RGB",(1200,1600),"black"); out=BytesIO(); image.save(out,format="PNG")',
      'print(base64.b64encode(out.getvalue()).decode())',
    ].join('\n'));
    await body(await request.patch(`${api}/zone-ocr-templates/${template.id}/`, {
      headers: authHeaders(admin), multipart: {
        sample_page_image: { name: 'different-layout.png', mimeType: 'image/png', buffer: Buffer.from(mismatched, 'base64') },
      },
    }));
    const secondScan = Buffer.concat([readFileSync(join(fixtures, 'e2e-invoice-scan.pdf')), Buffer.from(`\n% ${uniqueName('layout-mismatch')}\n`)]);
    const secondDocument = await uploadedDocument(request, user, uniqueName('layout-mismatch') + '.pdf', secondScan, 'application/pdf');
    const mismatchedZones = await call(request, user, 'GET', `/zone-ocr-results/?document_id=${secondDocument.id}&template_id=${template.id}`);
    const mismatchedResult = (mismatchedZones.results ?? mismatchedZones)[0];
    expect(mismatchedResult.extracted_value).toContain('1234.56');
    expect(mismatchedResult.confidence, 'A visibly different reference layout must reduce OCR confidence').toBeLessThan(result.confidence / 2);
    const versions = await call(request, user, 'GET', `/documents/${document.id}/versions/`);
    expect(versions).toHaveLength(1);
    expect(versions[0].is_active).toBe(true);
    const usage = await call(request, user, 'GET', '/quotas/usage/');
    expect(usage.storage_bytes).toBeGreaterThanOrEqual(scan.length);
    const forbidden = await request.get(`${api}/documents/${document.id}/`, { headers: authHeaders(await login(request)) });
    expect(forbidden.status()).toBe(200);
    const zip = await request.post(`${api}/documents/bulk-export/`, { headers: authHeaders(user), data: { ids: [document.id] } });
    expect(zip.status()).toBe(200);
    expect((await zip.body()).subarray(0, 2).toString()).toBe('PK');
  } finally {
    await call(request, admin, 'DELETE', `/zone-ocr-templates/${template.id}/`, undefined, 204);
  }
});

test('new file versions change downloaded bytes and activation restores old bytes with actual text diff', async ({ request }) => {
  const user = await login(request, userUsername, userPassword);
  const originalText = `Original alpha content ${uniqueName('version')}`;
  const document = await uploadedDocument(request, user, uniqueName('original') + '.txt', Buffer.from(originalText), 'text/plain');
  const replacementText = `Replacement beta content ${uniqueName('version')}`;
  const uploaded = await request.post(`${api}/documents/${document.id}/files/`, {
    headers: authHeaders(user), multipart: {
      document: { name: 'replacement.txt', mimeType: 'text/plain', buffer: Buffer.from(replacementText) }, comment: 'New file',
    },
  });
  const second = await body(uploaded, 201);
  expect(second.version_number).toBe(2);
  const versions = await call(request, user, 'GET', `/documents/${document.id}/versions/`);
  const first = versions.find((version: any) => version.version_number === 1);
  const latest = await request.get(`${api}/documents/${document.id}/download/`, { headers: authHeaders(user) });
  expect((await latest.body()).toString()).toBe(replacementText);
  const diff = await call(request, user, 'GET', `/documents/${document.id}/versions/compare/?v1=${first.id}&v2=${second.id}`);
  expect(diff.diff_html).toMatch(/Original|alpha/);
  expect(diff.diff_html).toMatch(/Replacement|beta/);
  await call(request, user, 'POST', `/documents/${document.id}/versions/${first.id}/activate/`);
  const restored = await request.get(`${api}/documents/${document.id}/download/`, { headers: authHeaders(user) });
  expect((await restored.body()).toString()).toBe(originalText);
});

test('active version metadata follows page count and MIME changes without offering a stale archive', async ({ request }) => {
  test.setTimeout(180_000);
  const token = await login(request, userUsername, userPassword);
  const document = await uploadedDocument(request, token, uniqueName('one-page') + '.pdf', makePdf(uniqueName('Original page')), 'application/pdf');
  const versions = await call(request, token, 'GET', `/documents/${document.id}/versions/`);
  const first = versions[0];
  const threePages = makePdf(uniqueName('Replacement pages'), 3);
  await body(await request.post(`${api}/documents/${document.id}/files/`, {
    headers: authHeaders(token), multipart: { document: { name: 'three-pages.pdf', mimeType: 'application/pdf', buffer: threePages } },
  }), 201);
  let metadata = await call(request, token, 'GET', `/documents/${document.id}/`);
  expect(metadata).toMatchObject({ page_count: 3, mime_type: 'application/pdf', original_filename: 'three-pages.pdf', archive_filename: '' });
  expect((await request.get(`${api}/documents/${document.id}/preview/?page=3`, { headers: authHeaders(token) })).status()).toBe(200);
  const png = readFileSync(join(fixtures, 'e2e-invoice-scan.png'));
  await body(await request.post(`${api}/documents/${document.id}/files/`, {
    headers: authHeaders(token), multipart: { document: { name: 'active-image.png', mimeType: 'image/png', buffer: png } },
  }), 201);
  metadata = await call(request, token, 'GET', `/documents/${document.id}/`);
  expect(metadata).toMatchObject({ page_count: 1, mime_type: 'image/png', original_filename: 'active-image.png', archive_filename: '' });
  const thumbnail = await request.get(`${api}/documents/${document.id}/preview/`, { headers: authHeaders(token) });
  expect(thumbnail.status()).toBe(200);
  expect(thumbnail.headers()['content-type']).toBe('image/webp');
  const download = await request.get(`${api}/documents/${document.id}/download/`, { headers: authHeaders(token) });
  expect(await download.body()).toEqual(png);
  await call(request, token, 'POST', `/documents/${document.id}/versions/${first.id}/activate/`);
  metadata = await call(request, token, 'GET', `/documents/${document.id}/`);
  expect(metadata.mime_type).toBe('application/pdf');
  expect(metadata.page_count).toBe(1);
  expect(metadata.archive_filename).toBeTruthy();
});

test('a real separator QR page produces two independently downloadable, correctly hashed documents', async ({ request }) => {
  test.setTimeout(240_000);
  const token = await login(request, userUsername, userPassword);
  const marker = uniqueName('separator');
  const encoded = stackPython([
    'import base64,json,sys,pymupdf', 'p=json.loads(sys.argv[1])',
    'pdf=pymupdf.open(stream=base64.b64decode(p["pdf"]),filetype="pdf")',
    'for page in pdf: page.insert_text((50,50),p["marker"],fontsize=10)',
    'print(base64.b64encode(pdf.tobytes()).decode())',
  ].join('\n'), { marker, pdf: readFileSync(join(fixtures, 'e2e-separators.pdf')).toString('base64') });
  await uploadedDocument(request, token, `${marker}.pdf`, Buffer.from(encoded, 'base64'), 'application/pdf');
  let documents: any[] = [];
  await expect.poll(async () => {
    const listing = await call(request, token, 'GET', `/documents/?search=${marker}`);
    documents = listing.results;
    return documents.length;
  }, { timeout: 150_000 }).toBe(2);
  for (const document of documents) {
    const metadata = await call(request, token, 'GET', `/documents/${document.id}/`);
    expect(metadata.page_count).toBe(1);
    const response = await request.get(`${api}/documents/${document.id}/download/`, { headers: authHeaders(token) });
    expect(response.status(), await response.text()).toBe(200);
    expect(createHash('sha256').update(await response.body()).digest('hex')).toBe(metadata.checksum);
  }
});

test('TOTP setup gates login and consumes each recovery code only once', async ({ request }) => {
  const username = uniqueName('otp-user');
  const registered = await body(await request.post(`${api}/auth/register/`, { data: { username, password: userPassword } }), 201);
  const setup = await call(request, registered.token, 'POST', '/auth/otp/setup/');
  expect(setup.qr_code_base64).toBeTruthy();
  const confirmed = await call(request, registered.token, 'POST', '/auth/otp/confirm/', { code: totp(setup.secret) });
  expect(confirmed.backup_codes.length).toBeGreaterThan(0);
  const challenge = await body(await request.post(`${api}/auth/login/`, { data: { username, password: userPassword } }), 202);
  expect(challenge.otp_required).toBe(true);
  expect(challenge.token).toBeUndefined();
  const verified = await body(await request.post(`${api}/auth/login/`, { data: { username, password: userPassword, otp_code: totp(setup.secret) } }));
  expect(verified.token).toBeTruthy();
  const recovery = confirmed.backup_codes[0];
  expect((await body(await request.post(`${api}/auth/login/`, { data: { username, password: userPassword, otp_code: recovery } }))).token).toBeTruthy();
  expect((await request.post(`${api}/auth/login/`, { data: { username, password: userPassword, otp_code: recovery } })).status()).toBe(400);
});

test('ordinary metadata clients cannot forge a reference to another owner\'s stored file', async ({ request }) => {
  const admin = await login(request);
  const user = await login(request, userUsername, userPassword);
  const marker = uniqueName('private-storage-reference');
  const privateDocument = await uploadedDocument(request, admin, `${marker}.txt`, Buffer.from(marker), 'text/plain');
  const forged = {
    filename: privateDocument.filename, archive_filename: privateDocument.filename,
    thumbnail_path: privateDocument.filename, checksum: privateDocument.checksum,
    mime_type: privateDocument.mime_type, original_filename: privateDocument.original_filename, page_count: 1,
  };
  const metadata = await createDocument(request, user, { ...forged, title: uniqueName('metadata-only') });
  expect(metadata.filename).toBeFalsy();
  expect(metadata.archive_filename).toBeFalsy();
  expect(metadata.thumbnail_path).toBeFalsy();
  expect(metadata.checksum).toBeFalsy();
  await call(request, user, 'PATCH', `/documents/${metadata.id}/`, forged);
  for (const path of [`/documents/${metadata.id}/download/`, `/documents/${metadata.id}/download/?version=archive`, `/documents/${privateDocument.id}/download/`]) {
    expect((await request.get(`${api}${path}`, { headers: authHeaders(user) })).status(), path).toBe(404);
  }
});

test('RBAC group grants and revokes document visibility; ordinary user cannot reach admin endpoints', async ({ request }) => {
  const admin = await login(request);
  const user = await login(request, userUsername, userPassword);
  const privateDoc = await createDocument(request, admin);
  expect((await request.get(`${api}/documents/${privateDoc.id}/`, { headers: authHeaders(user) })).status()).toBe(404);
  for (const path of ['/users/', '/roles/', '/storage/config/', '/audit-log/']) {
    expect((await request.get(`${api}${path}`, { headers: authHeaders(user) })).status(), path).toBe(403);
  }
  const profile = await call(request, user, 'GET', '/auth/profile/');
  const group = await call(request, admin, 'POST', '/groups/', { name: uniqueName('role-group') }, 201);
  const permissions = await call(request, admin, 'GET', '/permissions/');
  const view = permissions.find((permission: any) => permission.namespace === 'documents' && permission.codename === 'view_document');
  const role = await call(request, admin, 'POST', '/roles/', { name: uniqueName('reader-role'), permission_ids: [view.id], group_ids: [group.id] }, 201);
  await call(request, admin, 'PATCH', `/users/${profile.id}/`, { groups: [group.id] });
  try {
    expect((await request.get(`${api}/documents/${privateDoc.id}/`, { headers: authHeaders(user) })).status()).toBe(200);
    expect((await request.patch(`${api}/documents/${privateDoc.id}/`, { headers: authHeaders(user), data: { title: 'Forbidden' } })).status()).toBe(403);
    await call(request, admin, 'PATCH', `/roles/${role.id}/`, { permission_ids: [] });
    expect((await request.get(`${api}/documents/${privateDoc.id}/`, { headers: authHeaders(user) })).status()).toBe(404);
  } finally {
    await call(request, admin, 'PATCH', `/users/${profile.id}/`, { groups: [] });
    await call(request, admin, 'DELETE', `/roles/${role.id}/`, undefined, 204);
    await call(request, admin, 'DELETE', `/groups/${group.id}/`, undefined, 204);
  }
});

test('real Elasticsearch returns text hits, facets, synonyms, curations and search analytics', async ({ request }) => {
  test.setTimeout(150_000);
  const admin = await login(request);
  const user = await login(request, userUsername, userPassword);
  const key = uniqueName('solaracceptance').replaceAll('-', '');
  const tag = await call(request, admin, 'POST', '/tags/', { name: uniqueName('energy'), color: '#008800' }, 201);
  const document = await createDocument(request, user, { title: key, content: `${key} photovoltaic batteries solar electricity` });
  await call(request, user, 'POST', '/bulk/', { action: 'add_tags', document_ids: [document.id], tag_ids: [tag.id] });
  let results: any;
  await expect.poll(async () => {
    results = await call(request, user, 'GET', `/search/?query=${key}`);
    return results.results.map((result: any) => result.id);
  }, { timeout: 80_000 }).toContain(document.id);
  expect(results.facets.tags.some((facet: any) => facet.key === tag.name)).toBeTruthy();
  const synonymWord = uniqueName('solarsynonym').replaceAll('-', '');
  const synonym = await call(request, admin, 'POST', '/search/synonyms/', { terms: [synonymWord, key], enabled: true }, 201);
  const synonymResults = await call(request, user, 'GET', `/search/?query=${synonymWord}`);
  expect(synonymResults.results.map((result: any) => result.id)).toContain(document.id);
  const curatedWord = uniqueName('curated').replaceAll('-', '');
  const curation = await call(request, admin, 'POST', '/search/curations/', { query_text: curatedWord, pinned_documents: [document.id], enabled: true }, 201);
  const curated = await call(request, user, 'GET', `/search/?query=${curatedWord}`);
  expect(curated.results[0].id).toBe(document.id);
  await call(request, user, 'POST', '/search/click/', { query_text: key, document_id: document.id, click_position: 1 });
  const analytics = await call(request, admin, 'GET', '/search/analytics/');
  expect(analytics.total_queries).toBeGreaterThan(0);
  expect(analytics.total_clicks).toBeGreaterThan(0);
  expect(analytics.top_queries.some((entry: any) => entry.query_text === key)).toBeTruthy();
  await call(request, admin, 'DELETE', `/search/synonyms/${synonym.id}/`, undefined, 204);
  await call(request, admin, 'DELETE', `/search/curations/${curation.id}/`, undefined, 204);
});

test('storage usage quota rejects an upload before it exceeds the allowance and audit exports contain real actions', async ({ request }) => {
  test.setTimeout(180_000);
  const admin = await login(request);
  const username = uniqueName('quota-user');
  const created = await call(request, admin, 'POST', '/users/', { username, password: userPassword }, 201);
  const user = await login(request, username, userPassword);
  const quota = await call(request, admin, 'POST', '/quotas/', { user: created.id, max_storage_bytes: 8 }, 201);
  try {
    const result = await request.post(`${api}/documents/upload/`, { headers: authHeaders(user), multipart: {
      document: { name: 'too-large.txt', mimeType: 'text/plain', buffer: Buffer.from('larger than eight bytes') },
    } });
    expect(result.status(), await result.text()).toBe(429);
    const original = Buffer.from(uniqueName('managed-quota-bytes'));
    await call(request, admin, 'PATCH', `/quotas/${quota.id}/`, { max_documents: 1, max_storage_bytes: original.length + 4 });
    const document = await uploadedDocument(request, user, uniqueName('quota-original') + '.txt', original, 'text/plain');
    await body(await request.post(`${api}/documents/${document.id}/files/`, {
      headers: authHeaders(user), multipart: { document: { name: 'second.txt', mimeType: 'text/plain', buffer: Buffer.from('new!') } },
    }), 201);
    const blockedVersion = await request.post(`${api}/documents/${document.id}/files/`, {
      headers: authHeaders(user), multipart: { document: { name: 'third.txt', mimeType: 'text/plain', buffer: Buffer.from('x') } },
    });
    expect(blockedVersion.status(), await blockedVersion.text()).toBe(429);
    expect((await request.post(`${api}/documents/`, { headers: authHeaders(user), data: { title: 'Over document quota' } })).status()).toBe(429);
    const logs = await call(request, admin, 'GET', `/audit-log/?user=${created.id}`);
    expect((logs.results ?? logs).some((entry: any) => entry.action === 'login')).toBeTruthy();
    const csv = await request.get(`${api}/audit-log/export/?export_format=csv`, { headers: authHeaders(admin) });
    expect(csv.status()).toBe(200);
    expect(csv.headers()['content-type']).toContain('text/csv');
    expect(await csv.text()).toContain(username);
  } finally {
    await call(request, admin, 'DELETE', `/quotas/${quota.id}/`, undefined, 204);
  }
});

test('two concurrent real uploads cannot both persist past a one-document owner quota', async ({ request }) => {
  test.setTimeout(240_000);
  const admin = await login(request);
  const username = uniqueName('concurrent-quota-user');
  const owner = await call(request, admin, 'POST', '/users/', { username, password: userPassword }, 201);
  const user = await login(request, username, userPassword);
  const quota = await call(request, admin, 'POST', '/quotas/', { user: owner.id, max_documents: 1 }, 201);
  try {
    const responses = await Promise.all(['alpha', 'beta'].map((part) => request.post(`${api}/documents/upload/`, {
      headers: authHeaders(user), multipart: { document: {
        name: `${uniqueName(part)}.pdf`, mimeType: 'application/pdf',
        buffer: Buffer.concat([readFileSync(join(fixtures, 'e2e-invoice-scan.pdf')), Buffer.from(`\n% ${uniqueName(part)}\n`)]),
      } },
    })));
    const queued = await Promise.all(responses.map((response) => body(response, 202)));
    let tasks: any[] = [];
    await expect.poll(async () => {
      const listing = await call(request, user, 'GET', '/tasks/?page_size=100');
      tasks = (listing.results ?? listing).filter((task: any) => queued.some((entry) => entry.task_id === task.task_id));
      return tasks.filter((task) => ['success', 'failure'].includes(task.status)).length;
    }, { timeout: 180_000 }).toBe(2);
    expect(tasks.filter((task) => task.status === 'success')).toHaveLength(1);
    const rejected = tasks.find((task) => task.status === 'failure');
    expect(rejected.result).toContain('Document limit reached');
    const usage = await call(request, user, 'GET', '/quotas/usage/');
    expect(usage.document_count).toBe(1);
  } finally {
    await call(request, admin, 'DELETE', `/quotas/${quota.id}/`, undefined, 204);
  }
});

test('AI disabled state is explicit, or real Ollama chat and FAISS indexing work across web and worker processes', async ({ request }) => {
  test.setTimeout(240_000);
  const admin = await login(request);
  const user = await login(request, userUsername, userPassword);
  const status = await call(request, user, 'GET', '/ai/status/');
  if (process.env['E2E_INTEGRATIONS'] === '1') {
    expect(status.llm_enabled, 'Integration acceptance requires the enabled real provider').toBe(true);
  }
  const fixtureContent = 'Barack Obama approved the mission in London. The mission code is ORBIT73491. Solar batteries cost 1234 dollars.';
  const document = await createDocument(request, user, { content: fixtureContent });
  if (!status.llm_enabled) {
    const summary = await call(request, user, 'GET', `/ai/documents/${document.id}/summarize/`, undefined, 400);
    expect(summary.error).toContain('not enabled');
    const semantic = await call(request, user, 'GET', '/ai/search/semantic/?query=solar');
    expect(semantic.results).toEqual([]);
    return;
  }
  expect(process.env['E2E_INTEGRATIONS'], 'Enabled AI requires the real provider integration profile').toBe('1');
  await call(request, admin, 'POST', '/ai/rebuild-index/', {}, 202);
  await expect.poll(async () => {
    const semantic = await call(request, user, 'GET', '/ai/search/semantic/?query=solar%20batteries', undefined, 200, modelRequestTimeout);
    return semantic.results.map((item: any) => item.id);
  }, { timeout: 150_000, message: 'The worker must publish the new document into the web process FAISS snapshot' }).toContain(document.id);
  const chat = await call(request, user, 'POST', `/ai/documents/${document.id}/chat/`, { question: 'What is the mission code?', history: [] }, 200, modelRequestTimeout);
  expect(chat.answer, 'Real document Q&A must recover the known fixture fact').toContain('ORBIT73491');
  expect(chat.sources[0].document_id).toBe(document.id);
  const summary = await call(request, user, 'GET', `/ai/documents/${document.id}/summarize/`, undefined, 200, modelRequestTimeout);
  expect(summary.summary, 'Summary must preserve the actual mission identifier').toContain('ORBIT73491');
  expect(summary.summary, 'Summary must preserve the actual battery cost').toMatch(/\b(?:1234|1,234)\b/);
  const title = await call(request, user, 'GET', `/ai/documents/${document.id}/suggest-title/`, undefined, 200, modelRequestTimeout);
  expect(title.suggested_title, 'Title must describe the fixture document').toMatch(/mission|solar|batter|ORBIT|Barack Obama/i);
  expect(title.suggested_title.length).toBeLessThanOrEqual(100);
  expect(fixtureContent.toLowerCase().replace(/\s+/g, ' '), 'Title must copy a source phrase without inferred facts')
    .toContain(title.suggested_title.toLowerCase().replace(/\s+/g, ' '));
  const extracted = await call(request, user, 'GET', `/ai/documents/${document.id}/entities/`, undefined, 200, modelRequestTimeout);
  expect(extracted.entities.names, 'Entity endpoint must return structured, source-grounded names').toEqual(expect.arrayContaining(['Barack Obama']));
  expect(extracted.entities.dates, 'No dates are present in the fixture; inferred dates must be rejected').toEqual([]);
  expect(extracted.entities.amounts.some((amount: string) => amount.includes('1234'))).toBe(true);
  const hybrid = await call(request, user, 'GET', '/ai/search/hybrid/?query=solar', undefined, 200, modelRequestTimeout);
  expect(hybrid.results.length).toBeGreaterThan(0);
});

test('parallel worker ingests both remain discoverable in the shared FAISS index', async ({ request }) => {
  test.skip(process.env['E2E_INTEGRATIONS'] !== '1', 'Requires the real Ollama embedding model');
  test.setTimeout(240_000);
  const token = await login(request, userUsername, userPassword);
  const marker = uniqueName('parallelvectors');
  const documents = await Promise.all(['alpha', 'beta'].map((part) => uploadedDocument(
    request, token, `${marker}-${part}.txt`, Buffer.from(`${marker} ${part} solar battery acceptance vectors.`), 'text/plain',
  )));
  await expect.poll(async () => {
    const result = await call(request, token, 'GET', `/ai/search/semantic/?query=${encodeURIComponent(marker)}&k=50`, undefined, 200, modelRequestTimeout);
    return documents.every((document) => result.results.some((item: any) => item.id === document.id));
  }, { timeout: 150_000, message: 'Two independent workers must not overwrite each other’s published vectors' }).toBe(true);
});

test('real classifier trains on labelled documents and applies persisted metadata to a fresh ingestion', async ({ request }) => {
  test.setTimeout(240_000);
  const token = await login(request);
  stackPython([
    'import django; django.setup()', 'from documents.models import DocumentType',
    'from organization.models import Tag,Correspondent',
    'pattern=r"^classifier-[0-9]{13}-[0-9a-f]{6}-(invoice|contract)$"',
    'for model in (DocumentType,Tag,Correspondent):',
    ' model.objects.filter(name__regex=pattern,matching_algorithm=6).update(matching_algorithm=0)',
  ].join('\n'));
  const marker = uniqueName('classifier');
  const labels: any[] = [];
  for (const name of ['invoice', 'contract']) {
    labels.push({
      name,
      type: await call(request, token, 'POST', '/document-types/', { name: `${marker}-${name}`, matching_algorithm: 6 }, 201),
      tag: await call(request, token, 'POST', '/tags/', { name: `${marker}-${name}`, color: '#006688', matching_algorithm: 6 }, 201),
      correspondent: await call(request, token, 'POST', '/correspondents/', { name: `${marker}-${name}`, matching_algorithm: 6 }, 201),
    });
  }
  for (const label of labels) {
    for (let index = 0; index < 12; index++) {
      const content = label.name === 'invoice'
        ? `${marker} invoice billing payment receivable amount supplier shipping total receipt tax finance item${index}`
        : `${marker} contract legal agreement obligation clause jurisdiction warranty signature parties litigation section${index}`;
      const document = await createDocument(request, token, {
        title: `${marker}-${label.name}-${index}`, content, document_type: label.type.id, correspondent: label.correspondent.id,
      });
      await call(request, token, 'POST', '/bulk/', { action: 'add_tags', document_ids: [document.id], tag_ids: [label.tag.id] });
    }
  }
  const previousModel = await call(request, token, 'GET', '/classifier/status/');
  await call(request, token, 'POST', '/classifier/train/', {}, 202);
  await expect.poll(async () => {
    const status = await call(request, token, 'GET', '/classifier/status/');
    return status.tags_trained && status.document_type_trained && status.correspondent_trained
      && status.document_type_data_hash !== previousModel.document_type_data_hash;
  }, { timeout: 150_000, message: 'A real worker must train and publish the sklearn model' }).toBe(true);
  const content = `${marker} invoice billing payment receivable amount supplier shipping total receipt tax finance ${uniqueName('fresh')}`;
  const document = await uploadedDocument(request, token, `${uniqueName('classified')}.txt`, Buffer.from(content), 'text/plain');
  const invoice = labels.find((label) => label.name === 'invoice');
  expect(document.document_type).toBe(invoice.type.id);
  expect(document.correspondent).toBe(invoice.correspondent.id);
  const suggestions = await call(request, token, 'GET', `/documents/${document.id}/suggestions/`);
  expect(suggestions.document_type.length).toBeGreaterThan(0);
  for (const item of [...suggestions.tags, ...suggestions.document_type]) {
    expect(item.confidence).toBeGreaterThanOrEqual(0);
    expect(item.confidence).toBeLessThanOrEqual(1);
  }
});

test('watch and staging folders ingest real files through Beat and the separate worker', async ({ request }) => {
  test.setTimeout(240_000);
  const token = await login(request);
  const owner = (await call(request, token, 'GET', '/auth/profile/')).id;
  for (const sourceType of ['watch_folder', 'staging']) {
    const marker = uniqueName(sourceType);
    const folder = `/data/consume/${marker}`;
    const filename = `${marker}.txt`;
    const content = `Real ${sourceType} ingestion ${marker}`;
    stackPython('import json,sys\nfrom pathlib import Path\np=json.loads(sys.argv[1]); folder=Path(p["folder"]); folder.mkdir(); (folder/p["filename"]).write_text(p["content"])', { folder, filename, content });
    const source = await call(request, token, 'POST', '/sources/', {
      label: marker, enabled: false, source_type: sourceType, owner,
      ...(sourceType === 'staging' ? { configuration: { path: folder } } : {}),
    }, 201);
    try {
      if (sourceType === 'watch_folder') {
        await call(request, token, 'POST', `/sources/${source.id}/watch-folder/`, { path: folder, consumed_action: 'delete' }, 201);
      }
      await call(request, token, 'PATCH', `/sources/${source.id}/`, { enabled: true });
      let documentId: number | undefined;
      try {
        await expect.poll(async () => {
          const documents = await call(request, token, 'GET', `/documents/?search=${filename}`);
          documentId = documents.results.find((document: any) => document.original_filename === filename)?.id;
          return documentId;
        }, { timeout: 100_000 }).toBeTruthy();
      } catch (error) {
        logSourceFailure(source.id, owner, folder, filename);
        throw error;
      }
      const download = await request.get(`${api}/documents/${documentId}/download/`, { headers: authHeaders(token) });
      expect(download.status()).toBe(200);
      expect((await download.body()).toString()).toBe(content);
    } finally {
      await call(request, token, 'PATCH', `/sources/${source.id}/`, { enabled: false });
    }
  }
});

test('MinIO source ingestion uses only the configured object-store endpoint and never exposes credentials', async ({ request }) => {
  test.skip(process.env['E2E_INTEGRATIONS'] !== '1', 'Requires the real isolated S3-compatible service');
  test.setTimeout(150_000);
  const token = await login(request);
  const owner = (await call(request, token, 'GET', '/auth/profile/')).id;
  const marker = uniqueName('s3-ingestion');
  const filename = `${marker}.txt`;
  const content = `Real object storage source acceptance ${marker}`;
  const objectStore = JSON.parse(stackPython([
    'import json,sys,boto3', 'from django.conf import settings', 'p=json.loads(sys.argv[1])',
    'from io import BytesIO', 'from urllib.request import urlopen', 'from storage.backends.s3 import S3StorageBackend',
    's=boto3.client("s3",endpoint_url=settings.S3_ENDPOINT_URL,aws_access_key_id=settings.S3_ACCESS_KEY,aws_secret_access_key=settings.S3_SECRET_KEY)',
    'buckets=s.list_buckets()["Buckets"]',
    's.create_bucket(Bucket=settings.S3_BUCKET_NAME) if not any(b["Name"]==settings.S3_BUCKET_NAME for b in buckets) else None',
    's.put_object(Bucket=settings.S3_BUCKET_NAME,Key="inbox/"+p["filename"],Body=p["content"].encode())',
    'backend=S3StorageBackend(config={"S3_PROVIDER":"minio","S3_PREFIX":"acceptance-backend/"+p["filename"]})',
    'key=backend.save("artifact.txt",BytesIO(p["content"].encode()))',
    'try:',
    ' with backend.open(key) as source: matches=source.read()==p["content"].encode()',
    ' with urlopen(backend.presigned_url(key,expires_in=60),timeout=10) as source: signed=source.read()==p["content"].encode()',
    ' size=backend.size(key); listed=key in backend.list_files(); exists=backend.exists(key)',
    'finally: backend.delete(key)',
    'print(json.dumps({"matches":matches,"presigned":signed,"size":size,"listed":listed,"exists":exists,"removed":not backend.exists(key)}))',
  ].join('\n'), { filename, content }));
  expect(objectStore).toMatchObject({ matches: true, presigned: true, size: Buffer.byteLength(content), listed: true, exists: true, removed: true });
  const source = await call(request, token, 'POST', '/sources/', {
    label: marker, source_type: 's3', owner, enabled: true, configuration: {
      bucket: 'docvault-e2e', prefix: `inbox/${marker}`, use_storage_endpoint: true,
      aws_access_key_id: 'docvault-e2e', aws_secret_access_key: 'e2e-only-minio-password', region_name: 'us-east-1',
    },
  }, 201);
  expect(source).not.toHaveProperty('configuration');
  try {
    let documentId: number | undefined;
    await expect.poll(async () => {
      const listing = await call(request, token, 'GET', `/documents/?search=${filename}`);
      documentId = listing.results.find((document: any) => document.original_filename === filename)?.id;
      return documentId;
    }, { timeout: 100_000 }).toBeTruthy();
    const download = await request.get(`${api}/documents/${documentId}/download/`, { headers: authHeaders(token) });
    expect(download.status()).toBe(200);
    expect((await download.body()).toString()).toBe(content);
    const unsafe = await request.patch(`${api}/sources/${source.id}/`, {
      headers: authHeaders(token), data: { configuration: { endpoint_url: 'http://169.254.169.254/' } },
    });
    expect(unsafe.status()).toBe(400);
  } finally {
    await call(request, token, 'PATCH', `/sources/${source.id}/`, { enabled: false });
  }
});

test('real encrypted storage authenticates bytes and CAS deduplicates, detects corruption and migrates in batches', async ({ request }) => {
  const token = await login(request);
  const owner = (await call(request, token, 'GET', '/auth/profile/')).id;
  const marker = uniqueName('storage-proof');
  const result = JSON.parse(stackPython([
    'import django; django.setup()', 'import hashlib,json,sys,tempfile', 'from io import BytesIO,StringIO',
    'from pathlib import Path', 'from django.test import override_settings', 'from django.core.management import call_command',
    'from storage.backends.local import LocalStorageBackend', 'from storage.backends.encrypted import EncryptedStorageBackend,MAGIC',
    'from storage.backends.content_addressed import ContentAddressedStorageBackend', 'from storage.models import ContentBlob',
    'from storage.utils import get_storage_backend', 'from documents.models import Document,DocumentFile',
    'from documents.downloads import open_document_file',
    'p=json.loads(sys.argv[1]); payload=p["marker"].encode()',
    'with tempfile.TemporaryDirectory(dir="/data/consume") as folder:',
    ' raw=LocalStorageBackend(folder)',
    ' with override_settings(STORAGE_ENCRYPTION_KEY="acceptance-only-storage-key"):',
    '  encrypted=EncryptedStorageBackend(raw); encrypted.save("originals/probe",BytesIO(payload))',
    '  with raw.open("originals/probe") as f: at_rest=f.read()',
    '  with encrypted.open("originals/probe") as f: decrypted=f.read()',
    '  cas=ContentAddressedStorageBackend(encrypted); digest=cas.save("a",BytesIO(payload)); cas.save("b",BytesIO(payload))',
    '  blob=ContentBlob.objects.get(pk=digest); refs=blob.reference_count',
    '  valid=not any(x["expected"]==digest for x in cas.verify_integrity())',
    '  raw.save(blob.storage_path,BytesIO(b"deliberately corrupted acceptance bytes"))',
    '  detected=any(x["expected"]==digest for x in cas.verify_integrity())',
    '  cas.delete(digest); cas.delete(digest)',
    ' backend=get_storage_backend(); ids=[]',
    ' for index in range(2):',
    '  name=backend.save("originals/"+p["marker"]+str(index)+".txt",BytesIO(payload))',
    '  d=Document.objects.create(title=p["marker"]+str(index),filename=name,mime_type="text/plain",checksum=hashlib.sha256(payload).hexdigest(),owner_id=p["owner"])',
    '  DocumentFile.objects.create(document=d,file=name,filename=name,mime_type="text/plain",checksum=d.checksum,size=len(payload)); ids.append(d.pk)',
    ' output=StringIO(); call_command("migrate_to_cas",document_ids=ids,batch_size=1,stdout=output)',
    ' linked=DocumentFile.objects.filter(document_id__in=ids,blob__isnull=False).count(); readback=0',
    ' for artifact in DocumentFile.objects.filter(document_id__in=ids):',
    '  with open_document_file(artifact) as migrated: readback+=int(migrated.read()==payload)',
    ' repeat=StringIO(); call_command("migrate_to_cas",document_ids=ids,batch_size=1,stdout=repeat)',
    ' print(json.dumps({"encrypted":at_rest.startswith(MAGIC) and payload not in at_rest,"roundtrip":decrypted==payload,"references":refs,"valid":valid,"corruption_detected":detected,"migration":output.getvalue(),"linked":linked,"readback":readback,"repeat":repeat.getvalue(),"documents":ids}))',
  ].join('\n'), { marker, owner }));
  expect(result).toMatchObject({ encrypted: true, roundtrip: true, references: 2, valid: true, corruption_detected: true });
  expect(result.migration).toContain('0 errors');
  expect(result.linked).toBe(2);
  expect(result.readback).toBe(2);
  expect(result.repeat).toContain('Nothing to do');
  for (const documentId of result.documents) {
    const download = await request.get(`${api}/documents/${documentId}/download/`, { headers: authHeaders(token) });
    expect(download.status()).toBe(200);
    expect((await download.body()).toString()).toBe(marker);
  }
  const queued = await call(request, token, 'POST', '/storage/verify-integrity/', {}, 202);
  expect(queued.status).toBe('integrity_check_queued');
  const dedup = await call(request, token, 'GET', '/storage/dedup-stats/');
  expect(dedup.total_blobs).toBeGreaterThanOrEqual(0);
  const completed = JSON.parse(stackPython([
    'import django; django.setup()', 'import json', 'from storage.tasks import verify_storage_integrity',
    'print(json.dumps(verify_storage_integrity.delay().get(timeout=45)))',
  ].join('\n')));
  expect(completed).toMatchObject({ status: 'completed', issues_found: 0 });
});

test('four real processes save, read and release the same CAS object without losing references', async () => {
  test.setTimeout(120_000);
  const result = JSON.parse(stackPython([
    'import django; django.setup()', 'import concurrent.futures,hashlib,json,multiprocessing,sys,tempfile',
    'from io import BytesIO', 'from django.db import connection,connections',
    'from storage.backends.content_addressed import ContentAddressedStorageBackend',
    'from storage.backends.local import LocalStorageBackend', 'from storage.models import ContentBlob',
    'assert connection.vendor=="postgresql", "Real PostgreSQL locking required"',
    'payload=json.loads(sys.argv[1])["marker"].encode(); ctx=multiprocessing.get_context("fork"); barrier=ctx.Barrier(4)',
    'def run(folder):',
    ' connections.close_all(); cas=ContentAddressedStorageBackend(LocalStorageBackend(folder)); digest=cas.save("same",BytesIO(payload))',
    ' barrier.wait(timeout=30)',
    ' with cas.open(digest) as source: matches=source.read()==payload',
    ' references=ContentBlob.objects.get(pk=digest).reference_count',
    ' barrier.wait(timeout=30); cas.delete(digest); connections.close_all()',
    ' return {"matches":matches,"references":references}',
    'with tempfile.TemporaryDirectory(dir="/data/consume") as folder:',
    ' connections.close_all()',
    ' with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=ctx) as pool:',
    '  results=list(pool.map(run,[folder]*4))',
    ' digest=hashlib.sha256(payload).hexdigest(); remaining=ContentBlob.objects.filter(pk=digest).exists()',
    ' physical=LocalStorageBackend(folder).exists(ContentAddressedStorageBackend._hash_to_path(digest))',
    ' print(json.dumps({"workers":results,"remaining":remaining,"physical":physical}))',
  ].join('\n'), { marker: uniqueName('parallel-cas') }));
  expect(result.workers).toHaveLength(4);
  expect(result.workers.every((worker: any) => worker.matches && worker.references === 4)).toBe(true);
  expect(result.remaining).toBe(false);
  expect(result.physical).toBe(false);
});
