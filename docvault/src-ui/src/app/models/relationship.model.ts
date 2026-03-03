export interface RelationshipType {
  id: number;
  slug: string;
  label: string;
  icon: string;
  is_directional: boolean;
  is_builtin: boolean;
}

export interface DocumentRelationship {
  id: number;
  source_document: number;
  target_document: number;
  source_title: string;
  target_title: string;
  relationship_type: number;
  relationship_type_label: string;
  relationship_type_icon: string;
  notes: string;
  created_at: string;
}

export interface RelationshipGraphNode {
  id: number;
  title: string;
  document_type: string | null;
}

export interface RelationshipGraphEdge {
  source: number;
  target: number;
  type: string;
  label: string;
}

export interface RelationshipGraph {
  nodes: RelationshipGraphNode[];
  edges: RelationshipGraphEdge[];
}
