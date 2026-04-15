export interface EntityType {
  id: number;
  name: string;
  label: string;
  color: string;
  icon: string;
  enabled: boolean;
}

export interface Entity {
  id: number;
  document: number;
  entity_type: number;
  entity_type_name: string;
  entity_type_color: string;
  value: string;
  raw_value: string;
  confidence: number;
  start_offset: number;
  end_offset: number;
  page_number: number | null;
}

export interface EntityAggregate {
  id?: number;
  value: string;
  entity_type: string;
  document_count: number;
}

export interface EntityCooccurrence {
  entity: EntityAggregate;
  count: number;
}
