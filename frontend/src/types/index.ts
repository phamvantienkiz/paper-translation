export type SessionStatus = 'PENDING' | 'PARSING' | 'TRANSLATING' | 'COMPLETED' | 'FAILED';
export type SourceType = 'PDF' | 'DOCX' | 'ARXIV';
export type SegmentType = 'TITLE' | 'HEADING' | 'PARAGRAPH' | 'TABLE' | 'FIGURE' | 'MATH_DISPLAY';

export interface MathToken {
  id: string;
  token_placeholder: string;
  raw_latex: string;
  is_display_math: boolean;
}

export interface Segment {
  id: string;
  session_id: string;
  order_index: number;
  segment_type: string;
  original_content: string;
  translated_content: string | null;
  media_path: string | null;
  is_user_edited: boolean;
  status: string;
}

export interface Session {
  id: string;
  title: string | null;
  file_name: string;
  source_type: string;
  file_size_bytes: number;
  arxiv_id?: string | null;
  authors?: string | null;
  abstract?: string | null;
  status: SessionStatus;
  progress_percent: number;
  created_at: string;
  updated_at: string;
}

export interface ProgressEvent {
  status: SessionStatus;
  progress_percent: number;
  message?: string;
  error?: string;
}
