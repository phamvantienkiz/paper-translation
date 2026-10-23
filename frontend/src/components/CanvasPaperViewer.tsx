import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
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
 * để không render lên trang đọc 1 cột bản dịch.
 */
const JUNK_WATERMARK_REGEX =
  /(?:^arxiv:\d{4}\.\d+|ieee\s+transactions|cvpr|iccv|neurips|icml|conference\s+on|authorized\s+licensed\s+use|downloaded\s+on.*utc|copyright\s+©|all\s+rights\s+reserved|^\d+\s*$)/i;

/**
 * Regex nhận diện khối chú thích Hình (Figure / Fig. / Hình N)
 */
const FIGURE_CAPTION_REGEX = /(?:^|\n)\s*(?:figure|fig\.|hình)\s*\d+\b/i;

/**
 * Regex nhận diện khối chú thích Bảng (Table / Bảng N)
 */
const TABLE_CAPTION_REGEX = /^\s*(?:table|bảng)\s*\d+\b/i;

/**
 * Cấu trúc một phần tử hiển thị trong luồng 1 cột tự giãn chiều dọc (Flowing Single-Column Reader)
 */
type FlowItem =
  | {
      type: 'prose';
      key: string;
      block: CanvasBlock;
      displayText: string;
      variant:
        | 'paper_title'
        | 'author_meta'
        | 'section_header'
        | 'equation'
        | 'references'
        | 'body';
    }
  | {
      type: 'figure';
      key: string;
      cropBbox: [number, number, number, number];
      captionBlock: CanvasBlock;
      captionText: string;
    }
  | {
      type: 'table';
      key: string;
      cropBbox: [number, number, number, number];
      captionBlocks: CanvasBlock[];
      captionText: string;
      tableBlock: CanvasBlock;
    };

/**
 * Kiểm tra một chuỗi văn bản có phải là phương trình toán học độc lập (display equation)
 */
function isStandaloneEquation(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed) return false;
  if (/^\(\d+\)$/.test(trimmed)) return true;
  if (!trimmed.includes('$') && !trimmed.includes('\\')) return false;
  const withoutMath = trimmed
    .replace(/\$\$[\s\S]*?\$\$/g, '')
    .replace(/\$[^$]*\$/g, '')
    .replace(/\\[a-zA-Z]+/g, '')
    .replace(/\(\d+\)/g, '')
    .replace(/[^a-zA-ZÀ-ỹ]/g, '');
  return withoutMath.length < 8;
}

/**
 * Làm sạch tiền tố nhãn con (sub-labels như "Input\nRetinexFormer [3]\n") bị gộp nhầm vào trước "Hình N." / "Figure N."
 */
function cleanFigureCaptionText(text: string): string {
  const match = text.match(/(?:^|\n)\s*((?:Figure|Fig\.|Hình)\s*\d+[\s\S]*)/i);
  if (match && match[1]) {
    return match[1].trim();
  }
  return text.trim();
}

/**
 * Chuyển đổi danh sách các khối OCR của một trang thành luồng đọc 1 cột chuẩn học thuật:
 * - Tự động ghép và cắt vùng Hình vẽ (Figure 1..N, bao gồm cả lưới nhiều ảnh con và sơ đồ vector) từ ảnh gốc 200 DPI.
 * - Tự động ghép Chú thích Bảng (Table 1..N) với vùng ảnh Bảng số liệu chuẩn xác từ trang gốc.
 * - Sắp xếp văn bản theo đúng thứ tự đọc (Tiêu đề đầu trang -> Cột Trái từ trên xuống dưới -> Cột Phải từ trên xuống dưới).
 * - Loại bỏ triệt để hiện tượng đè chữ, cắt chữ khi văn bản tiếng Việt dài hơn tiếng Anh.
 */
function buildFlowItemsForPage(page: CanvasPage): FlowItem[] {
  const rawBlocks = page.blocks || [];
  const consumedIds = new Set<string>();

  // 1. Đánh dấu bỏ qua các khối header/footer, watermark rác, hoặc ký hiệu đánh số phương trình rời rạc "(1)".."(9)"
  for (const b of rawBlocks) {
    const label = (b.label || '').toLowerCase();
    const orig = (b.original_text || '').trim();
    if (label === 'page header' || label === 'page footer') {
      consumedIds.add(b.id);
      continue;
    }
    if (orig.length < 250 && JUNK_WATERMARK_REGEX.test(orig)) {
      consumedIds.add(b.id);
      continue;
    }
    if (/^\(\d+\)$/.test(orig)) {
      consumedIds.add(b.id);
      continue;
    }
  }

  // 2. Nhận diện tất cả các khối Table số liệu thực sự và ghép với Caption Bảng đứng ngay trước nó
  const tableGroups = new Map<
    string,
    {
      captionBlocks: CanvasBlock[];
      tableBlock: CanvasBlock;
      cropBbox: [number, number, number, number];
      anchorY: number;
      colGroup: 'full' | 'left' | 'right';
    }
  >();

  // Tìm các khối bắt đầu bằng "Table N." / "Bảng N."
  for (let i = 0; i < rawBlocks.length; i++) {
    const b = rawBlocks[i];
    if (consumedIds.has(b.id)) continue;
    const orig = (b.original_text || '').trim();
    const trans = (b.translated_text || '').trim();

    if (TABLE_CAPTION_REGEX.test(orig) || TABLE_CAPTION_REGEX.test(trans)) {
      const capBlocks: CanvasBlock[] = [b];
      consumedIds.add(b.id);

      let foundTableBlock: CanvasBlock | null = null;
      let extraHeaderBlock: CanvasBlock | null = null;

      // Duyệt các khối kế tiếp cùng cột để gom các dòng caption bị tách (như Table 3, Table 6, Table 7) và tìm khối [table]
      const bCenterX = (b.bbox_norm[0] + b.bbox_norm[2]) / 2;
      const bWidth = b.bbox_norm[2] - b.bbox_norm[0];

      for (let j = i + 1; j < Math.min(rawBlocks.length, i + 6); j++) {
        const cand = rawBlocks[j];
        if (consumedIds.has(cand.id)) continue;
        const candLabel = (cand.label || '').toLowerCase();
        const candOrig = (cand.original_text || '').trim();
        const candTrans = (cand.translated_text || '').trim();

        // Dừng nếu gặp Table/Figure mới hoặc Section Header
        if (
          TABLE_CAPTION_REGEX.test(candOrig) ||
          TABLE_CAPTION_REGEX.test(candTrans) ||
          FIGURE_CAPTION_REGEX.test(candOrig) ||
          FIGURE_CAPTION_REGEX.test(candTrans) ||
          candLabel === 'section header'
        ) {
          break;
        }

        // Kiểm tra cùng vùng cột
        const candCenterX = (cand.bbox_norm[0] + cand.bbox_norm[2]) / 2;
        const sameColumn =
          bWidth > 0.5 ||
          (bCenterX < 0.5 && candCenterX < 0.5) ||
          (bCenterX >= 0.5 && candCenterX >= 0.5);
        if (!sameColumn) continue;

        if (candLabel === 'table') {
          foundTableBlock = cand;
          consumedIds.add(cand.id);
          break;
        }

        // Nếu là dòng header của bảng bị tách thành caption (ví dụ BLK_0157: "Params↓ (M) MACs↓ (G)...")
        if (
          candLabel === 'caption' &&
          /(?:params|macs|psnr|ssim|lpips)/i.test(candOrig)
        ) {
          extraHeaderBlock = cand;
          consumedIds.add(cand.id);
          continue;
        }

        // Nếu là dòng tiếp nối của Table caption ngay sát bên dưới
        const prevCap = capBlocks[capBlocks.length - 1];
        if (
          candLabel === 'caption' &&
          cand.bbox_norm[1] - prevCap.bbox_norm[3] < 0.035
        ) {
          capBlocks.push(cand);
          consumedIds.add(cand.id);
        } else {
          break;
        }
      }

      if (foundTableBlock) {
        const tx0 = Math.max(
          0.07,
          Math.min(
            foundTableBlock.bbox_norm[0],
            extraHeaderBlock ? extraHeaderBlock.bbox_norm[0] : 1
          ) - 0.012
        );
        const ty0 = Math.max(
          0.05,
          Math.min(
            foundTableBlock.bbox_norm[1],
            extraHeaderBlock ? extraHeaderBlock.bbox_norm[1] : 1
          ) - 0.008
        );
        const tx1 = Math.min(
          0.93,
          Math.max(
            foundTableBlock.bbox_norm[2],
            extraHeaderBlock ? extraHeaderBlock.bbox_norm[2] : 0
          ) + 0.012
        );
        const ty1 = Math.min(0.95, foundTableBlock.bbox_norm[3] + 0.008);

        const tableWidth = tx1 - tx0;
        const tableCenterX = (tx0 + tx1) / 2;
        const colGroup: 'full' | 'left' | 'right' =
          tableWidth > 0.55 ? 'full' : tableCenterX < 0.5 ? 'left' : 'right';

        tableGroups.set(b.id, {
          captionBlocks: capBlocks,
          tableBlock: foundTableBlock,
          cropBbox: [tx0, ty0, tx1, ty1],
          anchorY: b.bbox_norm[1],
          colGroup,
        });
      } else {
        // Nếu không tìm thấy khối table đi kèm, trả lại để hiển thị như khối văn bản thường
        for (const cb of capBlocks) {
          consumedIds.delete(cb.id);
        }
      }
    }
  }

  // Tập hợp các khối thuộc về Table thực sự (để hỗ trợ tính ranh giới trên của Figure)
  const realTableRelatedIds = new Set<string>();
  tableGroups.forEach((grp) => {
    grp.captionBlocks.forEach((cb) => realTableRelatedIds.add(cb.id));
    realTableRelatedIds.add(grp.tableBlock.id);
  });

  // 3. Nhận diện tất cả các khối Chú thích Hình (Figure 1..N) và tính toán vùng cắt ảnh gốc [x0, y_top, x1, y_bottom]
  const figureGroups = new Map<
    string,
    {
      captionBlock: CanvasBlock;
      cropBbox: [number, number, number, number];
      anchorY: number;
      colGroup: 'full' | 'left' | 'right';
    }
  >();

  const figCapBlocks = rawBlocks
    .filter((b) => {
      if (consumedIds.has(b.id)) return false;
      const orig = (b.original_text || '').trim();
      const trans = (b.translated_text || '').trim();
      return FIGURE_CAPTION_REGEX.test(orig) || FIGURE_CAPTION_REGEX.test(trans);
    })
    .sort((a, b) => a.bbox_norm[1] - b.bbox_norm[1]);

  for (const capBlock of figCapBlocks) {
    const orig = (capBlock.original_text || '').trim();
    // Nếu caption bị gộp dòng sub-label phía trên (như BLK_0126 trang 7: "Input\nRetinexFormer [3]\nFigure 6..."),
    // đẩy đáy vùng ảnh xuống một chút để bao trọn dòng nhãn con trên ảnh nhưng không cắt vào chữ "Figure 6."
    const hasMergedSublabelPrefix =
      !/^\s*(?:figure|fig\.|hình)\s*\d+/i.test(orig) &&
      FIGURE_CAPTION_REGEX.test(orig);

    const yBottom = hasMergedSublabelPrefix
      ? Math.min(capBlock.bbox_norm[3], capBlock.bbox_norm[1] + 0.012)
      : Math.max(0.08, capBlock.bbox_norm[1] - 0.004);

    // Tìm ranh giới trên (yTop) của vùng hình vẽ: là đáy (y1) cao nhất của khối văn bản chính / tiêu đề / bảng / hình trước đó nằm phía trên capBlock
    let yTop = 0.082;
    for (const other of rawBlocks) {
      if (other.id === capBlock.id) continue;
      const otherLabel = (other.label || '').toLowerCase();
      if (otherLabel === 'page header' || otherLabel === 'page footer') continue;

      const otherY1 = other.bbox_norm[3];
      if (otherY1 > capBlock.bbox_norm[1] - 0.015) continue;

      const otherOrig = (other.original_text || '').trim();
      const isPreviousFigCap = FIGURE_CAPTION_REGEX.test(otherOrig);
      const isRealTablePart = realTableRelatedIds.has(other.id);
      const isHeaderOrTitle =
        otherLabel === 'title' ||
        otherLabel === 'section header' ||
        (page.page_number === 1 && other.bbox_norm[1] < 0.26);
      const isLongProse =
        otherLabel === 'text' && otherOrig.length > 140 && !isPreviousFigCap;

      if (
        isPreviousFigCap ||
        isRealTablePart ||
        isHeaderOrTitle ||
        isLongProse
      ) {
        if (otherY1 + 0.008 > yTop) {
          yTop = otherY1 + 0.008;
        }
      }
    }

    if (yBottom - yTop >= 0.06) {
      const fx0 = 0.085;
      const fx1 = 0.915;
      const capWidth = capBlock.bbox_norm[2] - capBlock.bbox_norm[0];
      const capCenterX = (capBlock.bbox_norm[0] + capBlock.bbox_norm[2]) / 2;
      const colGroup: 'full' | 'left' | 'right' =
        capWidth > 0.45 ? 'full' : capCenterX < 0.5 ? 'left' : 'right';

      figureGroups.set(capBlock.id, {
        captionBlock: capBlock,
        cropBbox: [fx0, yTop, fx1, yBottom],
        anchorY: yTop,
        colGroup,
      });
      consumedIds.add(capBlock.id);

      // Mọi khối figure hoặc nhãn con OCR nằm bên trong vùng [yTop, yBottom + 0.015] đã có mặt trong ảnh crop nên đánh dấu đã tiêu thụ
      for (const inner of rawBlocks) {
        if (consumedIds.has(inner.id) || realTableRelatedIds.has(inner.id)) {
          continue;
        }
        const midY = (inner.bbox_norm[1] + inner.bbox_norm[3]) / 2;
        if (midY >= yTop - 0.01 && midY <= yBottom + 0.015) {
          consumedIds.add(inner.id);
        }
      }
    }
  }

  // 4. Gom tất cả các phần tử (Figure, Table, và các khối văn bản còn lại) kèm thông tin phân nhóm cột để sắp xếp đúng luồng đọc 1 cột
  interface SortableEntry {
    colGroup: 'full_top' | 'left' | 'right' | 'full_bottom';
    sortY: number;
    item: FlowItem;
  }

  const entries: SortableEntry[] = [];

  // Thêm các nhóm Figure
  figureGroups.forEach((fg) => {
    const rawCaption =
      (fg.captionBlock.translated_text || '').trim() ||
      (fg.captionBlock.original_text || '').trim();
    const cleanedCaption = cleanFigureCaptionText(rawCaption);

    const colGroup =
      fg.colGroup === 'full'
        ? fg.anchorY < 0.65
          ? 'full_top'
          : 'full_bottom'
        : fg.colGroup;

    entries.push({
      colGroup,
      sortY: fg.anchorY,
      item: {
        type: 'figure',
        key: `fig-${fg.captionBlock.id}`,
        cropBbox: fg.cropBbox,
        captionBlock: fg.captionBlock,
        captionText: cleanedCaption,
      },
    });
  });

  // Thêm các nhóm Table
  tableGroups.forEach((tg) => {
    const captionText = tg.captionBlocks
      .map((cb) => (cb.translated_text || '').trim() || (cb.original_text || '').trim())
      .filter(Boolean)
      .join(' ');

    const colGroup =
      tg.colGroup === 'full'
        ? tg.anchorY < 0.65
          ? 'full_top'
          : 'full_bottom'
        : tg.colGroup;

    entries.push({
      colGroup,
      sortY: tg.anchorY,
      item: {
        type: 'table',
        key: `tbl-${tg.tableBlock.id}`,
        cropBbox: tg.cropBbox,
        captionBlocks: tg.captionBlocks,
        captionText,
        tableBlock: tg.tableBlock,
      },
    });
  });

  // Thêm các khối văn bản (prose) chưa bị tiêu thụ
  for (const b of rawBlocks) {
    if (consumedIds.has(b.id)) continue;
    const label = (b.label || '').toLowerCase();
    if (label === 'figure' || label === 'figure_text') continue;

    const orig = (b.original_text || '').trim();
    const trans = (b.translated_text || '').trim();
    const displayText = trans || orig;
    if (!displayText) continue;

    const [x0, y0, x1] = b.bbox_norm;
    const width = x1 - x0;
    const centerX = (x0 + x1) / 2;

    // Phân loại ngữ nghĩa hiển thị
    const isPaperTitle =
      label === 'title' || (page.page_number === 1 && b.block_code === 'BLK_0002');
    const isAuthorMeta =
      page.page_number === 1 && !isPaperTitle && y0 < 0.265;
    const isReferences =
      !b.is_translatable &&
      (page.page_number >= 9 || /^references\b/i.test(orig) || /^\[\d+\]/.test(orig));
    const isEq = isStandaloneEquation(orig);
    const isSecHeader =
      !isPaperTitle &&
      !isAuthorMeta &&
      !isEq &&
      (label === 'section header' || label === 'heading');

    let variant:
      | 'paper_title'
      | 'author_meta'
      | 'section_header'
      | 'equation'
      | 'references'
      | 'body' = 'body';

    if (isPaperTitle) variant = 'paper_title';
    else if (isAuthorMeta) variant = 'author_meta';
    else if (isSecHeader) variant = 'section_header';
    else if (isEq) variant = 'equation';
    else if (isReferences) variant = 'references';

    let colGroup: 'full_top' | 'left' | 'right' | 'full_bottom' = 'left';
    if (isPaperTitle || isAuthorMeta || (width > 0.55 && y0 < 0.65)) {
      colGroup = 'full_top';
    } else if (width > 0.55) {
      colGroup = 'full_bottom';
    } else if (centerX < 0.5) {
      colGroup = 'left';
    } else {
      colGroup = 'right';
    }

    entries.push({
      colGroup,
      sortY: y0,
      item: {
        type: 'prose',
        key: b.id,
        block: b,
        displayText,
        variant,
      },
    });
  }

  // Sắp xếp theo thứ tự: Khối tràn ngang đầu trang (full_top) -> Cột Trái (left) -> Cột Phải (right) -> Khối tràn ngang cuối trang (full_bottom)
  const groupPriority: Record<SortableEntry['colGroup'], number> = {
    full_top: 1,
    left: 2,
    right: 3,
    full_bottom: 4,
  };

  entries.sort((a, b) => {
    const pDiff = groupPriority[a.colGroup] - groupPriority[b.colGroup];
    if (pDiff !== 0) return pDiff;
    return a.sortY - b.sortY;
  });

  return entries.map((e) => e.item);
}

/**
 * Component cắt một vùng hình chữ nhật [x0, y0, x1, y1] chuẩn xác từ ảnh trang gốc 200 DPI
 * bằng SVG viewBox — giữ nguyên 100% độ nét của sơ đồ vector, lưới nhiều ảnh con và bảng số liệu.
 */
const CroppedPageRegion: React.FC<{
  pageImageUrl: string;
  pageWidthPt: number;
  pageHeightPt: number;
  cropBbox: [number, number, number, number];
  altText: string;
}> = ({ pageImageUrl, pageWidthPt, pageHeightPt, cropBbox, altText }) => {
  const W = pageWidthPt > 0 ? pageWidthPt : 612;
  const H = pageHeightPt > 0 ? pageHeightPt : 792;
  const [x0, y0, x1, y1] = cropBbox;
  const vx = Math.max(0, x0 * W);
  const vy = Math.max(0, y0 * H);
  const vw = Math.max(10, (x1 - x0) * W);
  const vh = Math.max(10, (y1 - y0) * H);

  return (
    <div className="w-full overflow-hidden rounded-lg border border-slate-200/90 bg-white shadow-2xs">
      <svg
        viewBox={`${vx} ${vy} ${vw} ${vh}`}
        className="w-full h-auto block mx-auto"
        role="img"
        aria-label={altText}
      >
        <image
          href={pageImageUrl}
          x={0}
          y={0}
          width={W}
          height={H}
          preserveAspectRatio="none"
        />
      </svg>
    </div>
  );
};

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
  const [layoutVersion, setLayoutVersion] = useState<number>(0);

  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  const totalPages = canvasData.pages.length;

  // Chiều rộng cơ sở hiển thị (820px ở mức zoom 100%)
  const baseWidth = 820;
  const displayWidth = Math.round((baseWidth * zoomLevel) / 100);
  const zoomScale = displayWidth / baseWidth;

  // Tính toán trước danh sách phần tử luồng 1 cột cho tất cả các trang
  const flowItemsByPage = useMemo(() => {
    const map = new Map<number, FlowItem[]>();
    for (const page of canvasData.pages) {
      map.set(page.page_number, buildFlowItemsForPage(page));
    }
    return map;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canvasData.pages, layoutVersion]);

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
        threshold: 0.2,
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

    setLayoutVersion((v) => v + 1);

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
   * Mở modal chỉnh sửa một khối văn bản hoặc chú thích
   */
  const openEditModal = (block: CanvasBlock) => {
    setActiveBlock(block);
    setIsEditingModalOpen(true);
  };

  /**
   * Render một phần tử trong trang đọc 1 cột tự giãn chiều dọc (Flowing Single-Column Reader)
   */
  const renderFlowItem = (item: FlowItem, page: CanvasPage) => {
    if (item.type === 'figure') {
      const isHovered = hoveredBlockId === item.captionBlock.id;
      return (
        <figure
          key={item.key}
          className="my-5 p-3.5 rounded-xl bg-slate-50/70 border border-slate-200/80 flex flex-col gap-3"
        >
          <CroppedPageRegion
            pageImageUrl={page.page_image_url}
            pageWidthPt={page.width_pt}
            pageHeightPt={page.height_pt}
            cropBbox={item.cropBbox}
            altText={`Hình minh họa trang ${page.page_number}`}
          />

          <figcaption
            className={`relative rounded-lg px-2.5 py-1.5 font-serif text-slate-700 text-justify cursor-pointer transition-colors select-text ${
              isHovered ? 'bg-blue-50/70 ring-1 ring-academic-navy/40' : 'hover:bg-slate-100/80'
            }`}
            style={{
              fontSize: `${Math.round(13.5 * zoomScale * 10) / 10}px`,
              lineHeight: 1.6,
            }}
            onMouseEnter={() => setHoveredBlockId(item.captionBlock.id)}
            onMouseLeave={() => setHoveredBlockId(null)}
            onClick={() => openEditModal(item.captionBlock)}
          >
            {isHovered && (
              <span className="absolute -top-4 right-2 flex items-center gap-1 bg-academic-navy text-white px-2 py-0.5 rounded text-[10px] font-sans shadow-sm z-10">
                <Edit3 className="w-2.5 h-2.5" />
                <span>Sửa chú thích ({item.captionBlock.block_code})</span>
              </span>
            )}
            <MathRenderer text={item.captionText} />
          </figcaption>
        </figure>
      );
    }

    if (item.type === 'table') {
      const primaryCapBlock = item.captionBlocks[0] || item.tableBlock;
      const isHovered = hoveredBlockId === primaryCapBlock.id;
      return (
        <div
          key={item.key}
          className="my-5 p-3.5 rounded-xl bg-slate-50/70 border border-slate-200/80 flex flex-col gap-2.5"
        >
          {/* Chú thích Bảng ở phía trên bảng theo chuẩn bài báo khoa học */}
          {item.captionText && (
            <div
              className={`relative rounded-lg px-2.5 py-1.5 font-serif text-slate-800 font-medium text-justify cursor-pointer transition-colors select-text ${
                isHovered ? 'bg-blue-50/70 ring-1 ring-academic-navy/40' : 'hover:bg-slate-100/80'
              }`}
              style={{
                fontSize: `${Math.round(13.5 * zoomScale * 10) / 10}px`,
                lineHeight: 1.55,
              }}
              onMouseEnter={() => setHoveredBlockId(primaryCapBlock.id)}
              onMouseLeave={() => setHoveredBlockId(null)}
              onClick={() => openEditModal(primaryCapBlock)}
            >
              {isHovered && (
                <span className="absolute -top-4 right-2 flex items-center gap-1 bg-academic-navy text-white px-2 py-0.5 rounded text-[10px] font-sans shadow-sm z-10">
                  <Edit3 className="w-2.5 h-2.5" />
                  <span>Sửa tiêu đề bảng ({primaryCapBlock.block_code})</span>
                </span>
              )}
              <MathRenderer text={item.captionText} />
            </div>
          )}

          {/* Ảnh cắt Bảng số liệu sắc nét từ trang gốc */}
          <CroppedPageRegion
            pageImageUrl={page.page_image_url}
            pageWidthPt={page.width_pt}
            pageHeightPt={page.height_pt}
            cropBbox={item.cropBbox}
            altText={`Bảng số liệu trang ${page.page_number}`}
          />
        </div>
      );
    }

    // Khối văn bản học thuật (Prose: Title, Author Meta, Section Header, Body, Equation, References)
    const { block, displayText, variant } = item;
    const isHovered = hoveredBlockId === block.id;

    let fontSizePx = 15.0 * zoomScale;
    let lineHeight = 1.68;
    let blockClass = 'text-slate-800 text-justify my-2.5';

    if (variant === 'paper_title') {
      fontSizePx = 22.0 * zoomScale;
      lineHeight = 1.32;
      blockClass = 'font-bold text-slate-900 text-center mt-2 mb-3 tracking-tight';
    } else if (variant === 'author_meta') {
      fontSizePx = 13.0 * zoomScale;
      lineHeight = 1.45;
      blockClass = 'text-slate-600 text-center my-0.5';
    } else if (variant === 'section_header') {
      fontSizePx = 17.5 * zoomScale;
      lineHeight = 1.4;
      blockClass =
        'font-bold text-academic-navy text-left mt-5 mb-2 pb-1 border-b border-slate-200/80';
    } else if (variant === 'equation') {
      fontSizePx = 15.0 * zoomScale;
      lineHeight = 1.6;
      blockClass =
        'text-slate-900 text-center my-3 py-2.5 px-4 bg-slate-50/80 rounded-lg border border-slate-200/60 overflow-x-auto';
    } else if (variant === 'references') {
      fontSizePx = 12.5 * zoomScale;
      lineHeight = 1.55;
      blockClass = 'text-slate-700 text-left my-2 whitespace-pre-line';
    }

    return (
      <div
        key={item.key}
        className={`relative rounded-lg px-2.5 py-1 font-serif transition-colors cursor-pointer select-text ${blockClass} ${
          isHovered ? 'bg-blue-50/60 ring-1 ring-academic-navy/40' : 'hover:bg-slate-50/90'
        }`}
        style={{
          fontSize: `${Math.round(fontSizePx * 10) / 10}px`,
          lineHeight,
        }}
        onMouseEnter={() => setHoveredBlockId(block.id)}
        onMouseLeave={() => setHoveredBlockId(null)}
        onClick={() => openEditModal(block)}
      >
        {isHovered && (
          <span className="absolute -top-4 right-2 flex items-center gap-1 bg-academic-navy text-white px-2 py-0.5 rounded text-[10px] font-sans shadow-sm z-10">
            <Edit3 className="w-2.5 h-2.5" />
            <span>Sửa ({block.block_code})</span>
          </span>
        )}

        <MathRenderer text={displayText} />

        {block.is_user_edited && (
          <span
            className="inline-block ml-1.5 w-2 h-2 rounded-full bg-emerald-500 align-middle"
            title="Khối đã hiệu đính thủ công"
          />
        )}
      </div>
    );
  };

  /**
   * Render 1 Trang trong chuỗi cuộn liên tục:
   * - Chế độ TRANSLATED / SIDE_BY_SIDE: Trình bày 1 cột tự giãn chiều dọc (Flowing Single-Column Reader)
   *   đảm bảo không bao giờ mất chữ, đè chữ tiếng Việt, đồng thời giữ nguyên 100% ảnh và bảng biểu.
   * - Chế độ ORIGINAL: Hiển thị ảnh scan trang gốc.
   */
  const renderSinglePage = (page: CanvasPage) => {
    const aspectRatio =
      page.width_pt > 0 ? page.height_pt / page.width_pt : 1.414;
    const minPageHeight = Math.round(displayWidth * aspectRatio);
    const flowItems = flowItemsByPage.get(page.page_number) || [];

    return (
      <div
        key={page.page_number}
        ref={(el) => {
          if (el) pageRefs.current.set(page.page_number, el);
          else pageRefs.current.delete(page.page_number);
        }}
        data-page-number={page.page_number}
        id={`paper-page-${page.page_number}`}
        className="scroll-mt-20 flex flex-col items-center w-full"
      >
        <div
          className={`flex items-start gap-8 transition-all duration-200 ${
            viewMode === 'SIDE_BY_SIDE' ? 'flex-row justify-center max-w-full' : 'justify-center'
          }`}
        >
          {/* Cột Trái: Ảnh Scan Trang Gốc (Neo sticky khi cuộn đối chiếu ở chế độ SIDE_BY_SIDE) */}
          {viewMode === 'SIDE_BY_SIDE' && (
            <div className="flex flex-col items-center sticky top-6 self-start">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-slate-400" />
                Bản gốc tiếng Anh (Trang {page.page_number})
              </div>
              <div
                className="relative bg-white shadow-paper rounded-xs overflow-hidden border border-slate-300"
                style={{ width: `${displayWidth}px`, height: `${minPageHeight}px` }}
              >
                <img
                  src={page.page_image_url}
                  alt={`Bản gốc trang ${page.page_number}`}
                  className="w-full h-full object-fill block"
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
                Bản dịch tiếng Việt — 1 Cột Đầy Đủ (Trang {page.page_number})
              </div>
            )}

            {/* Chế độ ORIGINAL: Chỉ hiển thị ảnh scan gốc */}
            {viewMode === 'ORIGINAL' ? (
              <div
                className="relative bg-white shadow-paper rounded-xs overflow-hidden border border-slate-300"
                style={{ width: `${displayWidth}px`, height: `${minPageHeight}px` }}
              >
                <img
                  src={page.page_image_url}
                  alt={`Bản gốc trang ${page.page_number}`}
                  className="w-full h-full object-fill block"
                  loading="lazy"
                />
              </div>
            ) : (
              /* Chế độ TRANSLATED / SIDE_BY_SIDE: Trang Đọc Học Thuật 1 Cột Tự Giãn Chiều Dọc */
              <article
                className="relative bg-white shadow-paper hover:shadow-paper-hover transition-shadow rounded-xs border border-slate-300 flex flex-col justify-between"
                style={{
                  width: `${displayWidth}px`,
                  minHeight: `${minPageHeight}px`,
                  padding: `${Math.round(36 * zoomScale)}px ${Math.round(44 * zoomScale)}px`,
                }}
              >
                {/* Header nhỏ đánh dấu số trang của tài liệu */}
                <div className="flex items-center justify-between border-b border-slate-100 pb-2.5 mb-3 text-[11px] font-sans text-slate-400">
                  <span className="truncate max-w-[75%] font-medium">
                    {canvasData.title || 'Bản dịch Bài báo Khoa học'}
                  </span>
                  <span className="font-mono font-semibold text-slate-500">
                    Trang {page.page_number} / {totalPages}
                  </span>
                </div>

                {/* Nội dung 1 cột tự giãn theo luồng đọc */}
                <div className="flex-1 flex flex-col">
                  {flowItems.map((item) => renderFlowItem(item, page))}
                </div>

                {/* Footer số trang */}
                <div className="mt-6 pt-3 border-t border-slate-100 text-center text-[11px] font-mono text-slate-400">
                  — {page.page_number} —
                </div>
              </article>
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
            title="Trình bày 1 cột tự giãn chiều dọc, hiển thị trọn vẹn 100% văn bản tiếng Việt, hình ảnh và bảng biểu"
          >
            <Languages className="w-3.5 h-3.5" />
            <span>Bản dịch (1 Cột)</span>
          </button>

          <button
            onClick={() => setViewMode('SIDE_BY_SIDE')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              viewMode === 'SIDE_BY_SIDE'
                ? 'bg-academic-navy text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
            title="Đối chiếu song song: Gốc bên trái, Bản dịch 1 cột bên phải"
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
            title="Tải về tệp PDF bản dịch"
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

      {/* Continuous Vertical Scroll Document Stage */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto canvas-stage-grid p-6 scroll-smooth"
      >
        {totalPages === 0 ? (
          <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center max-w-md shadow-xs mx-auto my-12">
            <Loader2 className="w-8 h-8 text-academic-navy animate-spin mx-auto mb-3" />
            <h3 className="text-sm font-bold text-slate-800">Đang chuẩn bị trang đọc...</h3>
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
