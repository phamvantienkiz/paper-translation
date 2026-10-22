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
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Download,
  Edit3,
  Columns,
  FileText,
  Languages,
  Loader2,
  RefreshCw,
  Sparkles,
} from 'lucide-react';

interface CanvasPaperViewerProps {
  canvasData: CanvasData;
  sessionId: string;
  onRefresh?: () => void;
  onBlockUpdated?: (updatedBlock: CanvasBlock) => void;
}

/**
 * Thuật toán Binary-Search Font Auto-Scaling:
 * Tìm cỡ chữ lớn nhất trong khoảng [minSize, maxSize] sao cho văn bản
 * sau khi wrap dòng nằm vừa vặn trong Bounding Box [boxWidth, boxHeight].
 */
export function calculateOptimalFontSize(
  text: string,
  boxWidth: number,
  boxHeight: number,
  minSize = 7,
  maxSize = 22
): number {
  if (!text || boxWidth <= 0 || boxHeight <= 0) return minSize;

  // Xấp xỉ số ký tự trên mỗi dòng theo cỡ chữ:
  // Với font học thuật serif, chiều rộng trung bình 1 ký tự ~ 0.52 * fontSize.
  // Chiều cao dòng ~ 1.35 * fontSize.
  let low = minSize;
  let high = maxSize;
  let best = minSize;

  const words = text.split(/\s+/).filter(Boolean);
  if (words.length === 0) return minSize;

  for (let iter = 0; iter < 8; iter++) {
    const mid = (low + high) / 2;
    const charWidth = mid * 0.52;
    const lineHeight = mid * 1.35;
    const maxCharsPerLine = Math.max(1, Math.floor(boxWidth / charWidth));

    // Đếm số dòng cần thiết khi word-wrap
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
      low = mid + 0.5; // Thử cỡ chữ to hơn
    } else {
      high = mid - 0.5; // Quá cao, giảm cỡ chữ
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
  const [currentPageIndex, setCurrentPageIndex] = useState<number>(0);
  const [viewMode, setViewMode] = useState<ViewMode>('TRANSLATED');
  const [zoomLevel, setZoomLevel] = useState<number>(100); // 100 = 100%
  const [activeBlock, setActiveBlock] = useState<CanvasBlock | null>(null);
  const [hoveredBlockId, setHoveredBlockId] = useState<string | null>(null);
  const [isExportingPdf, setIsExportingPdf] = useState<boolean>(false);
  const [isEditingModalOpen, setIsEditingModalOpen] = useState<boolean>(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const originalCanvasRef = useRef<HTMLCanvasElement>(null);

  const totalPages = canvasData.pages.length;
  const currentPage: CanvasPage | undefined = canvasData.pages[currentPageIndex];

  // Base display width at 100% zoom (e.g. 820px for A4 paper)
  const baseWidth = 820;
  const displayWidth = Math.round((baseWidth * zoomLevel) / 100);
  const aspectRatio =
    currentPage && currentPage.width_pt > 0
      ? currentPage.height_pt / currentPage.width_pt
      : 1.414;
  const displayHeight = Math.round(displayWidth * aspectRatio);

  // Keyboard navigation shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (isEditingModalOpen) return;
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      if (e.key === 'ArrowRight' || e.key === 'PageDown') {
        e.preventDefault();
        setCurrentPageIndex((prev) => Math.min(totalPages - 1, prev + 1));
      } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
        e.preventDefault();
        setCurrentPageIndex((prev) => Math.max(0, prev - 1));
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
  }, [totalPages, isEditingModalOpen]);

  /**
   * Kết xuất 3-Layer HTML5 Canvas:
   * Layer 0: Ảnh nền toàn trang gốc (page_image_url)
   * Layer 1: Hộp trắng (#FFFFFF) phủ các vùng translatable
   * Layer 2: Vẽ trực tiếp lên 2D context để chuẩn bị cho export raster
   */
  const renderCanvasLayers = useCallback(
    (canvas: HTMLCanvasElement | null, isOriginalOnly: boolean) => {
      if (!canvas || !currentPage) return;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const dpr = window.devicePixelRatio || 1;
      canvas.width = displayWidth * dpr;
      canvas.height = displayHeight * dpr;
      canvas.style.width = `${displayWidth}px`;
      canvas.style.height = `${displayHeight}px`;

      ctx.save();
      ctx.scale(dpr, dpr);

      // Xóa canvas
      ctx.fillStyle = '#FFFFFF';
      ctx.fillRect(0, 0, displayWidth, displayHeight);

      // Layer 0: Ảnh nền trang gốc
      const baseImg = new Image();
      baseImg.crossOrigin = 'anonymous';
      baseImg.src = currentPage.page_image_url;

      baseImg.onload = () => {
        ctx.drawImage(baseImg, 0, 0, displayWidth, displayHeight);

        // Nếu là chế độ bản gốc thuần túy, dừng lại ở Layer 0
        if (isOriginalOnly) {
          ctx.restore();
          return;
        }

        // Layer 1: Smart Whiteout (#FFFFFF) cho các khối dịch
        currentPage.blocks.forEach((block) => {
          if (block.is_translatable && block.translated_text) {
            const [x0, y0, x1, y1] = block.bbox_norm;
            const bx = x0 * displayWidth;
            const by = y0 * displayHeight;
            const bw = (x1 - x0) * displayWidth;
            const bh = (y1 - y0) * displayHeight;

            // Phủ nền trắng xóa mờ chữ tiếng Anh với viền 1.5px bù trừ
            ctx.fillStyle = '#FFFFFF';
            ctx.fillRect(bx - 1.5, by - 1.5, bw + 3, bh + 3);
          }
        });

        ctx.restore();
      };

      baseImg.onerror = () => {
        // Fallback hiển thị khung trang nếu ảnh chưa tải xong
        ctx.fillStyle = '#F8FAFC';
        ctx.fillRect(0, 0, displayWidth, displayHeight);
        ctx.strokeStyle = '#CBD5E1';
        ctx.strokeRect(0, 0, displayWidth, displayHeight);
        ctx.restore();
      };
    },
    [currentPage, displayWidth, displayHeight]
  );

  // Kích hoạt render lại canvas khi trang, zoom hoặc viewMode thay đổi
  useEffect(() => {
    if (viewMode === 'ORIGINAL') {
      renderCanvasLayers(canvasRef.current, true);
    } else if (viewMode === 'TRANSLATED') {
      renderCanvasLayers(canvasRef.current, false);
    } else if (viewMode === 'SIDE_BY_SIDE') {
      renderCanvasLayers(originalCanvasRef.current, true);
      renderCanvasLayers(canvasRef.current, false);
    }
  }, [currentPageIndex, zoomLevel, viewMode, renderCanvasLayers]);

  // Xử lý lưu chỉnh sửa khối
  const handleSaveBlockEdit = async (blockId: string, newText: string) => {
    const updated = await api.updateBlockTranslation(blockId, newText);

    // Cập nhật lại trong bộ nhớ canvasData
    if (currentPage) {
      const idx = currentPage.blocks.findIndex((b) => b.id === blockId);
      if (idx !== -1) {
        currentPage.blocks[idx] = {
          ...currentPage.blocks[idx],
          translated_text: updated.translated_text,
          is_user_edited: true,
        };
      }
    }

    if (onBlockUpdated) {
      onBlockUpdated(updated);
    }

    // Vẽ lại canvas
    renderCanvasLayers(canvasRef.current, false);
  };

  // Xử lý 1-Click PDF Export
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

  return (
    <div className="flex flex-col h-full bg-slate-100/70 select-none">
      {/* Viewer Control Bar */}
      <div className="h-14 bg-white border-b border-slate-200/90 px-4 md:px-6 flex items-center justify-between shadow-xs z-10">
        {/* Left: View Mode Switcher */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200/80">
          <button
            onClick={() => setViewMode('TRANSLATED')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              viewMode === 'TRANSLATED'
                ? 'bg-academic-navy text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
            title="Tái hiện bản dịch 3 lớp giữ nguyên bố cục gốc"
          >
            <Languages className="w-3.5 h-3.5" />
            <span>Bản dịch (VI)</span>
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

          <button
            onClick={() => setViewMode('SIDE_BY_SIDE')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              viewMode === 'SIDE_BY_SIDE'
                ? 'bg-academic-navy text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
            title="Đối chiếu song song: Gốc bên trái, Bản dịch 3 lớp bên phải"
          >
            <Columns className="w-3.5 h-3.5" />
            <span>Song song (2 bên)</span>
          </button>
        </div>

        {/* Center: Page Navigation */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentPageIndex((prev) => Math.max(0, prev - 1))}
            disabled={currentPageIndex === 0}
            className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed text-slate-700 transition-colors cursor-pointer"
            aria-label="Trang trước"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <div className="flex items-center gap-1.5 text-xs font-medium text-slate-700">
            <span>Trang</span>
            <input
              type="number"
              min={1}
              max={totalPages || 1}
              value={currentPageIndex + 1}
              onChange={(e) => {
                const val = parseInt(e.target.value, 10);
                if (!isNaN(val) && val >= 1 && val <= totalPages) {
                  setCurrentPageIndex(val - 1);
                }
              }}
              className="w-12 text-center py-1 bg-white border border-slate-200 rounded-md font-mono text-xs focus:ring-1 focus:ring-academic-navy outline-hidden"
            />
            <span className="text-slate-400">/ {totalPages || 1}</span>
          </div>

          <button
            onClick={() => setCurrentPageIndex((prev) => Math.min(totalPages - 1, prev + 1))}
            disabled={currentPageIndex >= totalPages - 1}
            className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed text-slate-700 transition-colors cursor-pointer"
            aria-label="Trang kế tiếp"
          >
            <ChevronRight className="w-4 h-4" />
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
            <span>Tải PDF Bản Dịch</span>
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

      {/* Canvas Paper Stage */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto canvas-stage-grid p-6 flex items-start justify-center"
      >
        {!currentPage ? (
          <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center max-w-md shadow-xs">
            <Loader2 className="w-8 h-8 text-academic-navy animate-spin mx-auto mb-3" />
            <h3 className="text-sm font-bold text-slate-800">Đang chuẩn bị trang Canvas...</h3>
            <p className="text-xs text-slate-500 mt-1">
              Hệ thống đang tải ảnh nền Layer 0 và bóc tách tọa độ bố cục.
            </p>
          </div>
        ) : (
          <div
            className={`flex items-start gap-8 transition-all duration-200 ${
              viewMode === 'SIDE_BY_SIDE' ? 'flex-row justify-center max-w-full' : 'justify-center'
            }`}
          >
            {/* Left Sheet: Original Paper (Only shown in SIDE_BY_SIDE mode) */}
            {viewMode === 'SIDE_BY_SIDE' && (
              <div className="flex flex-col items-center">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-slate-400" />
                  Bản gốc tiếng Anh (Page {currentPage.page_number})
                </div>
                <div
                  className="relative bg-white shadow-paper rounded-xs overflow-hidden border border-slate-300"
                  style={{ width: `${displayWidth}px`, height: `${displayHeight}px` }}
                >
                  <canvas ref={originalCanvasRef} className="block w-full h-full" />
                </div>
              </div>
            )}

            {/* Right Sheet: 3-Layer HTML5 Canvas (Translated / Active Page) */}
            <div className="flex flex-col items-center">
              {viewMode === 'SIDE_BY_SIDE' && (
                <div className="text-[11px] font-semibold uppercase tracking-wider text-academic-navy mb-2 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-academic-gold" />
                  Bản dịch tiếng Việt 3 Lớp (Page {currentPage.page_number})
                </div>
              )}

              <div
                className="relative bg-white shadow-paper hover:shadow-paper-hover transition-shadow rounded-xs overflow-hidden border border-slate-300"
                style={{ width: `${displayWidth}px`, height: `${displayHeight}px` }}
              >
                {/* Layer 0 & Layer 1 HTML5 Canvas */}
                <canvas ref={canvasRef} className="block w-full h-full" />

                {/* Layer 2: Interactive SVG & DOM Overlay */}
                {viewMode !== 'ORIGINAL' && (
                  <div className="absolute inset-0 pointer-events-none">
                    {currentPage.blocks.map((block) => {
                      const isTranslatable = block.is_translatable;
                      const hasTranslated = Boolean(block.translated_text);
                      const [x0, y0, x1, y1] = block.bbox_norm;

                      const boxWidthPx = (x1 - x0) * displayWidth;
                      const boxHeightPx = (y1 - y0) * displayHeight;
                      const isHovered = hoveredBlockId === block.id;

                      const displayText = block.translated_text || block.original_text;

                      // Tự động tính cỡ chữ tối ưu bằng Binary Search
                      const optimalFontSize = calculateOptimalFontSize(
                        displayText,
                        boxWidthPx,
                        boxHeightPx,
                        8,
                        block.label === 'title' ? 24 : block.label === 'heading' ? 16 : 12
                      );

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
                          className={`pointer-events-auto transition-all group ${
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
                                  ? 'border border-academic-navy/60 bg-blue-500/5 shadow-xs'
                                  : 'border-transparent'
                              }`}
                            >
                              {isHovered && (
                                <div className="absolute -top-6 right-0 z-20 flex items-center gap-1 bg-academic-navy text-white px-2 py-0.5 rounded text-[10px] font-sans shadow-md animate-in fade-in duration-100">
                                  <Edit3 className="w-2.5 h-2.5" />
                                  <span>Sửa ({block.block_code})</span>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Văn bản tiếng Việt với KaTeX Math */}
                          {hasTranslated && (
                            <div
                              className="w-full h-full overflow-hidden text-slate-900 font-serif leading-snug select-text flex flex-col justify-start"
                              style={{
                                fontSize: `${optimalFontSize}px`,
                                lineHeight: '1.25',
                              }}
                            >
                              <MathRenderer text={displayText} />
                            </div>
                          )}

                          {/* Huy hiệu đánh dấu khối đã sửa thủ công */}
                          {block.is_user_edited && (
                            <div
                              className="absolute bottom-0.5 right-0.5 w-2 h-2 rounded-full bg-emerald-500"
                              title="Khối đã hiệu đính thủ công"
                            />
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Modal chỉnh sửa khối trực tiếp trên Canvas */}
      <BlockEditModal
        block={activeBlock}
        isOpen={isEditingModalOpen}
        onClose={() => {
          setIsEditingModalOpen(false);
          setActiveBlock(null);
        }}
        onSave={handleSaveBlockEdit}
      />
    </div>
  );
};
