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
    ],
  },
  { path: '**', redirectTo: '' },
];
