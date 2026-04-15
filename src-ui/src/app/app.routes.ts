import { Routes } from '@angular/router';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () =>
      import('./components/login/login.component').then(
        (m) => m.LoginComponent,
      ),
  },
  {
    path: '',
    loadComponent: () =>
      import('./components/layout/layout.component').then(
        (m) => m.LayoutComponent,
      ),
    canActivate: [authGuard],
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./components/dashboard/dashboard.component').then(
            (m) => m.DashboardComponent,
          ),
      },
      {
        path: 'documents',
        loadComponent: () =>
          import('./components/document-list/document-list.component').then(
            (m) => m.DocumentListComponent,
          ),
      },
      {
        path: 'documents/:id/graph',
        loadComponent: () =>
          import(
            './components/relationship-graph/relationship-graph.component'
          ).then((m) => m.RelationshipGraphComponent),
      },
      {
        path: 'documents/:id/relationships',
        loadComponent: () =>
          import(
            './components/relationship-panel/relationship-panel.component'
          ).then((m) => m.RelationshipPanelComponent),
      },
      {
        path: 'documents/:id',
        loadComponent: () =>
          import(
            './components/document-detail/document-detail.component'
          ).then((m) => m.DocumentDetailComponent),
      },
      {
        path: 'search',
        loadComponent: () =>
          import(
            './components/search-results/search-results.component'
          ).then((m) => m.SearchResultsComponent),
      },
      {
        path: 'saved-views/:viewId/results',
        loadComponent: () =>
          import(
            './components/saved-view-results/saved-view-results.component'
          ).then((m) => m.SavedViewResultsComponent),
      },
      {
        path: 'saved-views',
        loadComponent: () =>
          import('./components/saved-views/saved-views.component').then(
            (m) => m.SavedViewsComponent,
          ),
      },
      {
        path: 'tags',
        loadComponent: () =>
          import('./components/tags/tags.component').then(
            (m) => m.TagsComponent,
          ),
      },
      {
        path: 'correspondents',
        loadComponent: () =>
          import(
            './components/correspondents/correspondents.component'
          ).then((m) => m.CorrespondentsComponent),
      },
      {
        path: 'cabinets',
        loadComponent: () =>
          import('./components/cabinets/cabinets.component').then(
            (m) => m.CabinetsComponent,
          ),
      },
      {
        path: 'custom-fields',
        loadComponent: () =>
          import('./components/custom-fields/custom-fields.component').then(
            (m) => m.CustomFieldsComponent,
          ),
      },
      {
        path: 'metadata-types',
        loadComponent: () =>
          import(
            './components/metadata-types/metadata-types.component'
          ).then((m) => m.MetadataTypesComponent),
      },
      {
        path: 'workflows',
        loadComponent: () =>
          import(
            './components/workflow-templates/workflow-templates.component'
          ).then((m) => m.WorkflowTemplatesComponent),
      },
      {
        path: 'workflows/:id',
        loadComponent: () =>
          import(
            './components/workflow-detail/workflow-detail.component'
          ).then((m) => m.WorkflowDetailComponent),
      },
      {
        path: 'notifications',
        loadComponent: () =>
          import('./components/notifications/notifications.component').then(
            (m) => m.NotificationsComponent,
          ),
      },
      {
        path: 'notification-preferences',
        loadComponent: () =>
          import(
            './components/notification-preferences/notification-preferences.component'
          ).then((m) => m.NotificationPreferencesComponent),
      },
      {
        path: 'sources',
        loadComponent: () =>
          import('./components/sources/sources.component').then(
            (m) => m.SourcesComponent,
          ),
      },
      {
        path: 'classifier',
        loadComponent: () =>
          import(
            './components/classifier-status/classifier-status.component'
          ).then((m) => m.ClassifierStatusComponent),
      },
      {
        path: 'barcode-config',
        loadComponent: () =>
          import('./components/barcode-config/barcode-config.component').then(
            (m) => m.BarcodeConfigComponent,
          ),
      },
      {
        path: 'ai-config',
        loadComponent: () =>
          import('./components/ai-config/ai-config.component').then(
            (m) => m.AIConfigComponent,
          ),
      },
      {
        path: 'share-links',
        loadComponent: () =>
          import('./components/share-links/share-links.component').then(
            (m) => m.ShareLinksComponent,
          ),
      },
      {
        path: 'activity',
        loadComponent: () =>
          import('./components/activity-feed/activity-feed.component').then(
            (m) => m.ActivityFeedComponent,
          ),
      },
      {
        path: 'otp-setup',
        loadComponent: () =>
          import('./components/otp-setup/otp-setup.component').then(
            (m) => m.OTPSetupComponent,
          ),
      },
      {
        path: 'audit-log',
        loadComponent: () =>
          import('./components/audit-log/audit-log.component').then(
            (m) => m.AuditLogComponent,
          ),
      },
      {
        path: 'scanner',
        loadComponent: () =>
          import('./components/scanner/scanner.component').then(
            (m) => m.ScannerComponent,
          ),
      },
      {
        path: 'zone-ocr',
        loadComponent: () =>
          import(
            './components/zone-ocr-templates/zone-ocr-templates.component'
          ).then((m) => m.ZoneOcrTemplatesComponent),
      },
      {
        path: 'zone-ocr/:id',
        loadComponent: () =>
          import(
            './components/zone-ocr-detail/zone-ocr-detail.component'
          ).then((m) => m.ZoneOcrDetailComponent),
      },
      {
        path: 'zone-ocr-review',
        loadComponent: () =>
          import(
            './components/zone-ocr-review/zone-ocr-review.component'
          ).then((m) => m.ZoneOcrReviewComponent),
      },
      {
        path: 'entity-browser',
        loadComponent: () =>
          import(
            './components/entity-browser/entity-browser.component'
          ).then((m) => m.EntityBrowserComponent),
      },
      {
        path: 'search-analytics',
        loadComponent: () =>
          import(
            './components/search-analytics/search-analytics.component'
          ).then((m) => m.SearchAnalyticsComponent),
      },
      {
        path: 'synonyms',
        loadComponent: () =>
          import(
            './components/synonym-manager/synonym-manager.component'
          ).then((m) => m.SynonymManagerComponent),
      },
      {
        path: 'curations',
        loadComponent: () =>
          import(
            './components/curation-manager/curation-manager.component'
          ).then((m) => m.CurationManagerComponent),
      },
      {
        path: 'portals',
        loadComponent: () =>
          import('./components/portal-admin/portal-admin.component').then(
            (m) => m.PortalAdminComponent,
          ),
      },
      {
        path: 'document-requests',
        loadComponent: () =>
          import(
            './components/request-manager/request-manager.component'
          ).then((m) => m.RequestManagerComponent),
      },
      {
        path: 'submission-review',
        loadComponent: () =>
          import(
            './components/submission-review/submission-review.component'
          ).then((m) => m.SubmissionReviewComponent),
      },
      {
        path: 'signature-requests',
        loadComponent: () =>
          import(
            './components/signature-requests/signature-requests.component'
          ).then((m) => m.SignatureRequestsComponent),
      },
      {
        path: 'signature-requests/:id',
        loadComponent: () =>
          import(
            './components/signature-request-detail/signature-request-detail.component'
          ).then((m) => m.SignatureRequestDetailComponent),
      },
      {
        path: 'legal-holds',
        loadComponent: () =>
          import(
            './components/legal-hold-dashboard/legal-hold-dashboard.component'
          ).then((m) => m.LegalHoldDashboardComponent),
      },
      {
        path: 'legal-holds/:id',
        loadComponent: () =>
          import(
            './components/legal-hold-detail/legal-hold-detail.component'
          ).then((m) => m.LegalHoldDetailComponent),
      },
      {
        path: 'physical-locations',
        loadComponent: () =>
          import(
            './components/physical-locations/physical-locations.component'
          ).then((m) => m.PhysicalLocationsComponent),
      },
      {
        path: 'charge-outs',
        loadComponent: () =>
          import(
            './components/charge-out-dashboard/charge-out-dashboard.component'
          ).then((m) => m.ChargeOutDashboardComponent),
      },
      {
        path: 'admin/storage',
        loadComponent: () =>
          import('./components/storage-admin/storage-admin.component').then(
            (m) => m.StorageAdminComponent,
          ),
      },
      {
        path: 'profile',
        loadComponent: () =>
          import('./components/profile/profile.component').then(
            (m) => m.ProfileComponent,
          ),
      },
    ],
  },
  {
    path: 'portal/:slug',
    loadComponent: () =>
      import('./components/public-portal/public-portal.component').then(
        (m) => m.PublicPortalComponent,
      ),
  },
  {
    path: 'request/:token',
    loadComponent: () =>
      import('./components/public-request/public-request.component').then(
        (m) => m.PublicRequestComponent,
      ),
  },
  {
    path: 'sign/:token',
    loadComponent: () =>
      import('./components/public-signing/public-signing.component').then(
        (m) => m.PublicSigningComponent,
      ),
  },
  {
    path: 'share/:slug',
    loadComponent: () =>
      import('./components/public-share/public-share.component').then(
        (m) => m.PublicShareComponent,
      ),
  },
  { path: '**', redirectTo: '' },
];
