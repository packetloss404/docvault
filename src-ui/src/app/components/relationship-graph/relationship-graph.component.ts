import {
  Component,
  OnInit,
  OnDestroy,
  AfterViewInit,
  ElementRef,
  ViewChild,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { RelationshipService } from '../../services/relationship.service';
import {
  RelationshipGraph,
  RelationshipGraphNode,
  RelationshipGraphEdge,
} from '../../models/relationship.model';

interface SimNode extends RelationshipGraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  fx: number | null;
  fy: number | null;
}

const NODE_RADIUS = 24;
const EDGE_COLORS = [
  '#0d6efd',
  '#198754',
  '#dc3545',
  '#ffc107',
  '#6f42c1',
  '#0dcaf0',
  '#fd7e14',
  '#20c997',
];

@Component({
  selector: 'app-relationship-graph',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="container-fluid py-3">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h4 class="mb-0">
          <i class="bi bi-share me-2"></i>Relationship Graph
        </h4>
        <div class="d-flex gap-2 align-items-center">
          <span class="text-muted small">Depth:</span>
          @for (d of [1, 2, 3]; track d) {
            <button
              class="btn btn-sm"
              [class.btn-primary]="depth() === d"
              [class.btn-outline-primary]="depth() !== d"
              (click)="setDepth(d)"
            >
              {{ d }}
            </button>
          }
          <a
            [routerLink]="['/documents', documentId, 'relationships']"
            class="btn btn-outline-secondary btn-sm ms-2"
          >
            <i class="bi bi-list-ul me-1"></i>List View
          </a>
          <a
            [routerLink]="['/documents', documentId]"
            class="btn btn-outline-secondary btn-sm"
          >
            <i class="bi bi-arrow-left me-1"></i>Back to Document
          </a>
        </div>
      </div>

      @if (loading()) {
        <div class="text-center py-5">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
        </div>
      } @else if (error()) {
        <div class="alert alert-danger">{{ error() }}</div>
      } @else {
        <!-- Legend -->
        @if (legendItems().length > 0) {
          <div class="card mb-3">
            <div class="card-body py-2 d-flex flex-wrap gap-3">
              <span class="text-muted small me-2">Legend:</span>
              @for (item of legendItems(); track item.label) {
                <span class="d-flex align-items-center gap-1 small">
                  <span
                    class="d-inline-block rounded"
                    [style.width.px]="14"
                    [style.height.px]="14"
                    [style.background]="item.color"
                  ></span>
                  {{ item.label }}
                </span>
              }
              <span class="d-flex align-items-center gap-1 small ms-3">
                <span
                  class="d-inline-block rounded-circle border border-2"
                  style="width: 14px; height: 14px; background: var(--bs-primary);"
                ></span>
                Current Document
              </span>
              <span class="d-flex align-items-center gap-1 small">
                <span
                  class="d-inline-block rounded-circle border border-2"
                  style="width: 14px; height: 14px; background: var(--bs-secondary);"
                ></span>
                Related Document
              </span>
            </div>
          </div>
        }

        <!-- SVG Graph -->
        <div
          class="card"
          style="overflow: hidden; cursor: grab;"
          (mousedown)="onBgMouseDown($event)"
          (mousemove)="onMouseMove($event)"
          (mouseup)="onMouseUp()"
          (mouseleave)="onMouseUp()"
        >
          <svg
            #svgEl
            [attr.width]="svgWidth"
            [attr.height]="svgHeight"
            [attr.viewBox]="
              '0 0 ' + svgWidth + ' ' + svgHeight
            "
            style="display: block;"
          >
            <!-- Edges -->
            @for (edge of simEdges(); track $index) {
              <line
                [attr.x1]="getNodeX(edge.source)"
                [attr.y1]="getNodeY(edge.source)"
                [attr.x2]="getNodeX(edge.target)"
                [attr.y2]="getNodeY(edge.target)"
                [attr.stroke]="getEdgeColor(edge.type)"
                stroke-width="2"
                stroke-opacity="0.6"
              />
              <text
                [attr.x]="(getNodeX(edge.source) + getNodeX(edge.target)) / 2"
                [attr.y]="
                  (getNodeY(edge.source) + getNodeY(edge.target)) / 2 - 6
                "
                text-anchor="middle"
                class="edge-label"
                fill="currentColor"
                font-size="10"
                opacity="0.7"
              >
                {{ edge.label }}
              </text>
            }

            <!-- Nodes -->
            @for (node of simNodes(); track node.id) {
              <g
                [attr.transform]="'translate(' + node.x + ',' + node.y + ')'"
                style="cursor: pointer;"
                (mousedown)="onNodeMouseDown($event, node)"
                (dblclick)="onNodeDoubleClick(node)"
              >
                <circle
                  [attr.r]="nodeRadius"
                  [attr.fill]="
                    node.id === documentId
                      ? 'var(--bs-primary)'
                      : 'var(--bs-secondary)'
                  "
                  stroke="white"
                  stroke-width="2"
                />
                <text
                  dy="4"
                  text-anchor="middle"
                  fill="white"
                  font-size="10"
                  font-weight="bold"
                >
                  {{ node.id }}
                </text>
                <text
                  [attr.y]="nodeRadius + 14"
                  text-anchor="middle"
                  fill="currentColor"
                  font-size="11"
                >
                  {{ truncate(node.title, 20) }}
                </text>
              </g>
            }
          </svg>
        </div>
        <p class="text-muted small mt-2">
          <i class="bi bi-info-circle me-1"></i>Drag nodes to rearrange.
          Double-click a node to navigate to that document.
        </p>
      }
    </div>
  `,
})
export class RelationshipGraphComponent
  implements OnInit, AfterViewInit, OnDestroy
{
  @ViewChild('svgEl') svgEl!: ElementRef<SVGSVGElement>;

  documentId = 0;
  depth = signal(1);
  loading = signal(true);
  error = signal('');

  simNodes = signal<SimNode[]>([]);
  simEdges = signal<RelationshipGraphEdge[]>([]);
  legendItems = signal<{ label: string; color: string }[]>([]);

  svgWidth = 900;
  svgHeight = 550;
  nodeRadius = NODE_RADIUS;

  private animFrameId: number | null = null;
  private dragNode: SimNode | null = null;
  private offsetX = 0;
  private offsetY = 0;
  private edgeTypeColorMap = new Map<string, string>();

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private relationshipService: RelationshipService,
  ) {}

  ngOnInit(): void {
    this.documentId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadGraph();
  }

  ngAfterViewInit(): void {
    this.startSimulation();
  }

  ngOnDestroy(): void {
    this.stopSimulation();
  }

  setDepth(d: number): void {
    this.depth.set(d);
    this.loadGraph();
  }

  loadGraph(): void {
    this.loading.set(true);
    this.error.set('');
    this.relationshipService
      .getRelationshipGraph(this.documentId, this.depth())
      .subscribe({
        next: (graph) => {
          this.initSimulation(graph);
          this.loading.set(false);
        },
        error: (err) => {
          this.error.set(err.error?.detail || 'Failed to load graph.');
          this.loading.set(false);
        },
      });
  }

  private initSimulation(graph: RelationshipGraph): void {
    this.stopSimulation();
    const cx = this.svgWidth / 2;
    const cy = this.svgHeight / 2;

    // Position nodes in a circle around center
    const nodes: SimNode[] = graph.nodes.map((n, i) => {
      const angle = (2 * Math.PI * i) / Math.max(graph.nodes.length, 1);
      const radius = Math.min(this.svgWidth, this.svgHeight) * 0.3;
      return {
        ...n,
        x: n.id === this.documentId ? cx : cx + radius * Math.cos(angle),
        y: n.id === this.documentId ? cy : cy + radius * Math.sin(angle),
        vx: 0,
        vy: 0,
        fx: null,
        fy: null,
      };
    });

    // Build edge type color map
    this.edgeTypeColorMap.clear();
    let colorIdx = 0;
    for (const edge of graph.edges) {
      if (!this.edgeTypeColorMap.has(edge.type)) {
        this.edgeTypeColorMap.set(
          edge.type,
          EDGE_COLORS[colorIdx % EDGE_COLORS.length],
        );
        colorIdx++;
      }
    }

    // Build legend
    const legend: { label: string; color: string }[] = [];
    this.edgeTypeColorMap.forEach((color, type) => {
      const edge = graph.edges.find((e) => e.type === type);
      legend.push({ label: edge?.label || type, color });
    });
    this.legendItems.set(legend);

    this.simNodes.set(nodes);
    this.simEdges.set(graph.edges);
    this.startSimulation();
  }

  private startSimulation(): void {
    const tick = () => {
      this.simulate();
      this.animFrameId = requestAnimationFrame(tick);
    };
    this.animFrameId = requestAnimationFrame(tick);
  }

  private stopSimulation(): void {
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
  }

  private simulate(): void {
    const nodes = this.simNodes();
    const edges = this.simEdges();
    if (nodes.length === 0) return;

    const cx = this.svgWidth / 2;
    const cy = this.svgHeight / 2;
    const damping = 0.85;
    const repulsionStrength = 3000;
    const attractionStrength = 0.005;
    const centerGravity = 0.01;

    // Reset forces
    for (const node of nodes) {
      if (node.fx !== null) {
        node.x = node.fx;
        node.y = node.fy!;
        node.vx = 0;
        node.vy = 0;
        continue;
      }

      let fx = 0;
      let fy = 0;

      // Repulsion between all nodes
      for (const other of nodes) {
        if (other.id === node.id) continue;
        const dx = node.x - other.x;
        const dy = node.y - other.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = repulsionStrength / (dist * dist);
        fx += (dx / dist) * force;
        fy += (dy / dist) * force;
      }

      // Attraction along edges
      for (const edge of edges) {
        let other: SimNode | undefined;
        if (edge.source === node.id) {
          other = nodes.find((n) => n.id === edge.target);
        } else if (edge.target === node.id) {
          other = nodes.find((n) => n.id === edge.source);
        }
        if (other) {
          const dx = other.x - node.x;
          const dy = other.y - node.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          fx += dx * attractionStrength * dist;
          fy += dy * attractionStrength * dist;
        }
      }

      // Center gravity
      fx += (cx - node.x) * centerGravity;
      fy += (cy - node.y) * centerGravity;

      node.vx = (node.vx + fx) * damping;
      node.vy = (node.vy + fy) * damping;
      node.x += node.vx;
      node.y += node.vy;

      // Clamp to bounds
      node.x = Math.max(NODE_RADIUS, Math.min(this.svgWidth - NODE_RADIUS, node.x));
      node.y = Math.max(NODE_RADIUS, Math.min(this.svgHeight - NODE_RADIUS, node.y));
    }

    // Trigger change detection by replacing the array reference
    this.simNodes.set([...nodes]);
  }

  getNodeX(id: number): number {
    return this.simNodes().find((n) => n.id === id)?.x ?? 0;
  }

  getNodeY(id: number): number {
    return this.simNodes().find((n) => n.id === id)?.y ?? 0;
  }

  getEdgeColor(type: string): string {
    return this.edgeTypeColorMap.get(type) || '#6c757d';
  }

  truncate(text: string, max: number): string {
    return text.length > max ? text.substring(0, max) + '...' : text;
  }

  // --- Drag support ---

  onNodeMouseDown(event: MouseEvent, node: SimNode): void {
    event.stopPropagation();
    event.preventDefault();
    this.dragNode = node;
    node.fx = node.x;
    node.fy = node.y;
    const svgRect = this.svgEl?.nativeElement?.getBoundingClientRect();
    if (svgRect) {
      this.offsetX = event.clientX - svgRect.left - node.x;
      this.offsetY = event.clientY - svgRect.top - node.y;
    }
  }

  onBgMouseDown(event: MouseEvent): void {
    // no-op for background; only nodes are draggable
  }

  onMouseMove(event: MouseEvent): void {
    if (!this.dragNode) return;
    const svgRect = this.svgEl?.nativeElement?.getBoundingClientRect();
    if (!svgRect) return;
    const x = event.clientX - svgRect.left - this.offsetX;
    const y = event.clientY - svgRect.top - this.offsetY;
    this.dragNode.fx = Math.max(
      NODE_RADIUS,
      Math.min(this.svgWidth - NODE_RADIUS, x),
    );
    this.dragNode.fy = Math.max(
      NODE_RADIUS,
      Math.min(this.svgHeight - NODE_RADIUS, y),
    );
  }

  onMouseUp(): void {
    if (this.dragNode) {
      this.dragNode.fx = null;
      this.dragNode.fy = null;
      this.dragNode = null;
    }
  }

  onNodeDoubleClick(node: SimNode): void {
    this.router.navigate(['/documents', node.id]);
  }
}
