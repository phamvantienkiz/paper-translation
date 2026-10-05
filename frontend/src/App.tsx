import React, { useState, useEffect, useCallback } from 'react';
import { api } from './services/api';
import { Session, Segment, MathToken } from './types';
import { UploadModal } from './components/UploadModal';
import { DualPaneReader } from './components/DualPaneReader';
import { BookOpen, Plus, FolderOpen, Sparkles, CheckCircle2, Cpu } from 'lucide-react';

export const App: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [mathTokens, setMathTokens] = useState<MathToken[]>([]);
  const [isLoadingSegments, setIsLoadingSegments] = useState<boolean>(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [isSessionDropdownOpen, setIsSessionDropdownOpen] = useState<boolean>(false);

  // Fetch list of sessions
  const loadSessions = useCallback(async () => {
    try {
      const list = await api.listSessions();
      setSessions(list);
      if (!currentSessionId && list.length > 0) {
        setCurrentSessionId(list[0].id);
      }
    } catch (err) {
      console.error('Error fetching sessions:', err);
    }
  }, [currentSessionId]);

  // Load session segments and math tokens
  const loadCurrentSessionData = useCallback(async (sessionId: string) => {
    try {
      setIsLoadingSegments(true);
      const [sessionData, segs, tokens] = await Promise.all([
        api.getSession(sessionId),
        api.getSegments(sessionId),
        api.getMathTokens(sessionId),
      ]);
      setCurrentSession(sessionData);
      setSegments(segs);
      setMathTokens(tokens);
    } catch (err) {
      console.error('Error fetching session data:', err);
    } finally {
      setIsLoadingSegments(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // When currentSessionId changes, load its data
  useEffect(() => {
    if (currentSessionId) {
      loadCurrentSessionData(currentSessionId);
    } else {
      setCurrentSession(null);
      setSegments([]);
      setMathTokens([]);
    }
  }, [currentSessionId, loadCurrentSessionData]);

  // SSE subscription for live progress when parsing/translating
  useEffect(() => {
    if (!currentSessionId || !currentSession) return;
    if (currentSession.status === 'COMPLETED' || currentSession.status === 'FAILED') return;

    const unsubscribe = api.subscribeProgress(
      currentSessionId,
      (data) => {
        setCurrentSession((prev) => (prev ? { ...prev, ...data } : prev));
        // If segments count changed or status completed, re-fetch
        if (data.status === 'COMPLETED' || (data.total_segments && data.total_segments > segments.length)) {
          api.getSegments(currentSessionId).then(setSegments).catch(console.error);
          api.getMathTokens(currentSessionId).then(setMathTokens).catch(console.error);
        }
      },
      () => {
        // SSE closed or errored
      }
    );

    return () => {
      unsubscribe();
    };
  }, [currentSessionId, currentSession?.status, segments.length]);

  const handleUploadSuccess = async (newSessionId: string) => {
    await loadSessions();
    setCurrentSessionId(newSessionId);
  };

  const handleSegmentUpdated = (updated: Segment) => {
    setSegments((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-100 text-slate-800">
      {/* Top Navbar */}
      <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between shadow-xs z-20">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-indigo-200 shadow-md">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-900 leading-tight flex items-center gap-2">
              Paper Translation
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 font-semibold border border-indigo-200">
                IT & AI Edition
              </span>
            </h1>
            <p className="text-xs text-slate-500">Dịch song ngữ tài liệu khoa học bảo toàn LaTeX & định dạng</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Session Selector */}
          <div className="relative">
            <button
              onClick={() => setIsSessionDropdownOpen(!isSessionDropdownOpen)}
              className="px-3 py-2 text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl flex items-center gap-2 transition-colors max-w-xs truncate"
            >
              <FolderOpen className="w-4 h-4 text-slate-500 flex-shrink-0" />
              <span className="truncate">
                {currentSession ? currentSession.title || currentSession.file_name : 'Chọn bài báo...'}
              </span>
            </button>

            {isSessionDropdownOpen && (
              <div className="absolute right-0 mt-2 w-80 bg-white border border-slate-200 rounded-xl shadow-xl py-2 z-50">
                <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Các bài dịch gần đây ({sessions.length})
                </div>
                <div className="max-h-64 overflow-y-auto divide-y divide-slate-100">
                  {sessions.length === 0 ? (
                    <div className="px-4 py-3 text-xs text-slate-400 text-center">Chưa có bài báo nào</div>
                  ) : (
                    sessions.map((s) => (
                      <button
                        key={s.id}
                        onClick={() => {
                          setCurrentSessionId(s.id);
                          setIsSessionDropdownOpen(false);
                        }}
                        className={`w-full text-left px-3 py-2.5 hover:bg-slate-50 text-xs transition-colors flex flex-col gap-0.5 ${
                          s.id === currentSessionId ? 'bg-indigo-50/60 font-semibold text-indigo-700' : 'text-slate-700'
                        }`}
                      >
                        <span className="truncate font-medium">{s.title || s.file_name}</span>
                        <div className="flex items-center gap-2 text-[10px] text-slate-400">
                          <span>{s.source_type}</span>
                          <span>•</span>
                          <span>{s.status}</span>
                          <span>•</span>
                          <span>{new Date(s.created_at).toLocaleDateString()}</span>
                        </div>
                      </button>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Upload Button */}
          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all"
          >
            <Plus className="w-4 h-4" />
            Nạp bài báo mới
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 overflow-hidden">
        {currentSession ? (
          <DualPaneReader
            session={currentSession}
            segments={segments}
            mathTokens={mathTokens}
            isLoading={isLoadingSegments}
            onRefresh={() => currentSessionId && loadCurrentSessionData(currentSessionId)}
            onSegmentUpdated={handleSegmentUpdated}
          />
        ) : (
          <div className="max-w-4xl mx-auto px-6 py-16 text-center">
            <div className="w-16 h-16 rounded-2xl bg-indigo-100 text-indigo-600 mx-auto mb-6 flex items-center justify-center shadow-inner">
              <Cpu className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight mb-3">
              Trình dịch thuật tài liệu khoa học chuyên ngành IT / AI
            </h2>
            <p className="text-sm text-slate-600 max-w-xl mx-auto mb-8 leading-relaxed">
              Giải pháp dịch song ngữ tối ưu cho cá nhân và cộng đồng. Bóc tách và bảo toàn 100% công thức toán học LaTeX,
              bảng biểu và hình ảnh cấu trúc.
            </p>

            <button
              onClick={() => setIsUploadModalOpen(true)}
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm rounded-xl shadow-lg shadow-indigo-200 transition-all inline-flex items-center gap-2"
            >
              <Plus className="w-5 h-5" />
              Nạp bài báo khoa học đầu tiên (PDF / DOCX / arXiv)
            </button>

            {/* Feature highlights */}
            <div className="grid grid-cols-3 gap-6 mt-16 text-left">
              <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
                <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3">
                  <Sparkles className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-semibold text-slate-800 mb-1">Bảo toàn công thức LaTeX</h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Tự động mask các biểu thức toán học inline và display bằng token độc nhất, chống vỡ mã hoặc sai lệch số học.
                </p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
                <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center mb-3">
                  <BookOpen className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-semibold text-slate-800 mb-1">Giao diện song song (Dual-Pane)</h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Đọc song song bản gốc và bản dịch tiếng Việt với cơ chế cuộn đồng bộ và highlight đoạn văn bản tương ứng.
                </p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
                <div className="w-9 h-9 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center mb-3">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-semibold text-slate-800 mb-1">Hỗ trợ đa định dạng</h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Xử lý mượt mà tệp PDF khoa học, tệp Word DOCX, hoặc nạp trực tiếp chỉ với ID/URL bài báo trên arXiv.
                </p>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSuccess={handleUploadSuccess}
      />
    </div>
  );
};
export default App;
