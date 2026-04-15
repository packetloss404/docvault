export interface Tag {
  id: number;
  name: string;
  slug: string;
  color: string;
  is_inbox_tag: boolean;
  parent: number | null;
  match: string;
  matching_algorithm: number;
  is_insensitive: boolean;
  document_count: number;
  children_count: number;
  owner: number | null;
  created_at: string;
  updated_at: string;
}

export interface TagTreeNode {
  id: number;
  name: string;
  slug: string;
  color: string;
  is_inbox_tag: boolean;
  parent: number | null;
  children: TagTreeNode[];
  document_count: number;
}

export interface Correspondent {
  id: number;
  name: string;
  slug: string;
  match: string;
  matching_algorithm: number;
  is_insensitive: boolean;
  document_count: number;
  owner: number | null;
  created_at: string;
  updated_at: string;
}

export interface Cabinet {
  id: number;
  name: string;
  slug: string;
  parent: number | null;
  order: number;
  document_count: number;
  children_count: number;
  owner: number | null;
  created_at: string;
  updated_at: string;
}

export interface CabinetTreeNode {
  id: number;
  name: string;
  slug: string;
  parent: number | null;
  children: CabinetTreeNode[];
  document_count: number;
}

export interface StoragePath {
  id: number;
  name: string;
  slug: string;
  path: string;
  match: string;
  matching_algorithm: number;
  is_insensitive: boolean;
  document_count: number;
  owner: number | null;
  created_at: string;
  updated_at: string;
}

export interface AutocompleteItem {
  id: number;
  name: string;
  color?: string;
}

export type CustomFieldDataType =
  | 'string'
  | 'longtext'
  | 'url'
  | 'date'
  | 'datetime'
  | 'boolean'
  | 'integer'
  | 'float'
  | 'monetary'
  | 'documentlink'
  | 'select'
  | 'multiselect';

export interface CustomField {
  id: number;
  name: string;
  slug: string;
  data_type: CustomFieldDataType;
  extra_data: Record<string, unknown>;
  instance_count: number;
  owner: number | null;
  created_at: string;
  updated_at: string;
}

export interface CustomFieldInstance {
  id: number;
  document: number;
  field: number;
  field_name: string;
  field_data_type: CustomFieldDataType;
  value: unknown;
  value_text: string | null;
  value_bool: boolean | null;
  value_url: string | null;
  value_date: string | null;
  value_datetime: string | null;
  value_int: number | null;
  value_float: number | null;
  value_monetary: string | null;
  value_document_ids: number[];
  value_select: unknown;
  created_at: string;
  updated_at: string;
}

export interface MetadataType {
  id: number;
  name: string;
  slug: string;
  label: string;
  default: string;
  lookup: string;
  validation: string;
  parser: string;
  instance_count: number;
  owner: number | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentMetadata {
  id: number;
  document: number;
  metadata_type: number;
  metadata_type_name: string;
  metadata_type_label: string;
  value: string;
  parsed_value: unknown;
  created_at: string;
  updated_at: string;
}

export interface DocumentTypeCustomField {
  id: number;
  document_type: number;
  custom_field: number;
  field_name: string;
  field_data_type: CustomFieldDataType;
  required: boolean;
}

export interface DocumentTypeMetadata {
  id: number;
  document_type: number;
  metadata_type: number;
  metadata_type_name: string;
  required: boolean;
}
