import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { authHeaders, login, uniqueName, userUsername, userPassword } from './support/api';
import { makePdf, sha256, uploadPdf } from './support/documents';

function appPython(script: string, payload: object): string {
  return execFileSync('docker', [
    'compose', '-f', resolve(process.cwd(), '../deploy/compose.e2e.yml'), 'exec', '-T', 'web',
    'python', '-c', 'import django; django.setup()\n' + script, JSON.stringify(payload),
  ], { timeout: 30_000, encoding: 'utf8' }).trim();
}

test('document count quotas protect metadata creation, not only the upload endpoint', async ({ request }) => {
  const admin = authHeaders(await login(request));
  const user = authHeaders(await login(request, userUsername, userPassword));
  const profile = await (await request.get('/api/v1/auth/profile/', { headers: user })).json();
  const usage = await (await request.get('/api/v1/quotas/usage/', { headers: user })).json();
  const configured = await request.post('/api/v1/quotas/', {
    headers: admin, data: { user: profile.id, max_documents: usage.document_count },
  });
  expect(configured.status(), await configured.text()).toBe(201);
  const quota = await configured.json();
  try {
    const metadata = await request.post('/api/v1/documents/', {
      headers: user, data: { title: uniqueName('quota-metadata-probe'), content: 'Synthetic quota boundary.' },
    });
    expect(metadata.status(), await metadata.text()).toBe(429);
  } finally {
    await request.delete('/api/v1/quotas/' + quota.id + '/', { headers: admin });
  }
});

test('Redis-backed stem results are shared by independent application processes', async () => {
  const word = uniqueName('acceptance-running');
  const produced = JSON.parse(appPython([
    'import json,sys', 'from django.core.cache import cache', 'from ml.preprocessing import StemmerCache',
    'word=json.loads(sys.argv[1])["word"]; value=StemmerCache().stem(word)',
    'print(json.dumps({"value":value,"stored":cache.get("stem:"+word),"backend":type(cache._cache).__module__}))',
  ].join('\n'), { word }));
  expect(produced.value).toBeTruthy();
  expect(produced.stored).toBe(produced.value);
  expect(produced.backend).toContain('redis');
  const consumed = JSON.parse(appPython([
    'import json,sys', 'from django.core.cache import cache',
    'key="stem:"+json.loads(sys.argv[1])["word"]; value=cache.get(key); cache.delete(key)',
    'print(json.dumps({"value":value}))',
  ].join('\n'), { word }));
  expect(consumed.value).toBe(produced.value);
});

test('IMAP attachment import crosses a real SMTP server, mailbox, Beat, worker and document storage', async ({ request }) => {
  test.skip(process.env['E2E_INTEGRATIONS'] !== '1', 'Requires the isolated GreenMail integration service');
  test.setTimeout(180_000);
  const token = await login(request);
  const headers = authHeaders(token);
  const profile = await request.get('/api/v1/auth/profile/', { headers });
  expect(profile.ok()).toBeTruthy();
  const owner = (await profile.json()).id;
  const subject = uniqueName('IMAP acceptance');
  const filename = `${uniqueName('imap-attachment')}.pdf`;
  const bytes = makePdf(subject);
  const send = [
    'import base64,json,smtplib,sys',
    'from email.message import EmailMessage',
    'p=json.loads(sys.argv[1]); m=EmailMessage()',
    'm["From"]="sender@example.test"; m["To"]="e2e@acceptance.test"; m["Subject"]=p["subject"]',
    'm.set_content("Synthetic document ingestion acceptance message.")',
    'm.add_attachment(base64.b64decode(p["data"]),maintype="application",subtype="pdf",filename=p["filename"])',
    's=smtplib.SMTP("greenmail",3025,timeout=15); s.send_message(m); s.quit()',
  ].join('\n');
  execFileSync('docker', [
    'compose', '-f', resolve(process.cwd(), '../deploy/compose.e2e.yml'), 'exec', '-T', 'web',
    'python', '-c', send, JSON.stringify({ subject, filename, data: bytes.toString('base64') }),
  ], { timeout: 30_000, stdio: 'pipe' });
  const created = await request.post('/api/v1/mail-accounts/', {
    headers, data: {
      name: subject, enabled: false, imap_server: 'greenmail', port: 3143,
      security: 'none', account_type: 'imap', username: 'e2e', password: 'e2e-password',
    },
  });
  expect(created.status(), await created.text()).toBe(201);
  const account = await created.json();
  expect(account).not.toHaveProperty('password');
  try {
    const connection = await request.post(`/api/v1/mail-accounts/${account.id}/test-connection/`, { headers });
    expect((await connection.json()).success).toBe(true);
    const rule = await request.post(`/api/v1/mail-accounts/${account.id}/rules/`, {
      headers, data: {
        name: subject, folder: 'INBOX', filter_subject: subject, action: 'download_attachment',
        processed_action: 'mark_read', owner,
      },
    });
    expect(rule.status(), await rule.text()).toBe(201);
    expect((await request.patch(`/api/v1/mail-accounts/${account.id}/`, { headers, data: { enabled: true } })).ok()).toBeTruthy();
    let documentId: number | undefined;
    await expect.poll(async () => {
      const response = await request.get(`/api/v1/documents/?search=${encodeURIComponent(filename)}`, { headers });
      expect(response.ok()).toBeTruthy();
      const body = await response.json();
      documentId = body.results?.find((item: { original_filename: string }) => item.original_filename === filename)?.id;
      return documentId;
    }, { timeout: 150_000, intervals: [1000, 2000] }).toBeTruthy();
    const download = await request.get(`/api/v1/documents/${documentId}/download/`, { headers });
    expect(download.ok()).toBeTruthy();
    expect(sha256(await download.body())).toBe(sha256(bytes));
    const detail = await request.get(`/api/v1/documents/${documentId}/`, { headers });
    expect((await detail.json()).content).toContain(subject);
  } finally {
    await request.patch(`/api/v1/mail-accounts/${account.id}/`, { headers, data: { enabled: false } });
  }
});

test('IP allowlists reject a forged forwarding header and security headers protect actual HTTP responses', async ({ request }) => {
  test.setTimeout(90_000);
  const name = 'docvault-e2e-ip-' + process.pid;
  const compose = ['compose', '-f', resolve(process.cwd(), '../deploy/compose.e2e.yml')];
  try {
    execFileSync('docker', [
      ...compose, 'run', '-d', '--no-deps', '--name', name, '--publish', '127.0.0.1:18087:8000',
      '-e', 'IP_WHITELIST=192.0.2.1', '-e', 'DOCVAULT_SKIP_MIGRATIONS=1', 'web', 'web',
    ], { timeout: 30_000, stdio: 'pipe' });
    await expect.poll(async () => {
      try {
        return (await request.get('http://127.0.0.1:18087/api/v1/documents/', { timeout: 2000 })).status();
      } catch {
        return 0;
      }
    }, { timeout: 30_000 }).toBe(403);
    const forged = await request.get('http://127.0.0.1:18087/api/v1/documents/', {
      headers: { 'X-Forwarded-For': '192.0.2.1', 'X-Real-IP': '192.0.2.1' },
    });
    expect(forged.status(), 'Untrusted clients must not bypass the IP policy by supplying forwarding headers').toBe(403);
    expect(forged.headers()['x-content-type-options']).toBe('nosniff');
    expect(forged.headers()['x-frame-options']).toBe('DENY');
    expect(forged.headers()['content-security-policy']).toContain("frame-ancestors 'none'");
  } finally {
    execFileSync('docker', ['rm', '-f', name], { stdio: 'ignore' });
  }
});

test('GPG signs actual stored PDF bytes and verifies the detached signature', async ({ request }) => {
  test.setTimeout(180_000);
  const token = await login(request);
  const headers = authHeaders(token);
  const identity = uniqueName('gpg-acceptance');
  const provision = [
    'from security.signing import get_gpg',
    'g=get_gpg()',
    'key=g.gen_key(g.gen_key_input(key_type="RSA",key_length=2048,name_real="DocVault acceptance",name_email="' + identity + '@example.test",no_protection=True))',
    'assert key.fingerprint, key.stderr',
    'print("ACCEPTANCE_KEY="+key.fingerprint)',
  ].join('\n');
  const output = execFileSync('docker', [
    'compose', '-f', resolve(process.cwd(), '../deploy/compose.e2e.yml'), 'exec', '-T', 'web',
    'python', 'manage.py', 'shell', '-c', provision,
  ], { timeout: 60_000, encoding: 'utf8' });
  const fingerprint = output.match(/ACCEPTANCE_KEY=([A-F0-9]+)/)?.[1];
  expect(fingerprint).toBeTruthy();
  const { doc } = await uploadPdf(request, token, identity);
  const signed = await request.post('/api/v1/documents/' + doc.id + '/sign/', { headers, data: { key_id: fingerprint } });
  expect(signed.status(), await signed.text()).toBe(201);
  const signature = await signed.json();
  expect(signature.verified).toBe(true);
  const verified = await request.post('/api/v1/documents/' + doc.id + '/verify/', { headers, data: { signature_id: signature.id } });
  expect(verified.ok(), await verified.text()).toBeTruthy();
  const verification = await verified.json();
  expect(verification.results[0].valid).toBe(true);
  const signatures = await request.get('/api/v1/documents/' + doc.id + '/signatures/', { headers });
  expect((await signatures.json()).some((item: { id: number; verified: boolean }) => item.id === signature.id && item.verified)).toBe(true);
  const history = await request.get('/api/v1/documents/' + doc.id + '/versions/', { headers });
  const original = (await history.json()).find((item: { version_number: number }) => item.version_number === 1);
  const replacement = await request.post('/api/v1/documents/' + doc.id + '/files/', {
    headers, multipart: {
      document: { name: 'different-signed-artifact.pdf', mimeType: 'application/pdf', buffer: makePdf(identity + ' replacement') },
    },
  });
  expect(replacement.status(), await replacement.text()).toBe(201);
  const invalidated = await request.get('/api/v1/documents/' + doc.id + '/signatures/', { headers });
  expect((await invalidated.json()).find((item: { id: number }) => item.id === signature.id).verified).toBe(false);
  const mismatch = await request.post('/api/v1/documents/' + doc.id + '/verify/', { headers, data: { signature_id: signature.id } });
  expect((await mismatch.json()).results[0].valid).toBe(false);
  const restored = await request.post('/api/v1/documents/' + doc.id + '/versions/' + original.id + '/activate/', { headers });
  expect(restored.ok()).toBeTruthy();
  const validAgain = await request.post('/api/v1/documents/' + doc.id + '/verify/', { headers, data: { signature_id: signature.id } });
  expect((await validAgain.json()).results[0].valid).toBe(true);
});

test('whole document ingestion, private previews and downloads work with MinIO as the storage backend', async ({ request }) => {
  test.skip(process.env['E2E_INTEGRATIONS'] !== '1', 'Requires the isolated MinIO service');
  test.setTimeout(300_000);
  const prefix = 'docvault-e2e-s3-' + process.pid;
  const database = 'docvault_s3_' + process.pid;
  const web = prefix + '-web';
  const worker = prefix + '-worker';
  const redis = prefix + '-redis';
  const volumes = [prefix + '-media', prefix + '-staging', prefix + '-export'];
  const compose = ['compose', '-f', resolve(process.cwd(), '../deploy/compose.e2e.yml')];
  let endpoint = '';
  const title = uniqueName('whole-minio-flow');
  let documentId: number | undefined;
  const run = (args: string[], timeout = 60_000) => execFileSync('docker', args, { timeout, encoding: 'utf8' });
  const variant = [
    '-e', 'DATABASE_URL=postgres://docvault:e2e-only-postgres@db:5432/' + database,
    '-e', 'REDIS_URL=redis://' + redis + ':6379',
    '-e', 'STORAGE_BACKEND=minio', '-e', 'S3_PREFIX=' + prefix,
    '-e', 'LLM_ENABLED=false', '-e', 'NER_ENABLED=false', '-e', 'ELASTICSEARCH_ENABLED=false',
    '-v', volumes[0] + ':/data/media', '-v', volumes[1] + ':/data/consume', '-v', volumes[2] + ':/data/export',
  ];
  try {
    run([...compose, 'exec', '-T', 'db', 'createdb', '-U', 'docvault', database]);
    run(['run', '-d', '--name', redis, '--network', 'docvault-e2e_default', 'redis:7-alpine']);
    run([...compose, 'run', '-d', '--no-deps', '--name', web, '--publish', '127.0.0.1::8000', ...variant, 'web', 'web']);
    const ports = JSON.parse(run(['inspect', '--format', '{{json .NetworkSettings.Ports}}', web]));
    const binding = ports['8000/tcp']?.find((port: { HostIp: string; HostPort: string }) => port.HostIp === '127.0.0.1');
    expect(binding, 'The isolated MinIO web container must publish an actual loopback port').toBeTruthy();
    endpoint = `http://127.0.0.1:${binding.HostPort}`;
    console.info(`Isolated MinIO web endpoint: ${endpoint}`);
    await expect.poll(async () => {
      try {
        return (await request.get(endpoint + '/health/', { timeout: 2000 })).status();
      } catch (error) {
        return error instanceof Error ? error.message : String(error);
      }
    }, { timeout: 90_000 }).toBe(200);
    run(['exec', web, 'python', 'manage.py', 'seed_e2e']);
    run([...compose, 'run', '-d', '--no-deps', '--name', worker, ...variant, '-e', 'CELERY_CONCURRENCY=1', 'worker', 'worker']);
    const signedIn = await request.post(endpoint + '/api/v1/auth/login/', {
      data: { username: 'e2e-admin', password: 'E2e-only-password-123!' },
    });
    expect(signedIn.ok(), await signedIn.text()).toBeTruthy();
    const headers = authHeaders((await signedIn.json()).token);
    const bytes = makePdf(title);
    const accepted = await request.post(endpoint + '/api/v1/documents/upload/', {
      headers, multipart: { title, document: { name: title + '.pdf', mimeType: 'application/pdf', buffer: bytes } },
    });
    expect(accepted.status(), await accepted.text()).toBe(202);
    const taskId = (await accepted.json()).task_id;
    await expect.poll(async () => {
      const response = await request.get(endpoint + '/api/v1/tasks/?page_size=100', { headers });
      expect(response.ok()).toBeTruthy();
      const body = await response.json();
      const task = (body.results ?? body).find((item: { task_id: string }) => item.task_id === taskId);
      if (task?.status === 'failure') throw new Error(task.result);
      documentId = task?.document;
      return task?.status;
    }, { timeout: 150_000, intervals: [1000, 2000] }).toBe('success');
    expect(documentId).toBeTruthy();
    const original = await request.get(endpoint + '/api/v1/documents/' + documentId + '/download/', { headers });
    expect(original.ok()).toBeTruthy();
    expect(sha256(await original.body())).toBe(sha256(bytes));
    const page = await request.get(endpoint + '/api/v1/documents/' + documentId + '/preview/?page=1', { headers });
    expect(page.ok()).toBeTruthy();
    expect(page.headers()['content-type']).toBe('image/png');
    const thumbnail = await request.get(endpoint + '/api/v1/documents/' + documentId + '/preview/', { headers });
    expect(thumbnail.ok()).toBeTruthy();
    expect(thumbnail.headers()['content-type']).toBe('image/webp');
    const archive = await request.get(endpoint + '/api/v1/documents/' + documentId + '/download/?version=archive', { headers });
    expect(archive.ok()).toBeTruthy();
    expect((await archive.body()).subarray(0, 4).toString()).toBe('%PDF');
    expect((await request.get(endpoint + '/api/v1/documents/' + documentId + '/download/')).status()).toBe(401);
  } finally {
    if (!documentId) {
      for (const name of [web, worker]) {
        try { console.error(run(['logs', '--tail', '35', name], 10_000)); } catch { /* startup may have failed */ }
      }
    }
    if (documentId) {
      const cleanup = [
        'import django; django.setup()', 'import json,sys',
        'from documents.models import Document', 'from storage.utils import get_storage_backend',
        'p=json.loads(sys.argv[1]); d=Document.all_objects.get(pk=p["id"],title=p["title"])',
        'assert d.owner.username.startswith("e2e-")',
        'backend=get_storage_backend(); keys={d.filename,d.archive_filename,d.thumbnail_path}',
        'for key in keys:', ' if key: backend.delete(key)',
        'd.hard_delete()',
      ].join('\n');
      try { run(['exec', web, 'python', '-c', cleanup, JSON.stringify({ id: documentId, title })]); } catch { /* disposable database cleanup below */ }
    }
    for (const name of [worker, web, redis]) {
      try { run(['rm', '-f', name], 30_000); } catch { /* container may not have started */ }
    }
    run([...compose, 'exec', '-T', 'db', 'dropdb', '-U', 'docvault', '--if-exists', '--force', database]);
    for (const volume of volumes) {
      try { run(['volume', 'rm', volume], 30_000); } catch { /* volume may not have been created */ }
    }
  }
});
