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
// Edges are drawn in a single hairline token; the relation kind is spelled out
// on the edge label and in the legend rather than encoded as a colour.
const EDGE_STROKE = 'var(--border2)';

@Component({
  selector: 'app-relationship-graph',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-pagehead rg__head">
        <h1 class="dv-h1 dv-h1--sm">Relationship graph</h1>
        <div class="rg__controls dv-push">
          <span class="dv-eyebrow">depth</span>
          @for (d of [1, 2, 3]; track d) {
            <button
              type="button"
              class="dv-navchip"
              [class.is-active]="depth() === d"
              [attr.aria-pressed]="depth() === d"
              (click)="setDepth(d)"
            >
              {{ d }}
            </button>
          }
          <a
            class="dv-btn dv-btn--ghost dv-btn--sm rg__link"
            [routerLink]="['/documents', documentId, 'relationships']"
            >list view</a
          >
          <a
            class="dv-btn dv-btn--ghost dv-btn--sm"
            [routerLink]="['/documents', documentId]"
            >← document</a
          >
        </div>
      </div>

      @if (loading()) {
        <div class="dv-empty">
          <span class="dv-spinner"></span>
          <span class="dv-sr">Loading graph…</span>
        </div>
      } @else if (error()) {
        <div class="dv-card dv-card--r10 rg__error" role="alert">{{ error() }}</div>
      } @else {
        <!-- Legend -->
        <div class="dv-card dv-card--r10 rg__legend">
          <span class="dv-eyebrow">legend</span>
          <span class="rg__key">
            <span class="rg__dot rg__dot--focus" aria-hidden="true"></span>
            this document
          </span>
          <span class="rg__key">
            <span class="rg__dot" aria-hidden="true"></span>
            related document
          </span>
          @if (legendItems().length > 0) {
            <span class="rg__kinds">
              @for (item of legendItems(); track item.label) {
                <span class="dv-chip dv-chip--upper">{{ item.label }}</span>
              }
            </span>
          }
        </div>

        <!-- SVG Graph -->
        <div
          class="dv-well rg__canvas"
          (mousedown)="onBgMouseDown($event)"
          (mousemove)="onMouseMove($event)"
          (mouseup)="onMouseUp()"
          (mouseleave)="onMouseUp()"
        >
          <svg
            #svgEl
            class="rg__svg"
            [attr.width]="svgWidth"
            [attr.height]="svgHeight"
            [attr.viewBox]="'0 0 ' + svgWidth + ' ' + svgHeight"
          >
            <!-- Edges -->
            @for (edge of simEdges(); track $index) {
              <line
                [attr.x1]="getNodeX(edge.source)"
                [attr.y1]="getNodeY(edge.source)"
                [attr.x2]="getNodeX(edge.target)"
                [attr.y2]="getNodeY(edge.target)"
                [attr.stroke]="getEdgeColor(edge.type)"
                stroke-width="1.5"
              />
              <text
                class="rg__edgelabel"
                [attr.x]="(getNodeX(edge.source) + getNodeX(edge.target)) / 2"
                [attr.y]="
                  (getNodeY(edge.source) + getNodeY(edge.target)) / 2 - 6
                "
                text-anchor="middle"
              >
                {{ edge.label }}
              </text>
            }

            <!-- Nodes -->
            @for (node of simNodes(); track node.id) {
              <g
                class="rg__node"
                [attr.transform]="'translate(' + node.x + ',' + node.y + ')'"
                (mousedown)="onNodeMouseDown($event, node)"
                (dblclick)="onNodeDoubleClick(node)"
              >
                <circle
                  [attr.r]="nodeRadius"
                  [class.rg__circle--focus]="node.id === documentId"
                  class="rg__circle"
                />
                <text
                  class="rg__id"
                  [class.rg__id--focus]="node.id === documentId"
                  dy="4"
                  text-anchor="middle"
                >
                  {{ node.id }}
                </text>
                <text
                  class="rg__label"
                  [attr.y]="nodeRadius + 14"
                  text-anchor="middle"
                >
                  {{ truncate(node.title, 20) }}
                </text>
              </g>
            }
          </svg>
        </div>

        <div class="dv-meta rg__hint">
          drag nodes to rearrange · double-click a node to open that document
        </div>
      }
    </div>
  `,
  styleUrl: './relationship-graph.component.scss',
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

    // Register every relation kind present so the legend can list them.
    this.edgeTypeColorMap.clear();
    for (const edge of graph.edges) {
      if (!this.edgeTypeColorMap.has(edge.type)) {
        this.edgeTypeColorMap.set(edge.type, EDGE_STROKE);
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
    const attractionStrength = 0.02;
    const linkDistance = NODE_RADIUS * 5;
    const minDistance = NODE_RADIUS * 2;
    const maxVelocity = NODE_RADIUS / 2;
    const centerGravity = 0.01;
    const nodeById = new Map(nodes.map((node) => [node.id, node]));

    // Compute every force before moving nodes so each step uses the same positions.
    const forces = nodes.map((node) => {
      let fx = 0;
      let fy = 0;

      for (const other of nodes) {
        if (other.id === node.id) continue;
        let dx = node.x - other.x;
        const dy = node.y - other.y;
        if (dx === 0 && dy === 0) dx = node.id < other.id ? -1 : 1;
        const dist = Math.hypot(dx, dy);
        const force = repulsionStrength / Math.max(dist, minDistance) ** 2;
        fx += (dx / dist) * force;
        fy += (dy / dist) * force;
      }

      for (const edge of edges) {
        let other: SimNode | undefined;
        if (edge.source === node.id) {
          other = nodeById.get(edge.target);
        } else if (edge.target === node.id) {
          other = nodeById.get(edge.source);
        }
        if (other) {
          const dx = other.x - node.x;
          const dy = other.y - node.y;
          const dist = Math.hypot(dx, dy) || 1;
          const force = (dist - linkDistance) * attractionStrength;
          fx += (dx / dist) * force;
          fy += (dy / dist) * force;
        }
      }

      fx += (cx - node.x) * centerGravity;
      fy += (cy - node.y) * centerGravity;
      return { fx, fy };
    });

    nodes.forEach((node, index) => {
      if (node.fx !== null) {
        node.x = node.fx;
        node.y = node.fy!;
        node.vx = 0;
        node.vy = 0;
        return;
      }
      node.vx = Math.max(-maxVelocity, Math.min(maxVelocity, (node.vx + forces[index].fx) * damping));
      node.vy = Math.max(-maxVelocity, Math.min(maxVelocity, (node.vy + forces[index].fy) * damping));
      node.x += node.vx;
      node.y += node.vy;

      const x = Math.max(NODE_RADIUS, Math.min(this.svgWidth - NODE_RADIUS, node.x));
      const y = Math.max(NODE_RADIUS, Math.min(this.svgHeight - NODE_RADIUS, node.y));
      if (x !== node.x) node.vx = 0;
      if (y !== node.y) node.vy = 0;
      node.x = x;
      node.y = y;
    });

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
    return this.edgeTypeColorMap.get(type) || EDGE_STROKE;
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
