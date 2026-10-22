import React, { useState, useEffect } from 'react';
import { X, Check, Copy, CheckCheck, Loader2, BookOpen, Sparkles, AlertCircle } from 'lucide-react';
import { CanvasBlock } from '../types';
import { MathRenderer } from './MathRenderer';

interface BlockEditModalProps {
  block: CanvasBlock | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (blockId: string, translatedText: string) => Promise<void>;
}

export const BlockEditModal: React.FC<BlockEditModalProps> = ({
  block,
  isOpen,
  onClose,
  onSave,
}) => {
  const [translatedText, setTranslatedText] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copiedOriginal, setCopiedOriginal] = useState(false);

  useEffect(() => {
    if (block) {
      setTranslatedText(block.translated_text || block.original_text || '');
      setErrorMessage(null);
      setCopiedOriginal(false);
    }
  }, [block]);

  if (!isOpen || !block) return null;

  const handleCopyOriginal = async () => {
    try {
      await navigator.clipboard.writeText(block.original_text);
      setCopiedOriginal(true);
      setTimeout(() => setCopiedOriginal(false), 2000);
    } catch (err) {
      console.warn('Clipboard write error', err);
    }
  };

  const handleSave = async () => {
    if (!translatedText.trim()) {
      setErrorMessage('Nội dung bản dịch không được để trống.');
      return;
    }
    setIsSaving(true);
    setErrorMessage(null);
    try {
      await onSave(block.id, translatedText);
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message || 'Lỗi khi lưu khối bản dịch');
    } finally {
      setIsSaving(false);
    }
  };

  const hasMath = /\$|\\\(|\\\[|\\begin\{/.test(translatedText);

  const getLabelVietnamese = (label: string): string => {
    const map: Record<string, string> = {
      title: 'Tiêu đề bài báo',
      heading: 'Tiêu đề mục',
      paragraph: 'Đoạn văn bản',
      table: 'Bảng biểu',
      figure: 'Hình vẽ / Đồ thị',
      caption: 'Chú thích hình/bảng',
      equation: 'Công thức toán',
      list_item: 'Mục danh sách',
      header: 'Đầu trang (Header)',
      footer: 'Chân trang (Footer)',
      footnote: 'Ghi chú cuối trang',
    };
    return map[label.toLowerCase()] || label;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden border border-slate-200"
        role="dialog"
        aria-modal="true"
        aria-labelledby="block-edit-title"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-academic-navy text-white flex items-center justify-center font-mono text-xs font-bold shadow-xs">
              {block.reading_order}
            </div>
            <div>
              <h2 id="block-edit-title" className="text-sm font-bold text-slate-900 flex items-center gap-2">
                Chỉnh sửa khối bản dịch
                <span className="font-mono text-[11px] text-academic-navy bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                  {block.block_code}
                </span>
                <span className="text-[11px] text-slate-500 font-normal">
                  ({getLabelVietnamese(block.label)})
                </span>
              </h2>
              {block.is_user_edited && (
                <span className="text-[11px] text-emerald-600 font-medium">
                  • Khối này đã được hiệu đính thủ công
                </span>
              )}
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors"
            aria-label="Đóng cửa sổ"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-5 overflow-y-auto flex-1">
          {errorMessage && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Original Text */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5" />
                Văn bản gốc (English)
              </label>
              <button
                type="button"
                onClick={handleCopyOriginal}
                className="text-[11px] text-slate-500 hover:text-academic-navy flex items-center gap-1 font-medium transition-colors"
              >
                {copiedOriginal ? (
                  <>
                    <CheckCheck className="w-3 h-3 text-emerald-600" />
                    <span className="text-emerald-600">Đã sao chép</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Sao chép</span>
                  </>
                )}
              </button>
            </div>
            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 font-serif leading-relaxed max-h-36 overflow-y-auto select-text whitespace-pre-wrap">
              {block.original_text}
            </div>
          </div>

          {/* Translated Text Editor */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-academic-navy flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-academic-gold" />
                Bản dịch tiếng Việt (Sửa trực tiếp)
              </label>
              <span className="text-[11px] text-slate-400">
                {translatedText.length} ký tự
              </span>
            </div>
            <textarea
              value={translatedText}
              onChange={(e) => setTranslatedText(e.target.value)}
              rows={5}
              className="w-full p-3.5 border border-slate-300 rounded-xl text-xs font-serif leading-relaxed text-slate-900 focus:ring-2 focus:ring-academic-navy focus:border-academic-navy outline-hidden transition-shadow resize-y"
              placeholder="Nhập nội dung tiếng Việt..."
            />
          </div>

          {/* Live KaTeX Math Preview if math detected */}
          {hasMath && (
            <div className="p-3.5 bg-blue-50/50 border border-blue-200 rounded-xl">
              <div className="text-[11px] font-semibold text-blue-900 uppercase tracking-wider mb-1 flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-blue-600" />
                Xem trước công thức toán KaTeX
              </div>
              <div className="text-xs font-serif text-slate-800">
                <MathRenderer text={translatedText} />
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-2.5">
          <button
            type="button"
            onClick={onClose}
            disabled={isSaving}
            className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-200/60 rounded-xl transition-colors cursor-pointer"
          >
            Hủy
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving}
            className="px-5 py-2 text-xs font-semibold text-white bg-academic-navy hover:bg-academic-navy-dark active:bg-slate-900 rounded-xl transition-all shadow-xs flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            {isSaving ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Check className="w-3.5 h-3.5" />
            )}
            <span>{isSaving ? 'Đang lưu...' : 'Lưu thay đổi'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
