export interface BarcodeConfig {
  separator_barcode: string;
  asn_prefix: string;
  dpi: number;
  max_pages: number;
  upscale: number;
  tag_mapping: Record<string, string>;
  retain_separator_pages: boolean;
  enabled: boolean;
}

export interface AsnAssignment {
  document_id: number;
  asn: number;
}

export interface BulkAsnResult {
  assigned: AsnAssignment[];
  count: number;
}
