import React, { useState, useEffect, useCallback } from 'react';
import { api } from './services/api';
import {
  Session,
  Segment,
  MathToken,
  CanvasData,
  DisplayMode,
  ProgressEvent,
} from './types';
import { UploadModal } from './components/UploadModal';
import { CanvasPaperViewer } from './components/CanvasPaperViewer';
import { DualPaneReader } from './components/DualPaneReader';
import {
  BookOpen,
  Plus,
  FolderOpen,
  Sparkles,
  Layers,
  Columns,
  RefreshCw,
  Loader2,
  CheckCircle2,
  Cpu,
  ChevronDown,
  Trash2,
} from 'lucide-react';

export const App: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [canvasData, setCanvasData] = useState<CanvasData | null>(null);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [mathTokens, setMathTokens] = useState<MathToken[]>([]);
  const [displayMode, setDisplayMode] = useState<DisplayMode>('CANVAS');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isTranslating, setIsTranslating] = useState<boolean>(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [isSessionDropdownOpen, setIsSessionDropdownOpen] = useState<boolean>(false);
  const [liveProgress, setLiveProgress] = useState<ProgressEvent | null>(null);

  // Tải danh sách phiên bài báo gần đây
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

  // Tải dữ liệu toàn bộ phiên hiện tại (CanvasData, Segments, MathTokens)
  const loadSessionDetails = useCallback(async (sessionId: string) => {
    try {
      setIsLoading(true);
      const [sessionInfo, canvas, segs, tokens] = await Promise.all([
        api.getSession(sessionId),
        api.getCanvasData(sessionId).catch(() => null),
        api.getSegments(sessionId).catch(() => []),
        api.getMathTokens(sessionId).catch(() => []),
      ]);

      setCurrentSession(sessionInfo);
      setCanvasData(canvas);
      setSegments(segs);
      setMathTokens(tokens);
    } catch (err) {
      console.error('Error loading session data:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Khởi tạo ban đầu
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // Khi currentSessionId thay đổi
  useEffect(() => {
    if (currentSessionId) {
      loadSessionDetails(currentSessionId);
    } else {
      setCurrentSession(null);
      setCanvasData(null);
      setSegments([]);
      setMathTokens([]);
    }
  }, [currentSessionId, loadSessionDetails]);

  // Kênh truyền Server-Sent Events (SSE) theo dõi tiến độ thời gian thực
  useEffect(() => {
    if (!currentSessionId || !currentSession) return;
    if (currentSession.status === 'COMPLETED' || currentSession.status === 'FAILED') {
      setLiveProgress(null);
      return;
    }

    const unsubscribe = api.subscribeProgress(
      currentSessionId,
      (data: ProgressEvent) => {
        setLiveProgress(data);
        setCurrentSession((prev) => (prev ? { ...prev, status: data.status, progress_percent: data.progress_percent } : prev));

        if (data.status === 'COMPLETED') {
          // Khi hoàn tất dịch thuật, tải lại toàn bộ CanvasData & Segments
          loadSessionDetails(currentSessionId);
          setTimeout(() => setLiveProgress(null), 3000);
        }
      },
      () => {
        // SSE closed
      }
    );

    return () => {
      unsubscribe();
    };
  }, [currentSessionId, currentSession?.status, loadSessionDetails]);

  const handleUploadSuccess = async (newSessionId: string) => {
    await loadSessions();
    setCurrentSessionId(newSessionId);
  };

  const handleTriggerTranslate = async () => {
    if (!currentSessionId) return;
    setIsTranslating(true);
    try {
      await api.startTranslation(currentSessionId);
      setCurrentSession((prev) => (prev ? { ...prev, status: 'TRANSLATING', progress_percent: 5 } : prev));
    } catch (err: any) {
      alert(err.message || 'Lỗi khi kích hoạt dịch thuật AI');
    } finally {
      setIsTranslating(false);
    }
  };

  const handleDeleteSession = async (sessionId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!window.confirm('Bạn có chắc chắn muốn xóa bài báo này và toàn bộ ảnh/file tạm trên máy không?')) {
      return;
    }
    try {
      await api.deleteSession(sessionId);
      const remaining = sessions.filter((s) => s.id !== sessionId);
      setSessions(remaining);
      if (currentSessionId === sessionId) {
        if (remaining.length > 0) {
          setCurrentSessionId(remaining[0].id);
        } else {
          setCurrentSessionId(null);
          setCurrentSession(null);
          setCanvasData(null);
          setSegments([]);
          setMathTokens([]);
        }
      }
    } catch (err: any) {
      alert(err.message || 'Lỗi khi xóa bài báo');
    }
  };

  const handleCleanupTemp = async () => {
    try {
      const count = await api.cleanupTempFiles();
      alert(`Đã dọn sạch ${count} file tạm trong backend/storage/temp/.`);
    } catch (err: any) {
      alert(err.message || 'Lỗi khi dọn dẹp file tạm');
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-100 text-slate-800 font-sans">
      {/* Top Navbar */}
      <header className="h-16 bg-white border-b border-slate-200/90 px-4 md:px-6 flex items-center justify-between shadow-xs z-30">
        {/* Brand & Edition */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-academic-navy flex items-center justify-center text-white shadow-xs">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-slate-900 leading-tight flex items-center gap-2">
              Paper Translation
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-blue-50 text-academic-navy font-semibold border border-blue-200">
                v3.1 Layout-Preserving
              </span>
            </h1>
            <p className="text-[11px] text-slate-500 hidden sm:block">
              Dịch bài báo khoa học bảo toàn 100% bố cục gốc, TikZ vector & công thức LaTeX
            </p>
          </div>
        </div>

        {/* View Mode Switcher: Canvas vs Dual-Pane */}
        {currentSession && (
          <div className="hidden lg:flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
            <button
              onClick={() => setDisplayMode('CANVAS')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                displayMode === 'CANVAS'
                  ? 'bg-academic-navy text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
              title="Xem trên HTML5 Canvas 3 lớp giữ nguyên bố cục gốc"
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Bố cục gốc (3-Layer Canvas)</span>
            </button>

            <button
              onClick={() => setDisplayMode('DUAL_PANE')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                displayMode === 'DUAL_PANE'
                  ? 'bg-academic-navy text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
              title="Đọc văn bản song song theo đoạn (Dual-Pane)"
            >
              <Columns className="w-3.5 h-3.5" />
              <span>Đọc song song (Dual-Pane)</span>
            </button>
          </div>
        )}

        {/* Action Controls */}
        <div className="flex items-center gap-2.5">
          {/* Session Selector Dropdown */}
          <div className="relative">
            <button
              onClick={() => setIsSessionDropdownOpen(!isSessionDropdownOpen)}
              className="px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl flex items-center gap-2 transition-colors max-w-xs truncate cursor-pointer"
            >
              <FolderOpen className="w-4 h-4 text-academic-navy shrink-0" />
              <span className="truncate max-w-[140px] sm:max-w-[200px]">
                {currentSession ? currentSession.title || currentSession.file_name : 'Chọn bài báo...'}
              </span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            </button>

            {isSessionDropdownOpen && (
              <div className="absolute right-0 mt-2 w-84 bg-white border border-slate-200 rounded-2xl shadow-xl py-2 z-50 animate-in fade-in duration-100">
                <div className="px-3.5 py-1.5 flex items-center justify-between">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Bài báo gần đây ({sessions.length})
                  </span>
                  <button
                    onClick={handleCleanupTemp}
                    className="text-[10px] text-slate-500 hover:text-rose-600 font-medium transition-colors"
                    title="Xóa toàn bộ file tạm sinh ra trong backend/storage/temp/"
                  >
                    Dọn rác tạm
                  </button>
                </div>
                <div className="max-h-64 overflow-y-auto divide-y divide-slate-100">
                  {sessions.length === 0 ? (
                    <div className="px-4 py-3 text-xs text-slate-400 text-center">Chưa có bài báo nào</div>
                  ) : (
                    sessions.map((s) => (
                      <div
                        key={s.id}
                        onClick={() => {
                          setCurrentSessionId(s.id);
                          setIsSessionDropdownOpen(false);
                        }}
                        className={`w-full text-left px-3.5 py-2.5 hover:bg-slate-50 text-xs transition-colors flex items-center justify-between gap-2 cursor-pointer ${
                          s.id === currentSessionId
                            ? 'bg-blue-50/80 font-bold text-academic-navy'
                            : 'text-slate-700'
                        }`}
                      >
                        <div className="flex flex-col gap-0.5 truncate flex-1 min-w-0">
                          <span className="truncate font-semibold">{s.title || s.file_name}</span>
                          <div className="flex items-center gap-2 text-[10px] text-slate-400">
                            <span>{s.source_type}</span>
                            <span>•</span>
                            <span
                              className={
                                s.status === 'COMPLETED'
                                  ? 'text-emerald-600 font-semibold'
                                  : s.status === 'TRANSLATING'
                                  ? 'text-blue-600 font-semibold'
                                  : ''
                              }
                            >
                              {s.status}
                            </span>
                            <span>•</span>
                            <span>{new Date(s.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>

                        <button
                          onClick={(e) => handleDeleteSession(s.id, e)}
                          className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors shrink-0"
                          title="Xóa bài báo và giải phóng toàn bộ file ảnh/PDF trên đĩa"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Trigger Translation Button */}
          {currentSession && currentSession.status !== 'TRANSLATING' && (
            <button
              onClick={handleTriggerTranslate}
              disabled={isTranslating}
              className="px-3 py-2 bg-amber-50 hover:bg-amber-100 text-academic-gold border border-amber-200 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
              title="Kích hoạt Universal AI dịch thuật toàn bộ bài báo"
            >
              {isTranslating ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Sparkles className="w-3.5 h-3.5" />
              )}
              <span className="hidden sm:inline">
                {currentSession.status === 'COMPLETED' ? 'Dịch lại' : 'Dịch AI'}
              </span>
            </button>
          )}

          {/* Upload Button */}
          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="px-3.5 py-2 bg-academic-navy hover:bg-academic-navy-dark active:bg-slate-900 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">Nạp bài báo</span>
          </button>
        </div>
      </header>

      {/* SSE Live Progress Banner */}
      {liveProgress && (
        <div className="bg-blue-50 border-b border-blue-200 px-6 py-2.5 flex items-center justify-between text-xs text-academic-navy z-20 animate-in slide-in-from-top-2">
          <div className="flex items-center gap-2.5">
            <RefreshCw className="w-4 h-4 animate-spin text-academic-navy shrink-0" />
            <span className="font-semibold">
              {liveProgress.message ||
                (liveProgress.status === 'PARSING'
                  ? 'Đang bóc tách cấu trúc tài liệu bằng Indra OCR...'
                  : 'Universal AI đang tiến hành dịch thuật...')}
            </span>
            {liveProgress.stage && (
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-white text-academic-navy font-bold border border-blue-200">
                {liveProgress.stage}
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            <div className="w-36 bg-blue-200/80 rounded-full h-2 overflow-hidden">
              <div
                className="bg-academic-navy h-2 rounded-full transition-all duration-300"
                style={{ width: `${liveProgress.progress_percent}%` }}
              />
            </div>
            <span className="font-mono font-bold text-xs">{liveProgress.progress_percent}%</span>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 overflow-hidden relative">
        {currentSession ? (
          displayMode === 'CANVAS' && canvasData ? (
            <CanvasPaperViewer
              canvasData={canvasData}
              sessionId={currentSession.id}
              onRefresh={() => currentSessionId && loadSessionDetails(currentSessionId)}
            />
          ) : (
            <DualPaneReader
              session={currentSession}
              segments={segments}
              mathTokens={mathTokens}
              isLoading={isLoading}
              onRefresh={() => currentSessionId && loadSessionDetails(currentSessionId)}
            />
          )
        ) : (
          /* Empty / Welcome State */
          <div className="max-w-4xl mx-auto px-6 py-16 text-center">
            <div className="w-16 h-16 rounded-2xl bg-blue-50 text-academic-navy mx-auto mb-6 flex items-center justify-center shadow-xs border border-blue-200">
              <Cpu className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight mb-3">
              Trình Dịch Thuật Bài Báo Khoa Học IT & AI Giữ Bố Cục
            </h2>
            <p className="text-sm text-slate-600 max-w-xl mx-auto mb-8 leading-relaxed">
              Tái hiện bài báo tiếng Việt trực tiếp trên HTML5 Canvas 3 lớp. Giữ trọn vẹn 100% sơ đồ TikZ vector,
              bảng biểu, cấu trúc 2 cột và công thức toán KaTeX.
            </p>

            <button
              onClick={() => setIsUploadModalOpen(true)}
              className="px-6 py-3 bg-academic-navy hover:bg-academic-navy-dark text-white font-semibold text-sm rounded-xl shadow-paper transition-all inline-flex items-center gap-2 cursor-pointer"
            >
              <Plus className="w-5 h-5" />
              Nạp bài báo khoa học đầu tiên (PDF / DOCX / arXiv)
            </button>

            {/* Feature Highlights */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 text-left">
              <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
                <div className="w-9 h-9 rounded-lg bg-blue-50 text-academic-navy flex items-center justify-center mb-3">
                  <Layers className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-bold text-slate-800 mb-1">Kiến trúc Canvas 3 Lớp</h3>
                <p className="text-xs text-slate-500 leading-relaxed font-serif">
                  Layer 0 giữ ảnh nền gốc độ phân giải cao; Layer 1 xóa vùng chữ dịch; Layer 2 tái hiện chữ tiếng Việt vừa vặn.
                </p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
                <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center mb-3">
                  <Sparkles className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-bold text-slate-800 mb-1">Bảo toàn công thức KaTeX</h3>
                <p className="text-xs text-slate-500 leading-relaxed font-serif">
                  Nhận diện và kết xuất sắc nét các biểu thức toán học inline $..$ và display $$..$$ trên Canvas.
                </p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
                <div className="w-9 h-9 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center mb-3">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-bold text-slate-800 mb-1">Hiệu đính & Xuất PDF 1-Click</h3>
                <p className="text-xs text-slate-500 leading-relaxed font-serif">
                  Chỉnh sửa trực tiếp từng khối dịch ngay trên mặt trang và tải về tệp PDF bản dịch hoàn chỉnh chỉ với 1 cú click.
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
