# Storage backends

DocVault stores document files through a pluggable backend. Local disk is the
default; object storage is required for any deployment where more than one
process needs the files — which includes every container platform, because the
web service and the Celery worker both read and write documents.

## Choosing a backend

| Backend | `STORAGE_BACKEND` | Endpoint needed | Notes |
| --- | --- | --- | --- |
| Local filesystem | `local` | — | Single host only, or a shared volume |
| Amazon S3 | `s3` | no | Region-derived endpoint |
| Backblaze B2 | `b2` | yes | S3-compatible API; cheapest egress |
| MinIO | `minio` | yes | Self-hosted; path-style addressing |
| Cloudflare R2 | `r2` | yes | No egress fees; ignores region |

All four object backends share one client. What differs between them is small
and, unhandled, fatal — so each has a preset in
`storage/backends/s3.py::PROVIDER_PRESETS` rather than leaving operators to
discover the flags:

- **B2, MinIO and R2 need checksums disabled.** Since boto3 1.36, every upload
  carries `x-amz-sdk-checksum-algorithm` and `x-amz-checksum-crc32`. B2 rejects
  them outright with *"Unsupported header ... received for this API call"*, and
  the preset therefore sets `request_checksum_calculation=when_required`.
  Amazon S3 supports the headers, so the preset leaves them on there — this is
  a compatibility workaround, not a blanket weakening of integrity checking.
- **MinIO needs path-style addressing.** It is usually reached by host or
  container name, where `bucket.host` does not resolve.

Both are overridable per-deployment with `S3_ADDRESSING_STYLE` and
`S3_DISABLE_CHECKSUMS` if a provider behaves differently.

## Configuring by environment

```bash
STORAGE_BACKEND=b2
S3_BUCKET_NAME=my-docvault-bucket
S3_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
S3_REGION=us-west-004
S3_ACCESS_KEY=<keyID>
S3_SECRET_KEY=<applicationKey>
# Optional
S3_PREFIX=documents          # key prefix; default "documents"
S3_ADDRESSING_STYLE=         # blank = provider preset
S3_DISABLE_CHECKSUMS=        # blank = provider preset
S3_AUTO_CREATE_BUCKET=false  # needs credentials that can create buckets
```

For Amazon S3, omit `S3_ENDPOINT_URL` and set `S3_REGION`. For R2, the endpoint
is `https://<account-id>.r2.cloudflarestorage.com` and the region is ignored.

### Backblaze B2 specifics

Use the **S3-compatible** credentials, not the native B2 ones: an application
key's `keyID` is the access key and the key string is the secret. The endpoint
region must match the one shown for your bucket (`us-west-004` and friends) —
B2 rejects requests signed for a different region.

Scope the application key to the single bucket. That means it cannot list or
create buckets, so leave `S3_AUTO_CREATE_BUCKET` off and create the bucket
yourself; the backend tolerates a `403` from `head_bucket` for exactly this
reason.

## Configuring from the admin UI

**Admin → Storage** exposes the same settings, plus a *Test connection* action
that round-trips a small probe object (put, head, delete) and reports the
provider's error verbatim if it fails. Test before saving.

Database configuration only takes effect when its **enabled** toggle is on;
otherwise the environment variables are used. That ordering means a container
deployment works with no database configuration at all, and the UI is an
override rather than a prerequisite.

The secret key is write-only: the API never returns it. The form shows whether
one is stored, and leaving the field blank on save keeps the existing secret.

## Switching backends

Changing the backend does **not** migrate existing documents. Files already
written to the previous backend stay there and stop resolving. Move the objects
first, then switch. The UI states this next to the selector and repeats it in
the save response, because it is the kind of thing that looks like it worked
until someone opens an old document.

## Encryption

`STORAGE_ENCRYPTION_ENABLED=true` wraps whichever backend is selected in
`EncryptedStorageBackend`, so at-rest encryption composes with object storage
rather than replacing it.
