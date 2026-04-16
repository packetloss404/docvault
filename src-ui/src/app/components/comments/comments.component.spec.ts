import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, Subject, throwError } from 'rxjs';
import { vi } from 'vitest';
import { CommentsComponent } from './comments.component';
import { CollaborationService } from '../../services/collaboration.service';
import { AuthService } from '../../services/auth.service';
import { Comment } from '../../models/collaboration.model';

const makeComment = (overrides: Partial<Comment> = {}): Comment => ({
  id: 1,
  document: 10,
  user: 42,
  username: 'alice',
  text: 'Hello world',
  created_at: '2024-01-01T10:00:00Z',
  updated_at: '2024-01-01T10:00:00Z',
  ...overrides,
});

describe('CommentsComponent', () => {
  let component: CommentsComponent;
  let fixture: ComponentFixture<CommentsComponent>;
  let collaborationService: {
    getComments: ReturnType<typeof vi.fn>;
    addComment: ReturnType<typeof vi.fn>;
    updateComment: ReturnType<typeof vi.fn>;
    deleteComment: ReturnType<typeof vi.fn>;
  };
  let currentUserFn: ReturnType<typeof vi.fn>;

  const sampleComments: Comment[] = [
    makeComment({ id: 1, user: 42, username: 'alice', text: 'First comment' }),
    makeComment({ id: 2, user: 99, username: 'bob', text: 'Second comment' }),
  ];

  beforeEach(async () => {
    currentUserFn = vi.fn().mockReturnValue({ id: 42, username: 'alice' });

    collaborationService = {
      getComments: vi.fn().mockReturnValue(of(sampleComments)),
      addComment: vi.fn().mockReturnValue(of(makeComment())),
      updateComment: vi.fn().mockReturnValue(of(makeComment())),
      deleteComment: vi.fn().mockReturnValue(of(undefined)),
    };

    const authService = { currentUser: currentUserFn };

    await TestBed.configureTestingModule({
      imports: [CommentsComponent],
      providers: [
        { provide: CollaborationService, useValue: collaborationService },
        { provide: AuthService, useValue: authService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CommentsComponent);
    component = fixture.componentInstance;
    component.documentId = 10;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('loadComments', () => {
    it('calls getComments with the documentId on init', () => {
      expect(collaborationService.getComments).toHaveBeenCalledWith(10);
    });

    it('populates the comments signal', () => {
      expect(component.comments()).toEqual(sampleComments);
    });

    it('sets loading to false after successful fetch', () => {
      expect(component.loading()).toBe(false);
    });

    it('sets loading to false on error', () => {
      collaborationService.getComments.mockReturnValue(throwError(() => new Error('Network')));
      component.loadComments();
      expect(component.loading()).toBe(false);
    });

    it('sets loading to true while fetching (before observable emits)', () => {
      const slowSubject = new Subject<Comment[]>();
      collaborationService.getComments.mockReturnValue(slowSubject.asObservable());

      component.loadComments();

      expect(component.loading()).toBe(true);

      slowSubject.next([]);
      expect(component.loading()).toBe(false);
    });
  });

  describe('addComment', () => {
    beforeEach(() => {
      collaborationService.getComments.mockReturnValue(of([]));
    });

    it('does not call addComment when the text is empty', () => {
      component.newCommentText.set('   ');
      component.addComment();
      expect(collaborationService.addComment).not.toHaveBeenCalled();
    });

    it('calls addComment with the documentId and trimmed text', () => {
      component.newCommentText.set('  My new comment  ');
      component.addComment();
      expect(collaborationService.addComment).toHaveBeenCalledWith(10, 'My new comment');
    });

    it('sets submitting to true while the request is in progress', () => {
      const slowSubject = new Subject<Comment>();
      collaborationService.addComment.mockReturnValue(slowSubject.asObservable());

      component.newCommentText.set('A comment');
      component.addComment();

      expect(component.submitting()).toBe(true);
    });

    it('clears newCommentText and reloads comments after success', () => {
      component.newCommentText.set('A comment');
      component.addComment();

      expect(component.newCommentText()).toBe('');
      expect(component.submitting()).toBe(false);
      expect(collaborationService.getComments.mock.calls.length).toBeGreaterThanOrEqual(2);
    });

    it('sets submitting to false on error', () => {
      collaborationService.addComment.mockReturnValue(throwError(() => new Error('fail')));
      component.newCommentText.set('A comment');
      component.addComment();
      expect(component.submitting()).toBe(false);
    });
  });

  describe('startEdit / cancelEdit', () => {
    it('sets editingComment and editText on startEdit', () => {
      const comment = sampleComments[0];
      component.startEdit(comment);
      expect(component.editingComment()).toBe(comment);
      expect(component.editText()).toBe(comment.text);
    });

    it('clears editingComment and editText on cancelEdit', () => {
      component.startEdit(sampleComments[0]);
      component.cancelEdit();
      expect(component.editingComment()).toBeNull();
      expect(component.editText()).toBe('');
    });
  });

  describe('saveEdit', () => {
    beforeEach(() => {
      collaborationService.getComments.mockReturnValue(of([]));
      component.startEdit(sampleComments[0]);
      component.editText.set('Updated text');
    });

    it('does nothing when no comment is being edited', () => {
      component.editingComment.set(null);
      component.saveEdit();
      expect(collaborationService.updateComment).not.toHaveBeenCalled();
    });

    it('does nothing when edit text is blank', () => {
      component.editText.set('   ');
      component.saveEdit();
      expect(collaborationService.updateComment).not.toHaveBeenCalled();
    });

    it('calls updateComment with documentId, commentId and trimmed text', () => {
      component.saveEdit();
      expect(collaborationService.updateComment).toHaveBeenCalledWith(10, 1, 'Updated text');
    });

    it('cancels edit and reloads after success', () => {
      component.saveEdit();
      expect(component.editingComment()).toBeNull();
      expect(component.submitting()).toBe(false);
      expect(collaborationService.getComments.mock.calls.length).toBeGreaterThanOrEqual(2);
    });

    it('sets submitting to false on error', () => {
      collaborationService.updateComment.mockReturnValue(throwError(() => new Error('fail')));
      component.saveEdit();
      expect(component.submitting()).toBe(false);
    });
  });

  describe('deleteComment', () => {
    beforeEach(() => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      collaborationService.getComments.mockReturnValue(of([]));
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('calls deleteComment with documentId and commentId when confirmed', () => {
      component.deleteComment(sampleComments[0]);
      expect(collaborationService.deleteComment).toHaveBeenCalledWith(10, 1);
    });

    it('reloads comments after deletion', () => {
      const callsBefore = collaborationService.getComments.mock.calls.length;
      component.deleteComment(sampleComments[0]);
      expect(collaborationService.getComments.mock.calls.length).toBeGreaterThan(callsBefore);
    });

    it('does not call deleteComment when the user cancels the dialog', () => {
      vi.spyOn(window, 'confirm').mockReturnValue(false);
      component.deleteComment(sampleComments[0]);
      expect(collaborationService.deleteComment).not.toHaveBeenCalled();
    });
  });

  describe('isOwnComment', () => {
    it('returns true when the comment user matches the current user id', () => {
      currentUserFn.mockReturnValue({ id: 42, username: 'alice' });
      expect(component.isOwnComment(makeComment({ user: 42 }))).toBe(true);
    });

    it('returns false when the comment user does not match', () => {
      currentUserFn.mockReturnValue({ id: 42, username: 'alice' });
      expect(component.isOwnComment(makeComment({ user: 99 }))).toBe(false);
    });

    it('returns false when there is no current user', () => {
      currentUserFn.mockReturnValue(null);
      expect(component.isOwnComment(makeComment({ user: 42 }))).toBe(false);
    });
  });

  describe('formatTime', () => {
    it('returns "just now" for dates less than a minute ago', () => {
      const now = new Date().toISOString();
      expect(component.formatTime(now)).toBe('just now');
    });

    it('returns minutes for dates within the last hour', () => {
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
      expect(component.formatTime(fiveMinutesAgo)).toBe('5m ago');
    });

    it('returns hours for dates within the last 24 hours', () => {
      const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
      expect(component.formatTime(twoHoursAgo)).toBe('2h ago');
    });

    it('returns days for dates within the last 7 days', () => {
      const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString();
      expect(component.formatTime(threeDaysAgo)).toBe('3d ago');
    });

    it('returns a locale date string for dates older than 7 days', () => {
      const old = new Date(2020, 0, 1);
      const result = component.formatTime(old.toISOString());
      expect(result).toBe(old.toLocaleDateString());
    });
  });
});
