import { DvIconName } from './components/icon/icon.component';

export interface SubNavItem {
  label: string;
  path: string;
}

export interface RailItem {
  key: string;
  label: string;
  icon: DvIconName;
  /** Where the rail icon navigates. */
  path: string;
  /** Route prefixes that light this rail item up. */
  match: string[];
  /** Hidden from non-staff users. */
  staffOnly?: boolean;
  /**
   * Peer screens within the cluster. Rendered by `<dv-subnav>`: `chip` for
   * cluster peers, `tab` for the document-scoped Organize sections.
   */
  sub?: SubNavItem[];
  subVariant?: 'chip' | 'tab';
}

/**
 * The Console rail. Ten clusters replace the old two-level sidebar; everything
 * that used to be a nested sidebar link is now chip sub-navigation inside the
 * cluster screen, so the rail itself never scrolls.
 */
export const RAIL: readonly RailItem[] = [
  {
    key: 'dash',
    label: 'Dashboard',
    icon: 'grid',
    path: '/',
    match: ['/'],
  },
  {
    key: 'docs',
    label: 'Documents',
    icon: 'doc',
    path: '/documents',
    match: ['/documents'],
  },
  {
    key: 'search',
    label: 'Search',
    icon: 'search',
    path: '/search',
    match: [
      '/search',
      '/saved-views',
      '/search-analytics',
      '/synonyms',
      '/curations',
      '/entity-browser',
    ],
    subVariant: 'chip',
    sub: [
      { label: 'results', path: '/search' },
      { label: 'saved views', path: '/saved-views' },
      { label: 'analytics', path: '/search-analytics' },
      { label: 'synonyms', path: '/synonyms' },
      { label: 'curations', path: '/curations' },
      { label: 'entities', path: '/entity-browser' },
    ],
  },
  {
    key: 'org',
    label: 'Organize',
    icon: 'tag',
    path: '/tags',
    match: [
      '/tags',
      '/correspondents',
      '/cabinets',
      '/custom-fields',
      '/metadata-types',
    ],
    subVariant: 'tab',
    sub: [
      { label: 'Tags', path: '/tags' },
      { label: 'Correspondents', path: '/correspondents' },
      { label: 'Cabinets', path: '/cabinets' },
      { label: 'Custom fields', path: '/custom-fields' },
      { label: 'Metadata types', path: '/metadata-types' },
    ],
  },
  {
    key: 'sign',
    label: 'E-Signatures',
    icon: 'pen',
    path: '/signature-requests',
    match: ['/signature-requests'],
  },
  {
    key: 'flow',
    label: 'Workflows',
    icon: 'flow',
    path: '/workflows',
    match: ['/workflows'],
  },
  {
    key: 'ingest',
    label: 'Ingest & Processing',
    icon: 'inbox',
    path: '/sources',
    match: [
      '/sources',
      '/scanner',
      '/classifier',
      '/barcode-config',
      '/zone-ocr',
      '/zone-ocr-review',
      '/ai-config',
    ],
    subVariant: 'chip',
    sub: [
      { label: 'sources', path: '/sources' },
      { label: 'scanners', path: '/scanner' },
      { label: 'barcode & asn', path: '/barcode-config' },
      { label: 'ml classifier', path: '/classifier' },
      { label: 'zone ocr', path: '/zone-ocr' },
      { label: 'ocr review', path: '/zone-ocr-review' },
      { label: 'ai config', path: '/ai-config' },
    ],
  },
  {
    key: 'share',
    label: 'Sharing & Portals',
    icon: 'link',
    path: '/share-links',
    match: [
      '/share-links',
      '/portals',
      '/document-requests',
      '/submission-review',
    ],
    subVariant: 'chip',
    sub: [
      { label: 'share links', path: '/share-links' },
      { label: 'portals', path: '/portals' },
      { label: 'doc requests', path: '/document-requests' },
      { label: 'review queue', path: '/submission-review' },
    ],
  },
  {
    key: 'comp',
    label: 'Compliance',
    icon: 'shield',
    path: '/legal-holds',
    match: [
      '/legal-holds',
      '/physical-locations',
      '/charge-outs',
      '/audit-log',
      '/activity',
    ],
    staffOnly: true,
    subVariant: 'chip',
    sub: [
      { label: 'legal holds', path: '/legal-holds' },
      { label: 'locations', path: '/physical-locations' },
      { label: 'charge-outs', path: '/charge-outs' },
      { label: 'audit log', path: '/audit-log' },
      { label: 'activity', path: '/activity' },
    ],
  },
  {
    key: 'admin',
    label: 'Admin',
    icon: 'gear',
    path: '/admin/users',
    match: ['/admin'],
    staffOnly: true,
    subVariant: 'chip',
    sub: [
      { label: 'users', path: '/admin/users' },
      { label: 'groups', path: '/admin/groups' },
      { label: 'roles', path: '/admin/roles' },
      { label: 'permissions', path: '/admin/permissions' },
      { label: 'storage', path: '/admin/storage' },
    ],
  },
];

/** Strips query string and fragment so matching only sees the path. */
export function normalizeUrl(url: string): string {
  return url.split('?')[0].split('#')[0];
}

/** True when `url` sits inside `path`'s subtree. `/` only matches itself. */
export function isUnder(url: string, path: string): boolean {
  const clean = normalizeUrl(url);
  if (path === '/') return clean === '/';
  return clean === path || clean.startsWith(`${path}/`);
}

export function railItemFor(url: string): RailItem | undefined {
  // Longest match wins so `/admin/users` beats a hypothetical `/admin`.
  let best: RailItem | undefined;
  let bestLength = -1;
  for (const item of RAIL) {
    for (const prefix of item.match) {
      if (isUnder(url, prefix) && prefix.length > bestLength) {
        best = item;
        bestLength = prefix.length;
      }
    }
  }
  return best;
}
