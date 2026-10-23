import React, { useState, useRef } from 'react';
import { Upload, Link as LinkIcon, FileText, X, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../services/api';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (sessionId: string) => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [activeTab, setActiveTab] = useState<'file' | 'arxiv'>('file');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [arxivInput, setArxivInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const ext = file.name.split('.').pop()?.toLowerCase();
      if (ext !== 'pdf' && ext !== 'docx') {
        setErrorMessage('Chỉ chấp nhận tệp định dạng .pdf hoặc .docx');
        return;
      }
      setSelectedFile(file);
      setErrorMessage(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      const ext = file.name.split('.').pop()?.toLowerCase();
      if (ext !== 'pdf' && ext !== 'docx') {
        setErrorMessage('Chỉ chấp nhận tệp định dạng .pdf hoặc .docx');
        return;
      }
      setSelectedFile(file);
      setErrorMessage(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      let result: { session_id: string };
      if (activeTab === 'file') {
        if (!selectedFile) {
          throw new Error('Vui lòng chọn một tệp PDF hoặc DOCX để tải lên');
        }
        result = await api.uploadFile(selectedFile);
      } else {
        if (!arxivInput.trim()) {
          throw new Error('Vui lòng nhập arXiv ID hoặc URL hợp lệ (ví dụ: 1706.03762)');
        }
        result = await api.ingestArxiv(arxivInput.trim());
      }
      onSuccess(result.session_id);
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message || 'Đã có lỗi xảy ra khi nạp tài liệu');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden border border-slate-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          <div>
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">Nạp bài báo khoa học</h2>
            <p className="text-xs text-slate-500">Tối ưu cho văn bản công nghệ thông tin & trí tuệ nhân tạo (LaTeX & Bố cục 2 cột)</p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
            aria-label="Đóng"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab switch */}
        <div className="flex border-b border-slate-100 px-6 pt-3">
          <button
            type="button"
            onClick={() => { setActiveTab('file'); setErrorMessage(null); }}
            className={`pb-3 px-3 text-sm font-semibold border-b-2 flex items-center gap-2 transition-colors cursor-pointer ${
              activeTab === 'file'
                ? 'border-academic-navy text-academic-navy'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <Upload className="w-4 h-4" />
            Tải tệp lên (PDF / DOCX)
          </button>
          <button
            type="button"
            onClick={() => { setActiveTab('arxiv'); setErrorMessage(null); }}
            className={`pb-3 px-3 text-sm font-semibold border-b-2 flex items-center gap-2 transition-colors cursor-pointer ${
              activeTab === 'arxiv'
                ? 'border-academic-navy text-academic-navy'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <LinkIcon className="w-4 h-4" />
            Nạp từ arXiv
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errorMessage && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-sm flex items-start gap-2">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {activeTab === 'file' ? (
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={handleFileChange}
                className="hidden"
              />
              <div
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                  selectedFile
                    ? 'border-academic-navy bg-blue-50/30'
                    : 'border-slate-300 hover:border-academic-navy bg-slate-50/50 hover:bg-slate-50'
                }`}
              >
                {selectedFile ? (
                  <div className="flex flex-col items-center">
                    <FileText className="w-10 h-10 text-academic-navy mb-2" />
                    <span className="text-sm font-medium text-slate-800 break-all">{selectedFile.name}</span>
                    <span className="text-xs text-slate-500 mt-1">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                    </span>
                    <span className="text-xs text-academic-navy font-semibold mt-2 hover:underline">
                      Nhấp để chọn tệp khác
                    </span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center">
                    <Upload className="w-10 h-10 text-slate-400 mb-2" />
                    <p className="text-sm font-medium text-slate-700">Kéo thả tệp vào đây, hoặc bấm để duyệt</p>
                    <p className="text-xs text-slate-500 mt-1">Hỗ trợ tệp PDF có text-layer hoặc tệp Word DOCX (tối đa 50MB)</p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-700">arXiv URL hoặc Paper ID</label>
              <input
                type="text"
                placeholder="Ví dụ: 1706.03762 hoặc https://arxiv.org/abs/1706.03762"
                value={arxivInput}
                onChange={(e) => setArxivInput(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-xl text-sm focus:outline-hidden focus:ring-2 focus:ring-academic-navy focus:border-academic-navy transition-shadow font-mono"
              />
              <p className="text-xs text-slate-500">
                Hệ thống sẽ tự động tải PDF từ kho lưu trữ mở arXiv và bóc tách cấu trúc bằng Indra OCR.
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 pt-2">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Ngôn ngữ gốc</label>
              <select
                disabled
                className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-sm text-slate-700 cursor-not-allowed"
              >
                <option value="en">English (Tiếng Anh)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Ngôn ngữ dịch</label>
              <select
                disabled
                className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-sm text-slate-700 cursor-not-allowed"
              >
                <option value="vi">Tiếng Việt (Vietnamese)</option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={isSubmitting || (activeTab === 'file' && !selectedFile) || (activeTab === 'arxiv' && !arxivInput.trim())}
              className="px-5 py-2 text-sm font-semibold text-white bg-academic-navy hover:bg-academic-navy-dark active:bg-slate-900 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl transition-all shadow-xs flex items-center gap-2 cursor-pointer"
            >
              {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>{isSubmitting ? 'Đang nạp...' : 'Bắt đầu nạp & bóc tách'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
