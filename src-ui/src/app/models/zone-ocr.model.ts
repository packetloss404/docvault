export interface ZoneOCRTemplate {
  id: number;
  name: string;
  description: string;
  sample_page_image: string | null;
  page_number: number;
  is_active: boolean;
  field_count: number;
  created_at: string;
}

export interface ZoneOCRField {
  id: number;
  template: number;
  name: string;
  field_type: string;
  bounding_box: { x: number; y: number; width: number; height: number };
  custom_field: number | null;
  order: number;
  preprocessing: string;
  validation_regex: string;
}

export interface ZoneOCRResult {
  id: number;
  document: number;
  template: number;
  template_name: string;
  field: number;
  field_name: string;
  extracted_value: string;
  confidence: number;
  reviewed: boolean;
  corrected_value: string;
  created_at: string;
}
