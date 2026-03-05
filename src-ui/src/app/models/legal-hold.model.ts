export interface LegalHoldCriteria {
  id: number;
  criteria_type: string;
  value: Record<string, any>;
}

export interface LegalHoldCustodian {
  id: number;
  user: number;
  user_name: string;
  notified_at: string | null;
  acknowledged: boolean;
  acknowledged_at: string | null;
  notes: string;
}

export interface LegalHoldDocument {
  id: number;
  document: number;
  document_title: string;
  held_at: string;
  released_at: string | null;
}

export interface LegalHold {
  id: number;
  name: string;
  matter_number: string;
  description: string;
  status: 'draft' | 'active' | 'released';
  activated_at: string | null;
  released_at: string | null;
  release_reason: string;
  criteria_count: number;
  custodian_count: number;
  document_count: number;
  created_at: string;
  updated_at: string;
}
