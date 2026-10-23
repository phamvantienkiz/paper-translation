import React, { useState } from 'react';
import { EngineStatus } from '../types';
import { api } from '../services/api';
import {
  Cpu,
  Cloud,
  Check,
  AlertTriangle,
  X,
  ShieldCheck,
  Layers,
  HardDrive,
  Loader2,
} from 'lucide-react';

interface EngineStatusModalProps {
  isOpen: boolean;
  onClose: () => void;
  status: EngineStatus | null;
  onUpdated: (newStatus: EngineStatus) => void;
}

export const EngineStatusModal: React.FC<EngineStatusModalProps> = ({
  isOpen,
  onClose,
  status,
  onUpdated,
}) => {
  const [selectedProvider, setSelectedProvider] = useState<string>(
    status?.active_provider || 'llama_cpp'
  );
  const [contextWindow, setContextWindow] = useState<number>(
    status?.context_window || 8192
  );
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen || !status) return null;

  // Tính toán RAM ước lượng hiển thị trực quan
  const estimatedRam =
    selectedProvider === 'llama_cpp'
      ? (1.03 + (contextWindow / 8192) * 1.77).toFixed(1)
      : '0.0';

  const handleApply = async () => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const newStatus = await api.switchEngine(selectedProvider, contextWindow);
      onUpdated(newStatus);
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message || 'Không thể chuyển đổi Engine');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div
        className="bg-white rounded-3xl max-w-xl w-full p-6 shadow-2xl border border-slate-200 relative animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-2xl bg-academic-navy text-white flex items-center justify-center shadow-xs">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Cấu Hình & Quản Lý Động Cơ Dịch Thuật
            </h2>
            <p className="text-xs text-slate-500">
              Lựa chọn chế độ Local-First (bảo mật ngoại tuyến) hoặc Cloud API
            </p>
          </div>
        </div>

        {errorMessage && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-500" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Engine Provider Selection Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
          {/* Option 1: Local LLM (Ưu tiên) */}
          <div
            onClick={() => setSelectedProvider('llama_cpp')}
            className={`p-4 rounded-2xl border-2 transition-all cursor-pointer relative ${
              selectedProvider === 'llama_cpp'
                ? 'border-emerald-600 bg-emerald-50/40 shadow-xs'
                : 'border-slate-200 hover:border-slate-300 bg-white'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <HardDrive
                  className={`w-4 h-4 ${
                    selectedProvider === 'llama_cpp'
                      ? 'text-emerald-700'
                      : 'text-slate-500'
                  }`}
                />
                <span className="text-xs font-bold text-slate-900">
                  Local First (Qwen3)
                </span>
              </div>
              {selectedProvider === 'llama_cpp' && (
                <div className="w-4 h-4 rounded-full bg-emerald-600 text-white flex items-center justify-center">
                  <Check className="w-2.5 h-2.5" />
                </div>
              )}
            </div>
            <div className="text-[11px] text-slate-600 mb-2 font-mono">
              Qwen3-1.7B-Q4_K_M.gguf
            </div>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Chạy ngoại tuyến 100% qua CPU/GPU bằng llama.cpp. Bảo mật tuyệt đối tài liệu nghiên cứu.
            </p>
            <div className="mt-3 flex items-center gap-1.5 text-[10px] text-emerald-800 font-semibold bg-emerald-100/70 px-2 py-0.5 rounded-md inline-flex">
              <ShieldCheck className="w-3 h-3 text-emerald-700" />
              <span>Offline • Không tốn API Key</span>
            </div>
          </div>

          {/* Option 2: Cloud API */}
          <div
            onClick={() => setSelectedProvider('gemini')}
            className={`p-4 rounded-2xl border-2 transition-all cursor-pointer relative ${
              selectedProvider === 'gemini'
                ? 'border-academic-navy bg-blue-50/40 shadow-xs'
                : 'border-slate-200 hover:border-slate-300 bg-white'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Cloud
                  className={`w-4 h-4 ${
                    selectedProvider === 'gemini'
                      ? 'text-academic-navy'
                      : 'text-slate-500'
                  }`}
                />
                <span className="text-xs font-bold text-slate-900">
                  Cloud API (Gemini)
                </span>
              </div>
              {selectedProvider === 'gemini' && (
                <div className="w-4 h-4 rounded-full bg-academic-navy text-white flex items-center justify-center">
                  <Check className="w-2.5 h-2.5" />
                </div>
              )}
            </div>
            <div className="text-[11px] text-slate-600 mb-2 font-mono">
              gemini-3.5-flash-lite
            </div>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Dịch toàn văn trong 1 lần gọi (Single-Call 1M tokens) qua Google Cloud. 0 MB RAM máy tính.
            </p>
            <div className="mt-3 flex items-center gap-1.5 text-[10px] text-blue-800 font-semibold bg-blue-100/70 px-2 py-0.5 rounded-md inline-flex">
              <Cloud className="w-3 h-3 text-academic-navy" />
              <span>Tốc độ cao • Single-Call</span>
            </div>
          </div>
        </div>

        {/* Local LLM Context Window & Hard Ceiling Configuration */}
        {selectedProvider === 'llama_cpp' && (
          <div className="mb-5 p-4 rounded-2xl bg-slate-50 border border-slate-200">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                <span>Kích Thước Ngữ Cảnh (Context Window)</span>
                <span className="text-[10px] text-slate-500 font-normal">
                  (Khóa trần cứng ≤ 4.0 GB RAM)
                </span>
              </label>
              <span className="text-xs font-mono font-bold text-emerald-700 bg-emerald-100/80 px-2 py-0.5 rounded">
                ~{estimatedRam} GB RAM / Max 4.0 GB
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 mt-2">
              <button
                type="button"
                onClick={() => setContextWindow(4096)}
                className={`py-2 px-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-0.5 transition-all cursor-pointer ${
                  contextWindow === 4096
                    ? 'border-emerald-600 bg-white text-emerald-800 shadow-xs'
                    : 'border-slate-200 bg-slate-100 text-slate-600 hover:bg-slate-200/60'
                }`}
              >
                <span>4K Tokens</span>
                <span className="text-[10px] text-slate-400 font-normal">~2.5 GB RAM</span>
              </button>

              <button
                type="button"
                onClick={() => setContextWindow(8192)}
                className={`py-2 px-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-0.5 transition-all cursor-pointer ${
                  contextWindow === 8192
                    ? 'border-emerald-600 bg-white text-emerald-800 shadow-xs'
                    : 'border-slate-200 bg-slate-100 text-slate-600 hover:bg-slate-200/60'
                }`}
              >
                <span className="flex items-center gap-1">
                  8K Tokens
                  <span className="text-[9px] bg-emerald-200 text-emerald-900 px-1 rounded font-bold">Mặc định</span>
                </span>
                <span className="text-[10px] text-slate-400 font-normal">~2.8 GB RAM</span>
              </button>

              <button
                type="button"
                onClick={() => setContextWindow(16384)}
                className={`py-2 px-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-0.5 transition-all cursor-pointer ${
                  contextWindow === 16384
                    ? 'border-emerald-600 bg-white text-emerald-800 shadow-xs'
                    : 'border-slate-200 bg-slate-100 text-slate-600 hover:bg-slate-200/60'
                }`}
              >
                <span className="flex items-center gap-1">
                  16K Tokens
                  <span className="text-[9px] bg-amber-200 text-amber-900 px-1 rounded font-bold">Kịch trần</span>
                </span>
                <span className="text-[10px] text-slate-400 font-normal">~3.8 GB RAM</span>
              </button>
            </div>

            {/* RAM Progress Bar */}
            <div className="mt-3">
              <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-emerald-600 h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${(parseFloat(estimatedRam) / 4.0) * 100}%` }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Sequential Mutex Explanation */}
        <div className="mb-6 p-3.5 rounded-2xl bg-blue-50/70 border border-blue-100 text-xs text-slate-600">
          <div className="flex items-start gap-2">
            <Layers className="w-4 h-4 text-academic-navy shrink-0 mt-0.5" />
            <div className="leading-relaxed">
              <span className="font-bold text-slate-800">
                Điều phối tuần tự an toàn (Sequential Mutex):
              </span>{' '}
              Indra OCR chạy trước để bóc tách bố cục $\rightarrow$ tự động giải phóng 100% RAM $\rightarrow$ nạp mô hình Qwen3 GGUF vào RAM để dịch. Hai mô hình không bao giờ nạp cùng lúc, bảo vệ máy tính khỏi tràn bộ nhớ.
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-2.5">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
          >
            Hủy
          </button>
          <button
            type="button"
            disabled={isSubmitting}
            onClick={handleApply}
            className="px-5 py-2 text-xs font-semibold bg-academic-navy hover:bg-academic-navy-dark text-white rounded-xl shadow-xs transition-all inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            {isSubmitting ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Check className="w-3.5 h-3.5" />
            )}
            <span>Lưu & Áp Dụng</span>
          </button>
        </div>
      </div>
    </div>
  );
};
