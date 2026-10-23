import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  CanvasData,
  CanvasPage,
  CanvasBlock,
  ViewMode,
} from '../types';
import { api } from '../services/api';
import { MathRenderer } from './MathRenderer';
import { BlockEditModal } from './BlockEditModal';
import {
  ChevronUp,
  ChevronDown,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Download,
  Edit3,
  FileText,
  Languages,
  Loader2,
  RefreshCw,
  Sparkles,
  BookOpen,
} from 'lucide-react';

interface CanvasPaperViewerProps {
  canvasData: CanvasData;
  sessionId: string;
  onRefresh?: () => void;
  onBlockUpdated?: (updatedBlock: CanvasBlock) => void;
}

/**
 * Regex nhận diện các khối rác watermark của nhà xuất bản (IEEE, CVPR, arXiv...)
 * để không render lên trang Word bản dịch.
 */
const JUNK_WATERMARK_REGEX =
  /(?:^arxiv:\d{4}\.\d+|ieee\s+transactions|cvpr|iccv|neurips|icml|conference\s+on|authorized\s+licensed\s+use|downloaded\s+on.*utc|copyright\s+©|all\s+rights\s+reserved|^\d+\s*$)/i;

/**
 * Thuật toán tính cỡ chữ cân đối cho các khối văn bản (Paragraph):
 * Giới hạn trong khoảng [9.5px .. 13px] để đảm bảo luôn đọc rõ ràng, không bị co quá nhỏ.
 */
export function calculateOptimalFontSize(
  text: string,
  boxWidth: number,
  boxHeight: number,
  minSize = 9.5,
  maxSize = 13
): number {
  if (!text || boxWidth <= 0 || boxHeight <= 0) return 11;

  let low = minSize;
  let high = maxSize;
  let best = minSize;

  const words = text.split(/\s+/).filter(Boolean);
  if (words.length === 0) return minSize;

  for (let iter = 0; iter < 6; iter++) {
    const mid = (low + high) / 2;
    const charWidth = mid * 0.52;
    const lineHeight = mid * 1.35;
    const maxCharsPerLine = Math.max(1, Math.floor(boxWidth / charWidth));

    let lines = 1;
    let currentLineLength = 0;

    for (const w of words) {
      if (currentLineLength === 0) {
        currentLineLength = w.length;
      } else if (currentLineLength + 1 + w.length <= maxCharsPerLine) {
        currentLineLength += 1 + w.length;
      } else {
        lines++;
        currentLineLength = w.length;
      }
    }

    const totalHeight = lines * lineHeight;

    if (totalHeight <= boxHeight) {
      best = mid;
      low = mid + 0.5;
    } else {
      high = mid - 0.5;
    }
  }

  return Math.max(minSize, Math.min(maxSize, Math.round(best * 10) / 10));
}

export const CanvasPaperViewer: React.FC<CanvasPaperViewerProps> = ({
  canvasData,
  sessionId,
  onRefresh,
  onBlockUpdated,
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>('TRANSLATED');
  const [zoomLevel, setZoomLevel] = useState<number>(100); // 100 = 100%
  const [activePageNumber, setActivePageNumber] = useState<number>(1);
  const [activeBlock, setActiveBlock] = useState<CanvasBlock | null>(null);
  const [hoveredBlockId, setHoveredBlockId] = useState<string | null>(null);
  const [isExportingPdf, setIsExportingPdf] = useState<boolean>(false);
  const [isEditingModalOpen, setIsEditingModalOpen] = useState<boolean>(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  const totalPages = canvasData.pages.length;

  // Chiều rộng cơ sở hiển thị (A4: 820px)
  const baseWidth = 820;
  const displayWidth = Math.round((baseWidth * zoomLevel) / 100);

  // Theo dõi vị trí cuộn để cập nhật trang hiện tại qua IntersectionObserver
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const pageNum = Number(entry.target.getAttribute('data-page-number'));
            if (pageNum) {
              setActivePageNumber(pageNum);
            }
          }
        });
      },
      {
        root: containerRef.current,
        threshold: 0.35,
      }
    );

    pageRefs.current.forEach((el) => {
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [canvasData.pages, zoomLevel, viewMode]);

  // Cuộn mượt đến trang chỉ định
  const scrollToPage = useCallback((pageNum: number) => {
    const target = pageRefs.current.get(pageNum);
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, []);

  // Keyboard navigation shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (isEditingModalOpen) return;
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      if (e.key === 'ArrowDown' || e.key === 'PageDown') {
        if (activePageNumber < totalPages) {
          e.preventDefault();
          scrollToPage(activePageNumber + 1);
        }
      } else if (e.key === 'ArrowUp' || e.key === 'PageUp') {
        if (activePageNumber > 1) {
          e.preventDefault();
          scrollToPage(activePageNumber - 1);
        }
      } else if (e.key === '+' || e.key === '=') {
        e.preventDefault();
        setZoomLevel((prev) => Math.min(200, prev + 15));
      } else if (e.key === '-' || e.key === '_') {
        e.preventDefault();
        setZoomLevel((prev) => Math.max(50, prev - 15));
      } else if (e.key === '0') {
        e.preventDefault();
        setZoomLevel(100);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activePageNumber, totalPages, isEditingModalOpen, scrollToPage]);

  // Xử lý lưu chỉnh sửa khối bản dịch
  const handleSaveBlockEdit = async (blockId: string, newText: string) => {
    const updated = await api.updateBlockTranslation(blockId, newText);

    // Cập nhật lại trong bộ nhớ canvasData
    for (const page of canvasData.pages) {
      const idx = page.blocks.findIndex((b) => b.id === blockId);
      if (idx !== -1) {
        page.blocks[idx] = {
          ...page.blocks[idx],
          translated_text: updated.translated_text,
          is_user_edited: true,
        };
        break;
      }
    }

    if (onBlockUpdated) {
      onBlockUpdated(updated);
    }
  };

  // 1-Click PDF Export
  const handleExportPdf = () => {
    setIsExportingPdf(true);
    const downloadUrl = api.getExportPdfUrl(sessionId);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.target = '_blank';
    link.download = `${canvasData.title || 'translated_paper'}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setTimeout(() => {
      setIsExportingPdf(false);
    }, 1500);
  };

  const handleFitWidth = () => {
    if (containerRef.current) {
      const availWidth = containerRef.current.clientWidth - 80;
      const targetZoom = Math.min(180, Math.max(50, Math.round((availWidth / baseWidth) * 100)));
      setZoomLevel(viewMode === 'SIDE_BY_SIDE' ? Math.round(targetZoom / 2.1) : targetZoom);
    }
  };

  /**
   * Render Khối Nội Dung Trên Trang Word Trắng:
   * - Bỏ qua watermark rác.
   * - Nhúng ảnh gốc crop cho khối figure.
   * - Áp dụng Typography chuẩn phân cấp (Title, Section, Body, Caption).
   */
  const renderCleanWordBlock = (block: CanvasBlock, pWidth: number, pHeight: number) => {
    const [x0, y0, x1, y1] = block.bbox_norm;
    const label = (block.label || '').toLowerCase();
    const rawText = block.translated_text || block.original_text || '';

    // Bỏ qua watermark rác hoặc header/footer phụ
    if (label === 'page header' || label === 'page footer' || JUNK_WATERMARK_REGEX.test(rawText)) {
      return null;
    }

    // 1. Khối HÌNH ẢNH (Figure): Nhúng ảnh gốc đã crop từ PDF, bỏ qua text OCR bên trong
    if (label === 'figure' || block.figure_image_url) {
      return (
        <div
          key={block.id}
          style={{
            position: 'absolute',
            left: `${x0 * 100}%`,
            top: `${y0 * 100}%`,
            width: `${(x1 - x0) * 100}%`,
            height: `${(y1 - y0) * 100}%`,
          }}
          className="flex flex-col items-center justify-center p-1 bg-white border border-slate-200/80 rounded-xs shadow-2xs overflow-hidden"
        >
          {block.figure_image_url ? (
            <img
              src={block.figure_image_url}
              alt={block.block_code}
              className="w-full h-full object-contain"
              loading="lazy"
            />
          ) : (
            <div className="w-full h-full bg-slate-50 border border-dashed border-slate-300 flex items-center justify-center text-slate-400 text-xs">
              [Hình vẽ / Biểu đồ gốc]
            </div>
          )}
        </div>
      );
    }

    const boxWidthPx = (x1 - x0) * pWidth;
    const boxHeightPx = (y1 - y0) * pHeight;
    const isTranslatable = block.is_translatable;
    const isHovered = hoveredBlockId === block.id;

    // 2. Khối TIÊU ĐỀ CHÍNH (Title)
    if (label === 'title') {
      return (
        <div
          key={block.id}
          style={{
            position: 'absolute',
            left: `${x0 * 100}%`,
            top: `${y0 * 100}%`,
            width: `${(x1 - x0) * 100}%`,
            height: `${(y1 - y0) * 100}%`,
          }}
          className="font-serif font-bold text-slate-900 tracking-tight leading-snug flex items-center justify-center text-center cursor-pointer select-text group"
          onClick={() => {
            if (isTranslatable) {
              setActiveBlock(block);
              setIsEditingModalOpen(true);
            }
          }}
        >
          <div className="text-base sm:text-lg md:text-xl font-bold">
            <MathRenderer text={rawText} />
          </div>
        </div>
      );
    }

    // 3. Khối TIÊU ĐỀ MỤC (Section Header)
    if (label === 'section header' || label === 'heading') {
      return (
        <div
          key={block.id}
          style={{
            position: 'absolute',
            left: `${x0 * 100}%`,
            top: `${y0 * 100}%`,
            width: `${(x1 - x0) * 100}%`,
            height: `${(y1 - y0) * 100}%`,
          }}
          className="font-serif font-bold text-slate-900 uppercase tracking-wide leading-tight flex items-start cursor-pointer select-text group"
          onClick={() => {
            if (isTranslatable) {
              setActiveBlock(block);
              setIsEditingModalOpen(true);
            }
          }}
        >
          <div className="text-xs sm:text-sm font-bold text-slate-900 border-b border-slate-200 w-full pb-0.5">
            <MathRenderer text={rawText} />
          </div>
        </div>
      );
    }

    // 4. Khối CHÚ THÍCH HÌNH / BẢNG (Caption)
    if (label === 'caption') {
      return (
        <div
          key={block.id}
          style={{
            position: 'absolute',
            left: `${x0 * 100}%`,
            top: `${y0 * 100}%`,
            width: `${(x1 - x0) * 100}%`,
            height: `${(y1 - y0) * 100}%`,
          }}
          className="font-sans italic text-slate-600 leading-tight text-center flex items-center justify-center cursor-pointer select-text text-[10px] sm:text-[11px]"
          onClick={() => {
            if (isTranslatable) {
              setActiveBlock(block);
              setIsEditingModalOpen(true);
            }
          }}
        >
          <MathRenderer text={rawText} />
        </div>
      );
    }

    // 5. Khối ĐOẠN VĂN HỌC THUẬT (Paragraph / Text)
    const optimalFontSize = calculateOptimalFontSize(rawText, boxWidthPx, boxHeightPx);

    return (
      <div
        key={block.id}
        style={{
          position: 'absolute',
          left: `${x0 * 100}%`,
          top: `${y0 * 100}%`,
          width: `${(x1 - x0) * 100}%`,
          height: `${(y1 - y0) * 100}%`,
        }}
        className={`pointer-events-auto transition-all group overflow-hidden select-text ${
          isTranslatable ? 'cursor-pointer' : ''
        }`}
        onMouseEnter={() => setHoveredBlockId(block.id)}
        onMouseLeave={() => setHoveredBlockId(null)}
        onClick={() => {
          if (isTranslatable) {
            setActiveBlock(block);
            setIsEditingModalOpen(true);
          }
        }}
      >
        {/* Khung viền hover tinh tế & Nút sửa nhanh */}
        {isTranslatable && (
          <div
            className={`absolute -inset-0.5 rounded-xs transition-opacity ${
              isHovered
                ? 'border border-academic-navy/60 bg-blue-500/5 shadow-2xs'
                : 'border-transparent'
            }`}
          >
            {isHovered && (
              <div className="absolute -top-5 right-0 z-20 flex items-center gap-1 bg-academic-navy text-white px-1.5 py-0.5 rounded text-[9px] font-sans shadow-md animate-in fade-in duration-100">
                <Edit3 className="w-2.5 h-2.5" />
                <span>Sửa ({block.block_code})</span>
              </div>
            )}
          </div>
        )}

        <div
          className="w-full h-full text-slate-800 font-serif leading-snug flex flex-col justify-start text-justify"
          style={{
            fontSize: `${optimalFontSize}px`,
            lineHeight: '1.35',
          }}
        >
          <MathRenderer text={rawText} />
        </div>

        {/* Huy hiệu đánh dấu khối đã sửa thủ công */}
        {block.is_user_edited && (
          <div
            className="absolute bottom-0.5 right-0.5 w-2 h-2 rounded-full bg-emerald-500"
            title="Khối đã hiệu đính thủ công"
          />
        )}
      </div>
    );
  };

  /**
   * Render 1 Trang Đơn Lẻ trong chuỗi liên tục
   */
  const renderSinglePage = (page: CanvasPage) => {
    const aspectRatio =
      page.width_pt > 0 ? page.height_pt / page.width_pt : 1.414;
    const pageHeight = Math.round(displayWidth * aspectRatio);

    return (
      <div
        key={page.page_number}
        ref={(el) => {
          if (el) pageRefs.current.set(page.page_number, el);
          else pageRefs.current.delete(page.page_number);
        }}
        data-page-number={page.page_number}
        id={`paper-page-${page.page_number}`}
        className="scroll-mt-20 flex flex-col items-center"
      >
        <div
          className={`flex items-start gap-8 transition-all duration-200 ${
            viewMode === 'SIDE_BY_SIDE' ? 'flex-row justify-center max-w-full' : 'justify-center'
          }`}
        >
          {/* Cột Trái: Ảnh Scan Trang Gốc (Chỉ hiển thị ở chế độ SIDE_BY_SIDE) */}
          {viewMode === 'SIDE_BY_SIDE' && (
            <div className="flex flex-col items-center">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-slate-400" />
                Bản gốc tiếng Anh (Trang {page.page_number})
              </div>
              <div
                className="relative bg-white shadow-paper rounded-xs overflow-hidden border border-slate-300"
                style={{ width: `${displayWidth}px`, height: `${pageHeight}px` }}
              >
                <img
                  src={page.page_image_url}
                  alt={`Bản gốc trang ${page.page_number}`}
                  className="w-full h-full object-contain block"
                  loading="lazy"
                />
              </div>
            </div>
          )}

          {/* Cột Phải hoặc Chế độ Chính */}
          <div className="flex flex-col items-center">
            {viewMode === 'SIDE_BY_SIDE' && (
              <div className="text-[11px] font-semibold uppercase tracking-wider text-academic-navy mb-2 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-academic-gold" />
                Bản dịch tiếng Việt (Trang {page.page_number})
              </div>
            )}

            {/* Chế độ ORIGINAL: Chỉ hiển thị ảnh scan gốc */}
            {viewMode === 'ORIGINAL' ? (
              <div
                className="relative bg-white shadow-paper rounded-xs overflow-hidden border border-slate-300"
                style={{ width: `${displayWidth}px`, height: `${pageHeight}px` }}
              >
                <img
                  src={page.page_image_url}
                  alt={`Bản gốc trang ${page.page_number}`}
                  className="w-full h-full object-contain block"
                  loading="lazy"
                />
              </div>
            ) : (
              /* Chế độ TRANSLATED / SIDE_BY_SIDE: Trang Word Trắng Sạch Tinh Tế */
              <div
                className="relative bg-white shadow-paper hover:shadow-paper-hover transition-shadow rounded-xs border border-slate-300 overflow-hidden"
                style={{ width: `${displayWidth}px`, height: `${pageHeight}px` }}
              >
                {/* Header trang học thuật nhẹ nhàng */}
                <div className="absolute top-3 left-8 right-8 flex justify-between items-center text-[10px] text-slate-400 font-serif border-b border-slate-100 pb-1 select-none pointer-events-none">
                  <span className="truncate max-w-sm">{canvasData.title || 'Paper Translation'}</span>
                  <span>Bản dịch Tiếng Việt</span>
                </div>

                {/* Các khối nội dung tái tạo sạch */}
                <div className="absolute inset-0 pt-7 pb-8 px-6">
                  {page.blocks.map((b) => renderCleanWordBlock(b, displayWidth, pageHeight))}
                </div>

                {/* Số trang căn giữa chân trang */}
                <div className="absolute bottom-2.5 inset-x-0 text-center text-[10px] text-slate-400 font-serif select-none pointer-events-none">
                  — {page.page_number} —
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full bg-slate-100/70 select-none relative">
      {/* Viewer Control Bar (Cố định ở đỉnh - Sticky Chrome) */}
      <div className="sticky top-0 h-14 bg-white/95 backdrop-blur border-b border-slate-200/90 px-4 md:px-6 flex items-center justify-between shadow-xs z-20">
        {/* Left: View Mode Switcher */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200/80">
          <button
            onClick={() => setViewMode('TRANSLATED')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              viewMode === 'TRANSLATED'
                ? 'bg-academic-navy text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
            title="Tái hiện bản dịch trên trang Word trắng sạch, không lem chữ"
          >
            <Languages className="w-3.5 h-3.5" />
            <span>Bản dịch (Word)</span>
          </button>

          <button
            onClick={() => setViewMode('SIDE_BY_SIDE')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              viewMode === 'SIDE_BY_SIDE'
                ? 'bg-academic-navy text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
            title="Đối chiếu song song: Gốc bên trái, Bản dịch Word bên phải"
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>Song song</span>
          </button>

          <button
            onClick={() => setViewMode('ORIGINAL')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              viewMode === 'ORIGINAL'
                ? 'bg-academic-navy text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
            title="Xem ảnh trang bài báo gốc tiếng Anh"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Bản gốc (EN)</span>
          </button>
        </div>

        {/* Center: Floating Page Indicator with Jump Controls */}
        <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-3 py-1 rounded-xl text-xs font-semibold text-slate-700 shadow-2xs">
          <button
            onClick={() => scrollToPage(Math.max(1, activePageNumber - 1))}
            disabled={activePageNumber <= 1}
            className="p-1 rounded hover:bg-slate-200 text-slate-500 hover:text-slate-800 disabled:opacity-30 cursor-pointer"
            title="Trang trước"
          >
            <ChevronUp className="w-3.5 h-3.5" />
          </button>
          <span className="font-mono text-academic-navy font-bold min-w-16 text-center">
            Trang {activePageNumber} / {totalPages}
          </span>
          <button
            onClick={() => scrollToPage(Math.min(totalPages, activePageNumber + 1))}
            disabled={activePageNumber >= totalPages}
            className="p-1 rounded hover:bg-slate-200 text-slate-500 hover:text-slate-800 disabled:opacity-30 cursor-pointer"
            title="Trang sau"
          >
            <ChevronDown className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Right: Zoom & Export Actions */}
        <div className="flex items-center gap-2">
          {/* Zoom controls */}
          <div className="flex items-center gap-1 bg-slate-50 border border-slate-200 rounded-xl p-0.5 text-slate-700">
            <button
              onClick={() => setZoomLevel((prev) => Math.max(50, prev - 15))}
              className="p-1.5 rounded-lg hover:bg-slate-200/60 transition-colors cursor-pointer"
              title="Thu nhỏ (-)"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="px-1.5 font-mono text-xs font-semibold min-w-11 text-center">
              {zoomLevel}%
            </span>
            <button
              onClick={() => setZoomLevel((prev) => Math.min(200, prev + 15))}
              className="p-1.5 rounded-lg hover:bg-slate-200/60 transition-colors cursor-pointer"
              title="Phóng to (+)"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleFitWidth}
              className="p-1.5 rounded-lg hover:bg-slate-200/60 transition-colors text-slate-500 hover:text-slate-900 cursor-pointer"
              title="Vừa chiều rộng (0)"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* 1-Click PDF Export Button */}
          <button
            onClick={handleExportPdf}
            disabled={isExportingPdf}
            className="px-3.5 py-2 bg-academic-navy hover:bg-academic-navy-dark active:bg-slate-900 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer disabled:opacity-50"
            title="Tải về tệp PDF bản dịch giữ nguyên bố cục"
          >
            {isExportingPdf ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Download className="w-3.5 h-3.5" />
            )}
            <span>Tải PDF</span>
          </button>

          {onRefresh && (
            <button
              onClick={onRefresh}
              className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
              title="Làm mới dữ liệu trang"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Continuous Vertical Scroll Document Stage (Cuộn Dọc Mượt Mà Như Landing Page) */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto canvas-stage-grid p-6 scroll-smooth"
      >
        {totalPages === 0 ? (
          <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center max-w-md shadow-xs mx-auto my-12">
            <Loader2 className="w-8 h-8 text-academic-navy animate-spin mx-auto mb-3" />
            <h3 className="text-sm font-bold text-slate-800">Đang chuẩn bị trang Canvas...</h3>
            <p className="text-xs text-slate-500 mt-1">
              Hệ thống đang tải bố cục tài liệu và ảnh minh họa.
            </p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-10 py-4 w-full">
            {canvasData.pages.map((page) => renderSinglePage(page))}
          </div>
        )}
      </div>

      {/* Modal Chỉnh Sửa Trực Tiếp Khối Văn Bản */}
      {isEditingModalOpen && activeBlock && (
        <BlockEditModal
          block={activeBlock}
          isOpen={isEditingModalOpen}
          onClose={() => {
            setIsEditingModalOpen(false);
            setActiveBlock(null);
          }}
          onSave={handleSaveBlockEdit}
        />
      )}
    </div>
  );
};
