import { Session, Segment, MathToken, CanvasData, CanvasBlock } from '../types';

const API_BASE = '/api/v1';

export const api = {
  async listSessions(): Promise<Session[]> {
    const res = await fetch(`${API_BASE}/sessions`);
    if (!res.ok) throw new Error('Không thể tải danh sách phiên dịch');
    const json = await res.json();
    return json.data || [];
  },

  async getSession(id: string): Promise<Session> {
    const res = await fetch(`${API_BASE}/sessions/${id}`);
    if (!res.ok) throw new Error('Không thể tải thông tin phiên');
    const json = await res.json();
    return json.data;
  },

  async getSegments(sessionId: string): Promise<Segment[]> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/segments`);
    if (!res.ok) throw new Error('Không thể tải các đoạn văn bản');
    const json = await res.json();
    return json.data || [];
  },

  async getMathTokens(sessionId: string): Promise<MathToken[]> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/tokens`);
    if (!res.ok) return [];
    const json = await res.json();
    return json.data || [];
  },

  async getCanvasData(sessionId: string): Promise<CanvasData> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/canvas-data`);
    if (!res.ok) throw new Error('Không thể tải dữ liệu Canvas bài báo');
    const json = await res.json();
    return json.data;
  },

  async updateBlockTranslation(blockId: string, translatedText: string): Promise<CanvasBlock> {
    const res = await fetch(`${API_BASE}/blocks/${blockId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ translated_text: translatedText }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Không thể cập nhật khối bản dịch' }));
      throw new Error(err.detail || 'Không thể cập nhật khối bản dịch');
    }
    const json = await res.json();
    return json.data;
  },

  async updateSegment(segmentId: string, translatedContent: string): Promise<Segment> {
    const res = await fetch(`${API_BASE}/segments/${segmentId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ translated_content: translatedContent }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Không thể lưu bản dịch' }));
      throw new Error(err.detail || 'Không thể lưu bản dịch');
    }
    const json = await res.json();
    return json.data;
  },

  async startTranslation(sessionId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/translate`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Không thể kích hoạt dịch' }));
      throw new Error(err.detail || 'Không thể kích hoạt dịch');
    }
  },

  getExportPdfUrl(sessionId: string): string {
    return `${API_BASE}/export/${sessionId}/pdf`;
  },

  async uploadFile(file: File): Promise<{ session_id: string; file_name: string; source_type: string; status: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_BASE}/ingestion/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload thất bại' }));
      throw new Error(err.detail || 'Upload thất bại');
    }
    const json = await res.json();
    return json.data;
  },

  async ingestArxiv(arxivUrlOrId: string): Promise<{ session_id: string; file_name: string; source_type: string; status: string }> {
    const res = await fetch(`${API_BASE}/ingestion/arxiv`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        arxiv_input: arxivUrlOrId,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Không thể nạp bài báo arXiv' }));
      throw new Error(err.detail || 'Không thể nạp bài báo arXiv');
    }
    const json = await res.json();
    return json.data;
  },

  subscribeProgress(sessionId: string, onMessage: (data: any) => void, onError?: () => void): () => void {
    const eventSource = new EventSource(`${API_BASE}/sessions/${sessionId}/progress`);

    const handleEvent = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        // Tương thích ngược: nếu backend gửi step thay vì status
        if (!data.status && data.step) {
          data.status = data.step;
        }
        onMessage(data);
      } catch (err) {
        console.error('Failed to parse SSE event data', err);
      }
    };

    eventSource.onmessage = handleEvent;
    eventSource.addEventListener('progress_update', handleEvent as EventListener);
    eventSource.addEventListener('completed', handleEvent as EventListener);
    eventSource.addEventListener('error', handleEvent as EventListener);

    eventSource.onerror = (err) => {
      console.warn('SSE connection error or closed', err);
      if (onError) onError();
      eventSource.close();
    };

    return () => {
      eventSource.removeEventListener('progress_update', handleEvent as EventListener);
      eventSource.removeEventListener('completed', handleEvent as EventListener);
      eventSource.removeEventListener('error', handleEvent as EventListener);
      eventSource.close();
    };
  },
};
