import { TestBed } from '@angular/core/testing';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { AIService } from './ai.service';
import { environment } from '../../environments/environment';

const BASE = `${environment.apiUrl}/ai`;

describe('AIService', () => {
  let service: AIService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AIService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('semanticSearch', () => {
    it('sends GET to /ai/search/semantic/ with default k=10', () => {
      service.semanticSearch('invoice').subscribe();
      const req = httpMock.expectOne(
        (r) =>
          r.url === `${BASE}/search/semantic/` &&
          r.params.get('query') === 'invoice' &&
          r.params.get('k') === '10',
      );
      expect(req.request.method).toBe('GET');
      req.flush({ results: [], count: 0 });
    });

    it('sends GET with custom k', () => {
      service.semanticSearch('contract', 5).subscribe();
      const req = httpMock.expectOne(
        (r) =>
          r.url === `${BASE}/search/semantic/` &&
          r.params.get('query') === 'contract' &&
          r.params.get('k') === '5',
      );
      expect(req.request.method).toBe('GET');
      req.flush({ results: [], count: 0 });
    });
  });

  describe('hybridSearch', () => {
    it('sends GET to /ai/search/hybrid/ with query and default k=10', () => {
      service.hybridSearch('report').subscribe();
      const req = httpMock.expectOne(
        (r) =>
          r.url === `${BASE}/search/hybrid/` &&
          r.params.get('query') === 'report' &&
          r.params.get('k') === '10',
      );
      expect(req.request.method).toBe('GET');
      req.flush({ results: [], count: 0 });
    });

    it('sends GET with custom k', () => {
      service.hybridSearch('report', 3).subscribe();
      const req = httpMock.expectOne(
        (r) =>
          r.url === `${BASE}/search/hybrid/` &&
          r.params.get('k') === '3',
      );
      expect(req.request.method).toBe('GET');
      req.flush({ results: [], count: 0 });
    });
  });

  describe('similarDocuments', () => {
    it('sends GET to /ai/similar/:documentId/ with default k=10', () => {
      service.similarDocuments(42).subscribe();
      const req = httpMock.expectOne(
        (r) =>
          r.url === `${BASE}/similar/42/` &&
          r.params.get('k') === '10',
      );
      expect(req.request.method).toBe('GET');
      req.flush({ results: [], count: 0 });
    });

    it('sends GET with custom k', () => {
      service.similarDocuments(42, 20).subscribe();
      const req = httpMock.expectOne(
        (r) =>
          r.url === `${BASE}/similar/42/` &&
          r.params.get('k') === '20',
      );
      expect(req.request.method).toBe('GET');
      req.flush({ results: [], count: 0 });
    });
  });

  describe('chatWithDocument', () => {
    it('sends POST to /ai/documents/:documentId/chat/ with request body', () => {
      const chatReq = { question: 'What is this about?', history: [] };
      service.chatWithDocument(42, chatReq).subscribe();
      const req = httpMock.expectOne(`${BASE}/documents/42/chat/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(chatReq);
      req.flush({ answer: 'It is about invoices.', sources: [] });
    });
  });

  describe('globalChat', () => {
    it('sends POST to /ai/chat/ with request body', () => {
      const chatReq = { question: 'Summarize everything' };
      service.globalChat(chatReq).subscribe();
      const req = httpMock.expectOne(`${BASE}/chat/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(chatReq);
      req.flush({ answer: 'Summary here.', sources: [] });
    });
  });

  describe('summarize', () => {
    it('sends GET to /ai/documents/:documentId/summarize/', () => {
      service.summarize(42).subscribe();
      const req = httpMock.expectOne(`${BASE}/documents/42/summarize/`);
      expect(req.request.method).toBe('GET');
      req.flush({ summary: 'This document covers invoicing.' });
    });
  });

  describe('extractEntities', () => {
    it('sends GET to /ai/documents/:documentId/entities/', () => {
      service.extractEntities(42).subscribe();
      const req = httpMock.expectOne(`${BASE}/documents/42/entities/`);
      expect(req.request.method).toBe('GET');
      req.flush({ entities: { people: ['Alice'], orgs: ['Acme'] } });
    });
  });

  describe('suggestTitle', () => {
    it('sends GET to /ai/documents/:documentId/suggest-title/', () => {
      service.suggestTitle(42).subscribe();
      const req = httpMock.expectOne(`${BASE}/documents/42/suggest-title/`);
      expect(req.request.method).toBe('GET');
      req.flush({ suggested_title: 'Invoice for Q1' });
    });
  });

  describe('getConfig', () => {
    it('sends GET to /ai/config/', () => {
      service.getConfig().subscribe();
      const req = httpMock.expectOne(`${BASE}/config/`);
      expect(req.request.method).toBe('GET');
      req.flush({ llm_enabled: true, llm_provider: 'openai', llm_model: 'gpt-4o', embedding_model: 'text-embedding-ada-002', vector_store_count: 100 });
    });
  });

  describe('getStatus', () => {
    it('sends GET to /ai/status/', () => {
      service.getStatus().subscribe();
      const req = httpMock.expectOne(`${BASE}/status/`);
      expect(req.request.method).toBe('GET');
      req.flush({ llm_enabled: true, llm_provider: 'openai', llm_model: 'gpt-4o', embedding_model: 'text-embedding-ada-002', vector_store_count: 100, llm_available: true });
    });
  });

  describe('rebuildIndex', () => {
    it('sends POST to /ai/rebuild-index/ with empty body', () => {
      service.rebuildIndex().subscribe();
      const req = httpMock.expectOne(`${BASE}/rebuild-index/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush({ status: 'ok', message: 'Index rebuilt.' });
    });
  });
});
