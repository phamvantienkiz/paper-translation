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
  stage?: string;
  message?: string;
  error?: string;
  total_segments?: number;
  completed_segments?: number;
}

// 3-Layer Canvas Architecture Types (v3.1)
export interface CanvasBlock {
  id: string;
  block_code: string;
  reading_order: number;
  label: string;
  bbox_norm: [number, number, number, number]; // [x0, y0, x1, y1] normalized to [0.0, 1.0]
  is_translatable: boolean;
  original_text: string;
  translated_text: string | null;
  figure_image_url: string | null;
  is_user_edited: boolean;
}

export interface CanvasPage {
  page_number: number;
  width_pt: number;
  height_pt: number;
  page_image_url: string;
  blocks: CanvasBlock[];
}

export interface CanvasData {
  session_id: string;
  title: string | null;
  total_pages: number;
  pages: CanvasPage[];
}

export type ViewMode = 'TRANSLATED' | 'ORIGINAL' | 'SIDE_BY_SIDE';
export type DisplayMode = 'CANVAS' | 'DUAL_PANE';

