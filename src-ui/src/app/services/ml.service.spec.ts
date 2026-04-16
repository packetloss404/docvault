import { TestBed } from '@angular/core/testing';
import {
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';
import {
  provideHttpClientTesting,
  HttpTestingController,
} from '@angular/common/http/testing';
import { MlService } from './ml.service';
import { environment } from '../../environments/environment';

const API = environment.apiUrl;

describe('MlService', () => {
  let service: MlService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        MlService,
        provideHttpClient(withInterceptorsFromDi()),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(MlService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('getSuggestions', () => {
    it('should GET suggestions for a document', () => {
      const mockSuggestions = {
        tags: [{ id: 1, confidence: 0.9 }],
        correspondent: [],
        document_type: [],
        storage_path: [],
      };

      service.getSuggestions(42).subscribe((result) => {
        expect(result).toEqual(mockSuggestions);
      });

      const req = httpMock.expectOne(`${API}/documents/42/suggestions/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockSuggestions);
    });
  });

  describe('getClassifierStatus', () => {
    it('should GET classifier status', () => {
      const mockStatus = {
        available: true,
        tags_trained: true,
        correspondent_trained: false,
        document_type_trained: true,
        storage_path_trained: false,
      };

      service.getClassifierStatus().subscribe((result) => {
        expect(result).toEqual(mockStatus);
      });

      const req = httpMock.expectOne(`${API}/classifier/status/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockStatus);
    });
  });

  describe('triggerTraining', () => {
    it('should POST to trigger classifier training', () => {
      const mockResponse = { task_id: 'abc-123' };

      service.triggerTraining().subscribe((result) => {
        expect(result).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(`${API}/classifier/train/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush(mockResponse);
    });
  });

  describe('applyTag', () => {
    it('should POST a tag to a document', () => {
      const mockDoc = { id: 5, title: 'Test Doc' };

      service.applyTag(5, 10).subscribe((result) => {
        expect(result).toEqual(mockDoc);
      });

      const req = httpMock.expectOne(`${API}/documents/5/tags/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ tag: 10 });
      req.flush(mockDoc);
    });
  });

  describe('applyCorrespondent', () => {
    it('should PATCH correspondent on a document', () => {
      const mockDoc = { id: 5, title: 'Test Doc', correspondent: 3 };

      service.applyCorrespondent(5, 3).subscribe((result) => {
        expect(result).toEqual(mockDoc);
      });

      const req = httpMock.expectOne(`${API}/documents/5/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual({ correspondent: 3 });
      req.flush(mockDoc);
    });
  });

  describe('applyDocumentType', () => {
    it('should PATCH document_type on a document', () => {
      const mockDoc = { id: 5, title: 'Test Doc', document_type: 7 };

      service.applyDocumentType(5, 7).subscribe((result) => {
        expect(result).toEqual(mockDoc);
      });

      const req = httpMock.expectOne(`${API}/documents/5/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual({ document_type: 7 });
      req.flush(mockDoc);
    });
  });

  describe('applyStoragePath', () => {
    it('should PATCH storage_path on a document', () => {
      const mockDoc = { id: 5, title: 'Test Doc', storage_path: 2 };

      service.applyStoragePath(5, 2).subscribe((result) => {
        expect(result).toEqual(mockDoc);
      });

      const req = httpMock.expectOne(`${API}/documents/5/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual({ storage_path: 2 });
      req.flush(mockDoc);
    });
  });
});
