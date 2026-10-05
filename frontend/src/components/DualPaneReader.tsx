import React, { useState, useRef, useEffect } from 'react';
import { Segment, Session, MathToken } from '../types';
import { MathRenderer } from './MathRenderer';
import { api } from '../services/api';
import {
  Download,
  CheckCircle2,
  Clock,
  AlertTriangle,
  RefreshCw,
  Link2,
  Unlink,
  Edit3,
  Check,
  X,
  Sparkles,
  UserCheck,
  Loader2,
} from 'lucide-react';

interface DualPaneReaderProps {
  session: Session;
  segments: Segment[];
  mathTokens: MathToken[];
  isLoading: boolean;
  onRefresh: () => void;
  onSegmentUpdated?: (updatedSegment: Segment) => void;
}

export const DualPaneReader: React.FC<DualPaneReaderProps> = ({
  session,
  segments,
  mathTokens,
  isLoading,
  onRefresh,
  onSegmentUpdated,
}) => {
  const [activeSegmentIndex, setActiveSegmentIndex] = useState<number | null>(null);
  const [syncScroll, setSyncScroll] = useState<boolean>(true);

  // Inline edit state
  const [editingSegmentId, setEditingSegmentId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState<string>('');
  const [isSavingSegment, setIsSavingSegment] = useState<boolean>(false);
  const [isTriggeringTranslate, setIsTriggeringTranslate] = useState<boolean>(false);

  const leftPaneRef = useRef<HTMLDivElement>(null);
  const rightPaneRef = useRef<HTMLDivElement>(null);
  const isScrollingRef = useRef<boolean>(false);

  // Synchronized scrolling handler
  const handleScroll = (source: 'left' | 'right') => {
    if (!syncScroll || isScrollingRef.current) return;

    const sourceEl = source === 'left' ? leftPaneRef.current : rightPaneRef.current;
    const targetEl = source === 'left' ? rightPaneRef.current : leftPaneRef.current;

    if (!sourceEl || !targetEl) return;

    isScrollingRef.current = true;
    const scrollPercentage = sourceEl.scrollTop / (sourceEl.scrollHeight - sourceEl.clientHeight || 1);
    targetEl.scrollTop = scrollPercentage * (targetEl.scrollHeight - targetEl.clientHeight);

    setTimeout(() => {
      isScrollingRef.current = false;
    }, 50);
  };

  useEffect(() => {
    setActiveSegmentIndex(null);
    setEditingSegmentId(null);
  }, [session.id]);

  const handleStartEdit = (seg: Segment) => {
    setEditingSegmentId(seg.id);
    setEditContent(seg.translated_content || seg.original_content);
  };

  const handleCancelEdit = () => {
    setEditingSegmentId(null);
    setEditContent('');
  };

  const handleSaveEdit = async (segId: string) => {
    setIsSavingSegment(true);
    try {
      const updated = await api.updateSegment(segId, editContent);
      if (onSegmentUpdated) {
        onSegmentUpdated(updated);
      }
      setEditingSegmentId(null);
    } catch (err: any) {
      alert(err.message || 'Lỗi khi lưu phân đoạn');
    } finally {
      setIsSavingSegment(false);
    }
  };

  const handleTriggerTranslate = async () => {
    setIsTriggeringTranslate(true);
    try {
      await api.startTranslation(session.id);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Lỗi khi kích hoạt dịch');
    } finally {
      setIsTriggeringTranslate(false);
    }
  };

  const handleDownloadPdf = () => {
    const url = api.getExportPdfUrl(session.id);
    window.open(url, '_blank');
  };

  const renderSegmentItem = (seg: Segment, isTranslation: boolean) => {
    const text = isTranslation
      ? seg.translated_content || '(Đang chờ dịch thuật...)'
      : seg.original_content;
    const isPendingTranslation = isTranslation && !seg.translated_content;
    const isActive = activeSegmentIndex === seg.order_index;
    const isEditingThis = isTranslation && editingSegmentId === seg.id;

    let typeBadge = null;
    if (seg.segment_type === 'TITLE' || seg.segment_type === 'HEADING') {
      typeBadge = (
        <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 font-semibold border border-blue-200">
          {seg.segment_type === 'TITLE' ? 'Tiêu đề' : 'Mục chính'}
        </span>
      );
    } else if (seg.segment_type === 'MATH_DISPLAY') {
      typeBadge = (
        <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-amber-50 text-amber-600 font-semibold border border-amber-200">
          Công thức
        </span>
      );
    } else if (seg.segment_type === 'TABLE') {
      typeBadge = (
        <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600 font-semibold border border-emerald-200">
          Bảng
        </span>
      );
    } else if (seg.segment_type === 'FIGURE') {
      typeBadge = (
        <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-purple-50 text-purple-600 font-semibold border border-purple-200">
          Hình ảnh
        </span>
      );
    }

    return (
      <div
        key={`${isTranslation ? 'trans' : 'orig'}-${seg.id || seg.order_index}`}
        onMouseEnter={() => !editingSegmentId && setActiveSegmentIndex(seg.order_index)}
        className={`p-4 rounded-xl border transition-all duration-200 ${
          isActive
            ? 'bg-indigo-50/70 border-indigo-300 ring-2 ring-indigo-200/50 shadow-sm'
            : 'bg-white border-slate-200/70 hover:border-slate-300 shadow-[0_1px_2px_rgba(0,0,0,0.02)]'
        }`}
      >
        <div className="flex items-center justify-between text-xs text-slate-400 mb-2 select-none">
          <div className="flex items-center gap-2">
            <span className="font-mono font-medium text-slate-500">#{seg.order_index + 1}</span>
            {typeBadge}
            {isTranslation && seg.is_user_edited && (
              <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 font-medium border border-amber-200" title="Đoạn văn này đã được người dùng chỉnh sửa">
                <UserCheck className="w-3 h-3" /> Đã sửa thủ công
              </span>
            )}
          </div>

          {/* Action button for translated side */}
          {isTranslation && !isEditingThis && (
            <button
              onClick={() => handleStartEdit(seg)}
              className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded border border-transparent hover:border-indigo-200 transition-colors"
              title="Chỉnh sửa trực tiếp đoạn dịch này"
            >
              <Edit3 className="w-3 h-3" />
              Sửa đoạn
            </button>
          )}
        </div>

        {/* Editing mode */}
        {isEditingThis ? (
          <div className="space-y-3 mt-2">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              rows={Math.max(3, editContent.split('\n').length + 1)}
              className="w-full p-3 text-sm border border-indigo-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white font-sans leading-relaxed text-slate-900"
              placeholder="Nhập nội dung chỉnh sửa..."
            />
            <div className="flex items-center justify-end gap-2">
              <button
                onClick={handleCancelEdit}
                disabled={isSavingSegment}
                className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors flex items-center gap-1"
              >
                <X className="w-3.5 h-3.5" /> Hủy
              </button>
              <button
                onClick={() => handleSaveEdit(seg.id)}
                disabled={isSavingSegment}
                className="px-3 py-1.5 text-xs bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium shadow-sm transition-colors flex items-center gap-1 disabled:opacity-50"
              >
                {isSavingSegment ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                Lưu thay đổi
              </button>
            </div>
          </div>
        ) : (
          /* Normal display mode */
          <>
            {seg.segment_type === 'TITLE' ? (
              <h2 className="text-xl font-bold text-slate-900 tracking-tight">
                <MathRenderer text={text} mathTokens={mathTokens} />
              </h2>
            ) : seg.segment_type === 'HEADING' ? (
              <h3 className="text-lg font-bold text-slate-900 tracking-tight">
                <MathRenderer text={text} mathTokens={mathTokens} />
              </h3>
            ) : seg.segment_type === 'MATH_DISPLAY' ? (
              <div className="bg-slate-50/80 rounded-lg p-3 border border-slate-200/60 my-1 overflow-x-auto text-center">
                <MathRenderer text={text} mathTokens={mathTokens} />
              </div>
            ) : seg.segment_type === 'TABLE' ? (
              <div className="bg-slate-50 rounded-lg p-3 border border-slate-200 overflow-x-auto font-mono text-xs text-slate-800">
                <MathRenderer text={text} mathTokens={mathTokens} />
              </div>
            ) : (
              <div className={`text-[15px] leading-relaxed ${isPendingTranslation ? 'italic text-slate-400 font-light' : 'text-slate-800'}`}>
                <MathRenderer text={text} mathTokens={mathTokens} />
              </div>
            )}

            {seg.media_path && (
              <div className="mt-3 rounded-lg overflow-hidden border border-slate-200 max-w-sm">
                <img src={seg.media_path} alt="Embedded figure" className="w-full object-contain max-h-60" />
              </div>
            )}
          </>
        )}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] bg-slate-100">
      {/* Reader Control Toolbar */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between shadow-xs z-10">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-slate-800 truncate max-w-md">
            {session.title || session.file_name}
          </span>
          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-slate-100 text-slate-600 border border-slate-200">
            {session.source_type}
          </span>

          {session.status === 'COMPLETED' ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
              <CheckCircle2 className="w-3.5 h-3.5" /> Hoàn thành
            </span>
          ) : session.status === 'TRANSLATING' ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 animate-pulse">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Đang dịch ({session.progress_percent}%)
            </span>
          ) : session.status === 'PARSING' ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
              <Clock className="w-3.5 h-3.5" /> Đang bóc tách ({session.progress_percent}%)
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-50 text-slate-600 border border-slate-200">
              <AlertTriangle className="w-3.5 h-3.5" /> {session.status}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Nút dịch / Dịch lại nếu cần */}
          {session.status !== 'TRANSLATING' && (
            <button
              onClick={handleTriggerTranslate}
              disabled={isTriggeringTranslate}
              className="px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50"
              title="Kích hoạt tiến trình dịch thuật AI"
            >
              {isTriggeringTranslate ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 text-indigo-600" />}
              <span>{session.status === 'COMPLETED' ? 'Dịch lại AI' : 'Bắt đầu dịch AI'}</span>
            </button>
          )}

          <button
            onClick={() => setSyncScroll(!syncScroll)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors border ${
              syncScroll
                ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
            title="Đồng bộ cuộn trang giữa 2 cột"
          >
            {syncScroll ? <Link2 className="w-3.5 h-3.5" /> : <Unlink className="w-3.5 h-3.5" />}
            <span>{syncScroll ? 'Cuộn song song' : 'Cuộn độc lập'}</span>
          </button>

          <button
            onClick={onRefresh}
            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
            title="Làm mới nội dung"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <button
            onClick={handleDownloadPdf}
            className="inline-flex items-center gap-2 px-4 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 shadow-sm transition-colors cursor-pointer"
            title="Tải về bản dịch đầy đủ dưới định dạng PDF"
          >
            <Download className="w-3.5 h-3.5" />
            Tải PDF bản dịch
          </button>
        </div>
      </div>

      {/* Dual Pane Columns */}
      <div className="flex-1 grid grid-cols-2 divide-x divide-slate-200 overflow-hidden">
        {/* Left Column: Original Paper */}
        <div
          ref={leftPaneRef}
          onScroll={() => handleScroll('left')}
          className="overflow-y-auto p-6 space-y-4 bg-slate-50/60"
        >
          <div className="sticky top-0 bg-slate-50/95 backdrop-blur-sm pb-2 border-b border-slate-200/80 mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-slate-400"></span>
              Văn bản gốc (English)
            </h2>
            <span className="text-xs text-slate-500 font-mono">{segments.length} đoạn</span>
          </div>

          {isLoading && segments.length === 0 ? (
            <div className="py-20 text-center text-slate-400">
              <RefreshCw className="w-8 h-8 mx-auto mb-3 animate-spin text-slate-300" />
              <p className="text-sm">Đang tải các đoạn văn bản...</p>
            </div>
          ) : segments.length === 0 ? (
            <div className="py-20 text-center text-slate-400">
              <p className="text-sm">Chưa có đoạn nào được bóc tách.</p>
            </div>
          ) : (
            segments.map((seg) => renderSegmentItem(seg, false))
          )}
        </div>

        {/* Right Column: Translated Paper */}
        <div
          ref={rightPaneRef}
          onScroll={() => handleScroll('right')}
          className="overflow-y-auto p-6 space-y-4 bg-white"
        >
          <div className="sticky top-0 bg-white/95 backdrop-blur-sm pb-2 border-b border-slate-200/80 mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-indigo-700 uppercase tracking-wider flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
              Bản dịch song ngữ (Tiếng Việt)
            </h2>
            <span className="text-xs text-indigo-600 font-mono">
              {segments.filter((s) => !!s.translated_content).length} / {segments.length} hoàn thành
            </span>
          </div>

          {isLoading && segments.length === 0 ? (
            <div className="py-20 text-center text-slate-400">
              <RefreshCw className="w-8 h-8 mx-auto mb-3 animate-spin text-indigo-400" />
              <p className="text-sm">Đang khởi tạo bản dịch...</p>
            </div>
          ) : segments.length === 0 ? (
            <div className="py-20 text-center text-slate-400">
              <p className="text-sm">Chưa có nội dung dịch.</p>
            </div>
          ) : (
            segments.map((seg) => renderSegmentItem(seg, true))
          )}
        </div>
      </div>
    </div>
  );
};
