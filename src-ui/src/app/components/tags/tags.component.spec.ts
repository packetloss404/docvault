import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { vi } from 'vitest';
import { TagsComponent } from './tags.component';
import { OrganizationService } from '../../services/organization.service';
import { Tag } from '../../models/organization.model';

const MAX_TAG_DEPTH = 5;

const makeTag = (overrides: Partial<Tag> = {}): Tag => ({
  id: 1,
  name: 'Tag',
  slug: 'tag',
  color: '#3b82f6',
  is_inbox_tag: false,
  parent: null,
  match: '',
  matching_algorithm: 0,
  is_insensitive: false,
  document_count: 0,
  children_count: 0,
  owner: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  ...overrides,
});

/** Build a linear chain of tags of the given depth (root at depth 1). */
function buildChain(depth: number): Tag[] {
  const tags: Tag[] = [];
  for (let i = 1; i <= depth; i++) {
    tags.push(makeTag({ id: i, name: `Level ${i}`, parent: i === 1 ? null : i - 1 }));
  }
  return tags;
}

describe('TagsComponent', () => {
  let component: TagsComponent;
  let fixture: ComponentFixture<TagsComponent>;
  let orgService: {
    getTags: ReturnType<typeof vi.fn>;
    createTag: ReturnType<typeof vi.fn>;
    updateTag: ReturnType<typeof vi.fn>;
    deleteTag: ReturnType<typeof vi.fn>;
  };

  const sampleTags = [
    makeTag({ id: 1, name: 'Finance', parent: null }),
    makeTag({ id: 2, name: 'Invoices', parent: 1 }),
  ];

  beforeEach(async () => {
    orgService = {
      getTags: vi.fn().mockReturnValue(of({ count: sampleTags.length, results: sampleTags })),
      createTag: vi.fn().mockReturnValue(of(makeTag())),
      updateTag: vi.fn().mockReturnValue(of(makeTag())),
      deleteTag: vi.fn().mockReturnValue(of(undefined)),
    };

    await TestBed.configureTestingModule({
      imports: [TagsComponent],
      providers: [{ provide: OrganizationService, useValue: orgService }],
    }).compileComponents();

    fixture = TestBed.createComponent(TagsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('ngOnInit / loadTags', () => {
    it('calls getTags on init and populates the tags signal', () => {
      expect(orgService.getTags).toHaveBeenCalled();
      expect(component.tags()).toEqual(sampleTags);
    });

    it('reloads tags when loadTags is called again', () => {
      const newTags = [makeTag({ id: 3, name: 'Legal' })];
      orgService.getTags.mockReturnValue(of({ count: 1, results: newTags }));

      component.loadTags();

      expect(component.tags()).toEqual(newTags);
    });
  });

  describe('startCreate', () => {
    it('sets creating to true and clears editing', () => {
      component.editing.set(sampleTags[0]);
      component.startCreate();
      expect(component.creating()).toBe(true);
      expect(component.editing()).toBeNull();
    });

    it('clears the depthError', () => {
      component.depthError.set('some error');
      component.startCreate();
      expect(component.depthError()).toBeNull();
    });

    it('resets the form fields', () => {
      component.formName.set('Old Name');
      component.formColor.set('#ff0000');
      component.startCreate();
      expect(component.formName()).toBe('');
      expect(component.formColor()).toBe('#3b82f6');
    });
  });

  describe('startEdit', () => {
    it('sets editing to the given tag and populates form fields', () => {
      const tag = makeTag({
        id: 5,
        name: 'My Tag',
        color: '#abc123',
        parent: 2,
        is_inbox_tag: true,
        match: 'foo',
        matching_algorithm: 3,
      });
      component.startEdit(tag);

      expect(component.editing()).toBe(tag);
      expect(component.creating()).toBe(false);
      expect(component.formName()).toBe('My Tag');
      expect(component.formColor()).toBe('#abc123');
      expect(component.formParent()).toBe(2);
      expect(component.formIsInbox()).toBe(true);
      expect(component.formMatch()).toBe('foo');
      expect(component.formAlgorithm()).toBe(3);
    });

    it('clears depthError on startEdit', () => {
      component.depthError.set('old error');
      component.startEdit(sampleTags[0]);
      expect(component.depthError()).toBeNull();
    });
  });

  describe('cancel', () => {
    it('clears creating, editing and depthError, resets form', () => {
      component.creating.set(true);
      component.editing.set(sampleTags[0]);
      component.depthError.set('err');
      component.formName.set('Something');

      component.cancel();

      expect(component.creating()).toBe(false);
      expect(component.editing()).toBeNull();
      expect(component.depthError()).toBeNull();
      expect(component.formName()).toBe('');
    });
  });

  describe('getDepth', () => {
    it('returns 1 for a root tag (no parent)', () => {
      component.tags.set([makeTag({ id: 1, parent: null })]);
      expect(component.getDepth(makeTag({ id: 1, parent: null }))).toBe(1);
    });

    it('returns 2 for a tag with a root parent', () => {
      component.tags.set([
        makeTag({ id: 1, parent: null }),
        makeTag({ id: 2, parent: 1 }),
      ]);
      expect(component.getDepth(makeTag({ id: 2, parent: 1 }))).toBe(2);
    });

    it('returns the correct depth for a 5-level chain', () => {
      const chain = buildChain(5);
      component.tags.set(chain);
      expect(component.getDepth(chain[4])).toBe(5);
    });

    it('handles a cycle without infinite looping', () => {
      const cyclicTags = [
        makeTag({ id: 1, parent: 2 }),
        makeTag({ id: 2, parent: 1 }),
      ];
      component.tags.set(cyclicTags);
      const depth = component.getDepth(cyclicTags[0]);
      expect(depth).toBeGreaterThan(0);
    });
  });

  describe('save – depth enforcement (MAX_TAG_DEPTH = 5)', () => {
    it('blocks save when placing a child under a depth-5 parent would exceed MAX_TAG_DEPTH', () => {
      const chain = buildChain(MAX_TAG_DEPTH);
      component.tags.set(chain);
      component.creating.set(true);
      component.formName.set('Too Deep');
      component.formParent.set(MAX_TAG_DEPTH);

      component.save();

      expect(component.depthError()).toContain(`${MAX_TAG_DEPTH}`);
      expect(orgService.createTag).not.toHaveBeenCalled();
    });

    it('allows save when parent is at depth 4 (new tag would be depth 5 = exactly the limit)', () => {
      const chain = buildChain(4);
      component.tags.set(chain);
      component.creating.set(true);
      component.formName.set('Exactly At Limit');
      component.formParent.set(4);

      orgService.getTags.mockReturnValue(of({ count: 0, results: [] }));
      component.save();

      expect(component.depthError()).toBeNull();
      expect(orgService.createTag).toHaveBeenCalled();
    });

    it('clears depthError when save succeeds with no parent', () => {
      component.tags.set([makeTag({ id: 1, parent: null })]);
      component.depthError.set('old error');
      component.creating.set(true);
      component.formName.set('OK Tag');
      component.formParent.set(null);

      orgService.getTags.mockReturnValue(of({ count: 0, results: [] }));
      component.save();

      expect(component.depthError()).toBeNull();
    });
  });

  describe('save – create', () => {
    beforeEach(() => {
      component.creating.set(true);
      component.editing.set(null);
      component.formName.set('New Tag');
      component.formColor.set('#ff0000');
      component.formParent.set(null);
      component.formIsInbox.set(false);
      component.formMatch.set('pattern');
      component.formAlgorithm.set(2);
      orgService.getTags.mockReturnValue(of({ count: 0, results: [] }));
    });

    it('calls createTag with the form data', () => {
      component.save();

      expect(orgService.createTag).toHaveBeenCalledWith({
        name: 'New Tag',
        color: '#ff0000',
        parent: null,
        is_inbox_tag: false,
        match: 'pattern',
        matching_algorithm: 2,
      });
    });

    it('cancels the form and reloads tags after creation', () => {
      component.save();

      expect(component.creating()).toBe(false);
      expect(orgService.getTags.mock.calls.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('save – edit', () => {
    beforeEach(() => {
      const tag = makeTag({ id: 10, name: 'Old Name', parent: null });
      component.editing.set(tag);
      component.creating.set(false);
      component.formName.set('Updated Name');
      component.formColor.set('#00ff00');
      component.formParent.set(null);
      component.formIsInbox.set(true);
      component.formMatch.set('');
      component.formAlgorithm.set(0);
      orgService.getTags.mockReturnValue(of({ count: 0, results: [] }));
    });

    it('calls updateTag with the correct id and form data', () => {
      component.save();

      expect(orgService.updateTag).toHaveBeenCalledWith(10, {
        name: 'Updated Name',
        color: '#00ff00',
        parent: null,
        is_inbox_tag: true,
        match: '',
        matching_algorithm: 0,
      });
    });

    it('cancels and reloads tags after update', () => {
      component.save();

      expect(component.editing()).toBeNull();
      expect(orgService.getTags.mock.calls.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('deleteTag', () => {
    beforeEach(() => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      orgService.getTags.mockReturnValue(of({ count: 0, results: [] }));
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('calls deleteTag on the service when confirmed', () => {
      const tag = makeTag({ id: 99, name: 'Old Tag' });
      component.deleteTag(tag);
      expect(orgService.deleteTag).toHaveBeenCalledWith(99);
    });

    it('reloads tags after deletion', () => {
      const tag = makeTag({ id: 99 });
      const callsBefore = orgService.getTags.mock.calls.length;
      component.deleteTag(tag);
      expect(orgService.getTags.mock.calls.length).toBeGreaterThan(callsBefore);
    });

    it('does not call deleteTag when the user cancels the confirmation', () => {
      vi.spyOn(window, 'confirm').mockReturnValue(false);
      component.deleteTag(makeTag({ id: 99 }));
      expect(orgService.deleteTag).not.toHaveBeenCalled();
    });
  });
});
