export interface WorkflowTemplate {
  id: number;
  label: string;
  internal_name: string;
  auto_launch: boolean;
  document_type_ids: number[];
  state_count: number;
  transition_count: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowState {
  id: number;
  workflow: number;
  label: string;
  initial: boolean;
  final: boolean;
  completion: number;
}

export interface WorkflowTransition {
  id: number;
  workflow: number;
  label: string;
  origin_state: number;
  origin_state_label: string;
  destination_state: number;
  destination_state_label: string;
  condition: string;
}

export interface WorkflowTransitionField {
  id: number;
  transition: number;
  name: string;
  label: string;
  field_type: 'char' | 'integer' | 'date' | 'boolean' | 'text';
  required: boolean;
  default: string;
  help_text: string;
}

export interface WorkflowStateAction {
  id: number;
  state: number;
  label: string;
  enabled: boolean;
  when: 'on_entry' | 'on_exit';
  backend_path: string;
  backend_data: Record<string, unknown>;
  condition: string;
  order: number;
}

export interface WorkflowStateEscalation {
  id: number;
  state: number;
  transition: number;
  enabled: boolean;
  amount: number;
  unit: 'minutes' | 'hours' | 'days' | 'weeks';
  condition: string;
  comment: string;
  priority: number;
}

export interface WorkflowInstance {
  id: number;
  workflow: number;
  workflow_label: string;
  document: number;
  current_state: number | null;
  current_state_label: string | null;
  completion: number;
  is_complete: boolean;
  context: Record<string, unknown>;
  launched_at: string;
  state_changed_at: string;
}

export interface WorkflowInstanceLogEntry {
  id: number;
  instance: number;
  datetime: string;
  transition: number | null;
  transition_label: string | null;
  user: number | null;
  username: string | null;
  comment: string;
  transition_field_values: Record<string, string>;
}

export interface ActionBackend {
  backend_path: string;
  label: string;
  description: string;
}
