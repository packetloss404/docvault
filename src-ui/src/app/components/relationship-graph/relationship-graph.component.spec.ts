import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { Subject } from 'rxjs';
import { RelationshipGraphComponent } from './relationship-graph.component';
import { RelationshipService } from '../../services/relationship.service';
import { RelationshipGraph } from '../../models/relationship.model';

describe('RelationshipGraphComponent simulation', () => {
  let fixture: ComponentFixture<RelationshipGraphComponent>;
  let response: Subject<RelationshipGraph>;
  let frames: Map<number, FrameRequestCallback>;
  let nextFrame: number;

  beforeEach(() => {
    frames = new Map();
    nextFrame = 0;
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      frames.set(++nextFrame, callback);
      return nextFrame;
    });
    vi.stubGlobal('cancelAnimationFrame', (id: number) => frames.delete(id));
    response = new Subject<RelationshipGraph>();
    TestBed.configureTestingModule({
      imports: [RelationshipGraphComponent],
      providers: [
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: '71' }) } } },
        { provide: RelationshipService, useValue: { getRelationshipGraph: vi.fn(() => response.asObservable()) } },
      ],
    });
    fixture = TestBed.createComponent(RelationshipGraphComponent);
    fixture.detectChanges();
  });

  afterEach(() => {
    fixture.destroy();
    vi.unstubAllGlobals();
  });

  function loadGraph(ids: number[]): void {
    response.next({
      nodes: ids.map((id) => ({ id, title: `Document ${id}`, document_type: null })),
      edges: [{ source: 71, target: 72, type: 'reference', label: 'Reference' }],
    });
    fixture.detectChanges();
  }

  function advanceFrame(): void {
    const callbacks = [...frames.values()];
    frames.clear();
    for (const callback of callbacks) callback(nextFrame * 16);
  }

  function edgeLength(): number {
    const component = fixture.componentInstance;
    return Math.hypot(component.getNodeX(71) - component.getNodeX(72), component.getNodeY(71) - component.getNodeY(72));
  }

  it.each([[71, 72], [72, 71]])('keeps linked nodes separated over 1,000 animation frames with node order %j', (...ids) => {
    loadGraph(ids);
    for (let frame = 0; frame < 1000; frame++) {
      advanceFrame();
      expect(edgeLength()).toBeGreaterThan(20);
      for (const node of fixture.componentInstance.simNodes()) {
        expect(Number.isFinite(node.x) && Number.isFinite(node.y)).toBe(true);
        expect(node.x).toBeGreaterThanOrEqual(24);
        expect(node.x).toBeLessThanOrEqual(876);
        expect(node.y).toBeGreaterThanOrEqual(24);
        expect(node.y).toBeLessThanOrEqual(526);
      }
    }
  });

  it('recovers separated nodes from the collapsed boundary positions captured in the CI trace', () => {
    loadGraph([71, 72]);
    fixture.componentInstance.simNodes.update((nodes) => nodes.map((node) => ({ ...node, x: 876, y: 275, vx: 5000, vy: 0 })));
    for (let frame = 0; frame < 1000; frame++) advanceFrame();
    expect(edgeLength()).toBeGreaterThan(48);
    for (const node of fixture.componentInstance.simNodes()) {
      expect(node.x).toBeGreaterThan(24);
      expect(node.x).toBeLessThan(876);
    }
  });

  it('keeps a dragged node fixed and settles after it is released', () => {
    loadGraph([71, 72]);
    const component = fixture.componentInstance;
    const node = component.simNodes()[0];
    component.onNodeMouseDown(new MouseEvent('mousedown', { clientX: node.x, clientY: node.y }), node);
    component.onMouseMove(new MouseEvent('mousemove', { clientX: 300, clientY: 200 }));
    for (let frame = 0; frame < 30; frame++) advanceFrame();
    expect(node.x).toBe(300);
    expect(node.y).toBe(200);
    component.onMouseUp();
    for (let frame = 0; frame < 1000; frame++) advanceFrame();
    expect(edgeLength()).toBeGreaterThan(20);
    expect(node.fx).toBeNull();
    expect(node.fy).toBeNull();
  });
});
