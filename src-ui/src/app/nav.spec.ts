import { describe, it, expect } from 'vitest';
import { RAIL, isUnder, normalizeUrl, railItemFor } from './nav';

describe('nav', () => {
  describe('normalizeUrl', () => {
    it('strips a query string', () => {
      expect(normalizeUrl('/search?q=tax&page=2')).toBe('/search');
    });

    it('strips a fragment', () => {
      expect(normalizeUrl('/documents/4#page-2')).toBe('/documents/4');
    });

    it('leaves a bare path alone', () => {
      expect(normalizeUrl('/tags')).toBe('/tags');
    });
  });

  describe('isUnder', () => {
    it('matches the root only against itself', () => {
      expect(isUnder('/', '/')).toBe(true);
      expect(isUnder('/documents', '/')).toBe(false);
    });

    it('matches an exact path', () => {
      expect(isUnder('/documents', '/documents')).toBe(true);
    });

    it('matches a child path', () => {
      expect(isUnder('/documents/42', '/documents')).toBe(true);
    });

    it('does not match a sibling with a shared prefix', () => {
      expect(isUnder('/document-requests', '/documents')).toBe(false);
    });

    it('ignores query strings when matching', () => {
      expect(isUnder('/search?q=x', '/search')).toBe(true);
    });
  });

  describe('railItemFor', () => {
    it('maps the root to the dashboard', () => {
      expect(railItemFor('/')?.key).toBe('dash');
    });

    it('maps a document detail route to the documents cluster', () => {
      expect(railItemFor('/documents/42')?.key).toBe('docs');
    });

    it('maps saved views into the search cluster', () => {
      expect(railItemFor('/saved-views')?.key).toBe('search');
    });

    it('maps correspondents into the organize cluster', () => {
      expect(railItemFor('/correspondents')?.key).toBe('org');
    });

    it('maps zone-ocr review into the ingest cluster', () => {
      expect(railItemFor('/zone-ocr-review')?.key).toBe('ingest');
    });

    it('maps admin subpages into the admin cluster', () => {
      expect(railItemFor('/admin/storage')?.key).toBe('admin');
    });

    it('maps the audit log into the compliance cluster', () => {
      expect(railItemFor('/audit-log')?.key).toBe('comp');
    });

    it('returns undefined for a route outside the rail', () => {
      expect(railItemFor('/403')).toBeUndefined();
    });
  });

  describe('rail definition', () => {
    it('has unique keys', () => {
      const keys = RAIL.map((item) => item.key);
      expect(new Set(keys).size).toBe(keys.length);
    });

    it('gives every cluster with sub-items a variant', () => {
      for (const item of RAIL) {
        if (item.sub?.length) expect(item.subVariant).toBeTruthy();
      }
    });

    it('points every rail item at one of its own match prefixes', () => {
      for (const item of RAIL) {
        expect(item.match.some((prefix) => isUnder(item.path, prefix))).toBe(true);
      }
    });

    it('routes every sub-item back to its own cluster', () => {
      for (const item of RAIL) {
        for (const sub of item.sub ?? []) {
          expect(railItemFor(sub.path)?.key).toBe(item.key);
        }
      }
    });
  });
});
