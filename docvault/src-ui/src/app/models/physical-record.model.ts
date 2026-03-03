export interface PhysicalLocation {
  id: number;
  name: string;
  location_type: string;
  parent: number | null;
  barcode: string | null;
  capacity: number | null;
  current_count: number;
  notes: string;
  is_active: boolean;
  children_count: number;
  children?: PhysicalLocation[];
}

export interface PhysicalRecord {
  id: number;
  document: number;
  document_title: string;
  location: number | null;
  location_name: string;
  position: string;
  barcode: string | null;
  condition: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface ChargeOut {
  id: number;
  physical_record: number;
  user: number;
  user_name: string;
  record_barcode: string;
  checked_out_at: string;
  expected_return: string;
  returned_at: string | null;
  notes: string;
  status: string;
}

export interface DestructionCertificate {
  id: number;
  physical_record: number;
  destroyed_at: string;
  destroyed_by: number;
  method: string;
  witness: string;
  notes: string;
}
