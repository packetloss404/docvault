export interface AnnotationReply {
  id: number;
  author_name: string;
  text: string;
  created_at: string;
}

export interface Annotation {
  id: number;
  document: number;
  page: number;
  annotation_type:
    | 'highlight'
    | 'underline'
    | 'strikethrough'
    | 'sticky_note'
    | 'freehand'
    | 'rectangle'
    | 'text_box'
    | 'rubber_stamp';
  coordinates: Record<string, any>;
  content: string;
  color: string;
  opacity: number;
  author_name: string;
  is_private: boolean;
  replies: AnnotationReply[];
  reply_count: number;
  created_at: string;
  updated_at: string;
}
