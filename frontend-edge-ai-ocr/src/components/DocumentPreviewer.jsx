import React, { useState, useEffect, useRef } from "react";
import * as pdfjsLib from "pdfjs-dist";

// Standard PDF.js jsdelivr CDN worker url supporting v6+
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`;


const FIELD_TO_DOC_TYPE = {
  // BL fields
  consignee: "BL",
  vessel_voyage_no: "BL",
  mvs: "BL",
  document_no_bl: "BL",
  date_bl: "BL",
  ship_date: "BL",
  country_of_destination: "BL",

  // PEB fields
  document_no_peb: "PEB",
  date_peb: "PEB",

  // PL fields
  document_no_pl: "PL",
  date_pl: "PL",

  // INV_COO fields
  invoice_no: "INV_COO",
  invoice_date: "INV_COO",
  form: "INV_COO",
  table: "INV_COO",
  total_amount: "INV_COO",
  total_weight_bruto: "INV_COO",
  total_weight_netto: "INV_COO",
  total_quantity_ctns: "INV_COO",
  total_quantity_pcs: "INV_COO",

  // Table item fields (Invoice)
  no: "INV_COO",
  kategori_barang: "INV_COO",
  model: "INV_COO",
  quantity_ctns: "INV_COO",
  quantity_pcs: "INV_COO",
  unit_price: "INV_COO",
  amount_usd: "INV_COO",
  bruto: "INV_COO",
  netto: "INV_COO",
};

function findBboxLeaves(val, currentKey = "") {
  if (val === null || val === undefined) return [];

  if (typeof val === "object") {
    if ("bbox" in val) {
      if (Array.isArray(val.bbox) && val.bbox.length === 4) {
        return [{
          key: currentKey,
          bbox: val.bbox,
          isAbsolute: true,
          confidence: "confidence" in val && val.confidence !== null && !isNaN(Number(val.confidence)) ? Number(val.confidence) : null,
          text: val.text,
          page_no: "page_no" in val ? val.page_no : null,
          status: "status" in val ? val.status : null,
          validation_errors: "validation_errors" in val ? val.validation_errors : null
        }];
      }
      return [];
    }

    if ("bbox_2d" in val) {
      if (Array.isArray(val.bbox_2d) && val.bbox_2d.length === 4) {
        return [{
          key: currentKey,
          bbox: val.bbox_2d,
          isAbsolute: false,
          confidence: "confidence" in val && val.confidence !== null && !isNaN(Number(val.confidence)) ? Number(val.confidence) : null,
          text: val.value,
          page_no: null,
          status: "status" in val ? val.status : null,
          validation_errors: "validation_errors" in val ? val.validation_errors : null
        }];
      }
      return [];
    }

    if (Array.isArray(val)) {
      return val.flatMap((item) => findBboxLeaves(item, currentKey));
    }

    return Object.entries(val).flatMap(([k, v]) => findBboxLeaves(v, k));
  }

  return [];
}

export default function DocumentPreviewer({
  files,
  selectedPages,
  onPagesChange,
  showPageSelector,
  ocrResult,
  isEmbedded = false,
}) {
  const [fileType, setFileType] = useState(null); // 'pdf' or 'images'
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [zoom, setZoom] = useState(100); // percentage

  // Image states
  const [activeImageIndex, setActiveImageIndex] = useState(0);
  const [imageUrls, setImageUrls] = useState([]);
  const [hoveredBoxIndex, setHoveredBoxIndex] = useState(null);

  // PDF.js rendering states
  const canvasRef = useRef(null);
  const imageRef = useRef(null);
  const [pdfDoc, setPdfDoc] = useState(null);
  const renderTaskRef = useRef(null);
  const [activePdfIndex, setActivePdfIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  // Absolute overlay container bounds tracking
  const [overlaySize, setOverlaySize] = useState({ width: 0, height: 0, left: 0, top: 0 });

  const updateOverlaySize = () => {
    requestAnimationFrame(() => {
      const el = fileType === "pdf" ? canvasRef.current : imageRef.current;
      if (el) {
        setOverlaySize({
          width: el.clientWidth,
          height: el.clientHeight,
          left: el.offsetLeft,
          top: el.offsetTop,
        });
      } else {
        setOverlaySize({ width: 0, height: 0, left: 0, top: 0 });
      }
    });
  };

  // Reset active PDF index when files list changes
  useEffect(() => {
    setActivePdfIndex(0);
  }, [files]);

  // Clean URLs on unmount or file change
  useEffect(() => {
    // Generate object URLs for images
    if (!files || files.length === 0) {
      setFileType(null);
      setImageUrls([]);
      setPdfDoc(null);
      setTotalPages(0);
      setIsLoading(false);
      return;
    }

    const firstFile = files[0];
    const isPdf = firstFile.type === "application/pdf" || /\.pdf$/i.test(firstFile.name);

    if (isPdf) {
      setFileType("pdf");
      setCurrentPage(1);
      setIsLoading(true);

      const fileToLoad = files[activePdfIndex] || firstFile;
      const fileReader = new FileReader();
      fileReader.onload = async function () {
        const typedarray = new Uint8Array(this.result);
        try {
          const loadingTask = pdfjsLib.getDocument({ data: typedarray });
          const pdf = await loadingTask.promise;
          setPdfDoc(pdf);
          setTotalPages(pdf.numPages);

          // Auto-select all pages initially
          const initialPages = [];
          for (let i = 1; i <= pdf.numPages; i++) {
            initialPages.push(i);
          }
          onPagesChange(initialPages);
        } catch (err) {
          console.error("Gagal memuat PDF via PDF.js:", err);
          setIsLoading(false);
        }
      };
      fileReader.readAsArrayBuffer(fileToLoad);
    } else {
      setFileType("images");
      setActiveImageIndex(0);
      setTotalPages(files.length);
      setIsLoading(false);

      const urls = files.map((file) => URL.createObjectURL(file));
      setImageUrls(urls);

      // Auto-select all images as they are processed in batch
      onPagesChange(files.map((_, idx) => idx + 1));

      return () => {
        urls.forEach((url) => URL.revokeObjectURL(url));
      };
    }
  }, [files, activePdfIndex]);

  // Auto-jump to first mismatch page/file on result load
  useEffect(() => {
    if (!ocrResult || !files || files.length === 0) return;

    const pageResponse = ocrResult.data !== undefined ? ocrResult.data : ocrResult;
    const bboxes = findBboxLeaves(pageResponse);
    const firstMismatch = bboxes.find((box) => box.page_no !== null && box.bbox !== null);

    if (firstMismatch) {
      const isCooMode = !ocrResult?.raw_results && files.length > 1;
      if (isCooMode && fileType === "pdf") {
        const fieldDocType = FIELD_TO_DOC_TYPE[firstMismatch.key];
        if (fieldDocType) {
          const targetIndex = files.findIndex((file) => {
            const name = file.name.toLowerCase();
            if (fieldDocType === "BL") return name.includes("bl") || name.includes("lading") || name.includes("bill");
            if (fieldDocType === "PEB") return name.includes("peb") || name.includes("ekspor");
            if (fieldDocType === "PL") return name.includes("packing") || name.includes("pl");
            if (fieldDocType === "INV_COO") return name.includes("invoice") || name.includes("inv");
            return false;
          });

          if (targetIndex !== -1) {
            setActivePdfIndex(targetIndex);
            setCurrentPage(firstMismatch.page_no);
          }
        }
      } else if (fileType === "pdf") {
        setCurrentPage(firstMismatch.page_no);
      } else if (fileType === "images") {
        setActiveImageIndex(firstMismatch.page_no - 1);
      }
    }
  }, [ocrResult, fileType]);

  // PDF Canvas render pipeline
  useEffect(() => {
    if (fileType !== "pdf" || !pdfDoc || !canvasRef.current) return;

    const renderPage = async () => {
      try {
        setIsLoading(true);
        // Cancel any pending render task to avoid collision
        if (renderTaskRef.current) {
          renderTaskRef.current.cancel();
        }

        const page = await pdfDoc.getPage(currentPage);
        const canvas = canvasRef.current;
        if (!canvas) {
          setIsLoading(false);
          return;
        }

        const context = canvas.getContext("2d");
        const scale = zoom / 100;
        const viewport = page.getViewport({ scale });

        canvas.height = viewport.height;
        canvas.width = viewport.width;

        const renderContext = {
          canvasContext: context,
          viewport: viewport,
        };

        const renderTask = page.render(renderContext);
        renderTaskRef.current = renderTask;
        await renderTask.promise;
        setIsLoading(false);
        updateOverlaySize();
      } catch (err) {
        if (err.name !== "RenderingCancelledException") {
          console.error("Error rendering PDF canvas:", err);
          setIsLoading(false);
        }
      }
    };

    renderPage();
  }, [pdfDoc, currentPage, zoom, fileType]);

  // Set up ResizeObserver to dynamically track layout sizes and positions of the element and its parent wrapper
  useEffect(() => {
    const el = fileType === "pdf" ? canvasRef.current : imageRef.current;
    if (!el) {
      setOverlaySize({ width: 0, height: 0, left: 0, top: 0 });
      return;
    }

    updateOverlaySize();

    const observer = new ResizeObserver(() => {
      updateOverlaySize();
    });

    observer.observe(el);

    const parent = el.parentElement;
    if (parent) {
      observer.observe(parent);
    }

    return () => observer.disconnect();
  }, [fileType, currentPage, activeImageIndex, imageUrls, pdfDoc, zoom]);

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 25, 200));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 25, 50));

  const handlePrevPage = () => {
    if (fileType === "pdf") {
      setCurrentPage((prev) => Math.max(prev - 1, 1));
    } else {
      setActiveImageIndex((prev) => Math.max(prev - 1, 0));
    }
  };

  const handleNextPage = () => {
    if (fileType === "pdf") {
      setCurrentPage((prev) => Math.min(prev + 1, totalPages));
    } else {
      setActiveImageIndex((prev) => Math.min(prev + 1, totalPages - 1));
    }
  };

  const togglePageCheckbox = (pageNum) => {
    if (selectedPages.includes(pageNum)) {
      onPagesChange(selectedPages.filter((p) => p !== pageNum));
    } else {
      onPagesChange([...selectedPages, pageNum].sort((a, b) => a - b));
    }
  };

  const getActivePageResponse = () => {
    if (!ocrResult) return null;

    // 1. Determine active file name
    const activeFileName = fileType === "pdf"
      ? files[activePdfIndex]?.name || files[0]?.name
      : files[activeImageIndex]?.name;

    // 2. Locate response for this file
    let fileResponse = null;
    if (ocrResult.raw_results) {
      const match = ocrResult.raw_results.find((r) => r.filename === activeFileName);
      fileResponse = match?.data;
    } else {
      fileResponse = ocrResult;
    }

    if (!fileResponse) return null;

    // Return the resolved data with bounding boxes if available, otherwise fallback to the response itself
    return fileResponse.data !== undefined ? fileResponse.data : fileResponse;
  };

  const getActivePageDimensions = () => {
    if (!ocrResult) return null;
    const activeFileName = fileType === "pdf"
      ? files[activePdfIndex]?.name || files[0]?.name
      : files[activeImageIndex]?.name;

    let fileResponse = null;
    if (ocrResult.raw_results) {
      const match = ocrResult.raw_results.find((r) => r.filename === activeFileName);
      fileResponse = match;
    } else {
      fileResponse = ocrResult;
    }
    return fileResponse?.page_dimensions || null;
  };

  const renderOverlays = () => {
    const pageResponse = getActivePageResponse();
    if (!pageResponse) return null;

    const bboxes = findBboxLeaves(pageResponse);
    if (!bboxes || bboxes.length === 0) return null;

    const pageDimensions = getActivePageDimensions();
    const activePageNo = fileType === "pdf" ? currentPage : activeImageIndex + 1;
    let origDim = null;
    if (ocrResult?.raw_results && fileType === "images") {
      origDim = pageDimensions?.[1] || pageDimensions?.["1"];
    } else {
      origDim = pageDimensions?.[activePageNo] || pageDimensions?.[String(activePageNo)];
    }

    // Dynamically fallback to natural/canvas dimensions if origDim is not provided in page_dimensions
    if (!origDim) {
      if (fileType === "images" && imageRef.current) {
        origDim = {
          width: imageRef.current.naturalWidth || 1,
          height: imageRef.current.naturalHeight || 1
        };
      } else if (fileType === "pdf" && canvasRef.current) {
        const scale = zoom / 100;
        origDim = {
          width: canvasRef.current.width / scale,
          height: canvasRef.current.height / scale
        };
      }
    }

    // Filter bboxes for active page
    const isCooMode = !ocrResult?.raw_results && files.length > 1;
    let activeDocType = "";
    if (isCooMode && fileType === "pdf") {
      const activeFile = files[activePdfIndex];
      const name = activeFile ? activeFile.name.toLowerCase() : "";
      if (name.includes("bl") || name.includes("lading") || name.includes("bill")) {
        activeDocType = "BL";
      } else if (name.includes("peb") || name.includes("ekspor")) {
        activeDocType = "PEB";
      } else if (name.includes("packing") || name.includes("pl")) {
        activeDocType = "PL";
      } else if (name.includes("invoice") || name.includes("inv")) {
        activeDocType = "INV_COO";
      }
    }

    const filteredBboxes = bboxes.filter((box) => {
      if (ocrResult?.raw_results && fileType === "images") {
        return true;
      }
      if (isCooMode) {
        const fieldDocType = FIELD_TO_DOC_TYPE[box.key];
        if (fieldDocType && fieldDocType !== activeDocType) {
          return false;
        }
      }
      return box.page_no === null || box.page_no === activePageNo;
    });

    if (filteredBboxes.length === 0) return null;

    const width = (overlaySize.width || 1);
    const height = (overlaySize.height || 1);
    return filteredBboxes.map((box, idx) => {
      const [x1, y1, x2, y2] = box.bbox;

      let left, top, boxWidth, boxHeight;
      if (origDim) {
        const scaleX = width / origDim.width;
        const scaleY = height / origDim.height;
        const rawW = (x2 - x1) * scaleX;
        const rawH = (y2 - y1) * scaleY;
        const absH = Math.abs(rawH);

        // Dynamic padding based on the bbox height (which scales with text/font size)
        const padX = Math.max(5, absH * 0.15);
        const padY = Math.max(2, absH * 0.1);

        left = x1 * scaleX - padX;
        top = y1 * scaleY + padY;
        boxWidth = rawW + padX * 2;
        boxHeight = rawH + padY * 2;
      }
      // Handle coordinate sorting to ensure positive widths and heights
      let sortedLeft = left;
      let sortedTop = top;
      let sortedWidth = boxWidth;
      let sortedHeight = boxHeight;
      if (sortedWidth < 0) {
        sortedLeft += sortedWidth;
        sortedWidth = -sortedWidth;
      }
      if (sortedHeight < 0) {
        sortedTop += sortedHeight;
        sortedHeight = -sortedHeight;
      }

      // Resolve status and color styling dynamically
      const status = box.status;
      let statusColor = "#10b981"; // default green (high confidence/exact match)
      let statusLabel = "Pas Sempurna";
      let statusIcon = "check_circle";
      let borderStyle = "solid";
      let badgeBg = "bg-emerald-500";
      let hoverBg = "rgba(16, 185, 129, 0.03)";
      let activeBg = "rgba(16, 185, 129, 0.08)";

      if (status === "text_modified") {
        statusColor = "#10b981";
        statusLabel = "Teks Disesuaikan";
        statusIcon = "edit_note";
        borderStyle = "dashed";
        badgeBg = "bg-indigo-500";
        hoverBg = "rgba(99, 102, 241, 0.03)";
        activeBg = "rgba(99, 102, 241, 0.08)";
      } else if (status === "low_confidence") {
        statusColor = "#f59e0b"; // amber
        statusLabel = "Akurasi Rendah";
        statusIcon = "warning";
        badgeBg = "bg-amber-500";
        hoverBg = "rgba(245, 158, 11, 0.03)";
        activeBg = "rgba(245, 158, 11, 0.08)";
      } else if (status === "uncertain") {
        statusColor = "#ef4444"; // red
        statusLabel = "Perlu Verifikasi";
        statusIcon = "gpp_maybe";
        badgeBg = "bg-red-500";
        hoverBg = "rgba(239, 68, 68, 0.03)";
        activeBg = "rgba(239, 68, 68, 0.08)";
      } else if (status === "not_found_in_ocr") {
        statusColor = "#f03b3bff"; 
        statusLabel = "Tidak Ada di OCR";
        statusIcon = "search_off";
        borderStyle = "dotted";
        badgeBg = "bg-pink-500";
        hoverBg = "rgba(236, 72, 153, 0.03)";
        activeBg = "rgba(236, 72, 153, 0.08)";
      } else {
        // No status, check confidence score
        if (box.confidence !== null) {
          if (box.confidence < 0.60) {
            statusColor = "#ef4444";
            statusLabel = "Perlu Verifikasi";
            statusIcon = "gpp_maybe";
            badgeBg = "bg-red-500";
            hoverBg = "rgba(239, 68, 68, 0.03)";
            activeBg = "rgba(239, 68, 68, 0.08)";
          } else if (box.confidence < 0.85) {
            statusColor = "#f59e0b";
            statusLabel = "Akurasi Rendah";
            statusIcon = "warning";
            badgeBg = "bg-amber-500";
            hoverBg = "rgba(245, 158, 11, 0.03)";
            activeBg = "rgba(245, 158, 11, 0.08)";
          }
        }
      }

      const isHovered = hoveredBoxIndex === idx;
      const isTooHigh = sortedTop < 185;

      return (
        <div
          key={idx}
          className="absolute border-2 rounded group cursor-pointer transition-all duration-200 ease-out pointer-events-auto"
          style={{
            left: `${sortedLeft}px`,
            top: `${sortedTop}px`,
            width: `${sortedWidth}px`,
            height: `${sortedHeight}px`,
            borderColor: statusColor,
            borderStyle: borderStyle,
            backgroundColor: isHovered ? activeBg : hoverBg,
            boxShadow: isHovered ? `0 0 12px 2px ${statusColor}70` : `0 0 4px ${statusColor}20`,
            transform: isHovered ? "scale(1.02)" : "scale(1)",
            zIndex: isHovered ? 100 : 10,
          }}
          onMouseEnter={() => setHoveredBoxIndex(idx)}
          onMouseLeave={() => setHoveredBoxIndex(null)}
        >
          {/* Permanent confidence / status badge on top-right of the box */}
          <div
            className={`absolute -top-3 right-0.5 px-1.5 py-0.5 rounded-full text-[8px] font-extrabold text-white shadow-md select-none pointer-events-none transition-all duration-200 z-20`}
            style={{ transform: isHovered ? "scale(1.1) translateY(-2px)" : "scale(1)", backgroundColor: statusColor }}
          >
            <span className="leading-none">
              {box.confidence !== null ? `${Math.round(box.confidence * 100)}%` : (status === "text_modified" ? "MOD" : (status === "uncertain" ? "UNC" : (status === "not_found_in_ocr" ? "NF" : "!")))}
            </span>
          </div>

          {/* Tooltip Badge on hover */}
          <div
            className={`absolute left-1/2 transform -translate-x-1/2 hidden group-hover:flex flex-col items-center pointer-events-none select-none z-50 transition-all duration-200 animate-fade-in ${
              isTooHigh ? "top-full mt-2" : "bottom-full mb-2"
            }`}
            style={{ minWidth: "180px" }}
          >
            {/* Tooltip arrow at top (pointing up) */}
            {isTooHigh && (
              <div className="w-2.5 h-2.5 bg-white/95 dark:bg-slate-900/95 rotate-45 -mb-1.5 border-l border-t border-slate-200 dark:border-slate-700/80 z-10"></div>
            )}

            <div className="bg-white/95 dark:bg-slate-900/95 text-slate-850 dark:text-white rounded-lg p-3 shadow-2xl border border-slate-200 dark:border-slate-700/80 flex flex-col gap-2 w-full relative z-20">
              {/* Field Key & Status Badges */}
              <div className="flex items-center justify-between gap-1 border-b border-slate-100 dark:border-slate-800 pb-1.5">
                <span className="font-bold text-slate-700 dark:text-slate-200 tracking-wide uppercase text-[10px] truncate max-w-[100px]">{box.key}</span>
                <span className={`px-1.5 py-0.5 rounded text-[8px] font-extrabold uppercase tracking-wider text-white ${badgeBg}`}>
                  {statusLabel}
                </span>
              </div>

              {/* Text Value */}
              <div className="flex flex-col gap-0.5">
                <span className="text-[8px] text-slate-400 dark:text-slate-500 font-medium uppercase tracking-wider">Nilai Terdeteksi</span>
                <span className="font-mono text-slate-800 dark:text-slate-100 text-[10px] break-words bg-slate-50 dark:bg-slate-950/50 p-1.5 rounded border border-slate-100 dark:border-slate-800/50">
                  {box.text || "—"}
                </span>
              </div>

              {/* Confidence Progress */}
              {box.confidence !== null && (
                <div className="flex flex-col gap-0.5 mt-0.5">
                  <div className="flex items-center justify-between text-[8px] font-medium uppercase tracking-wider text-slate-400">
                    <span>Confidence</span>
                    <span className="font-mono font-bold" style={{ color: statusColor }}>{Math.round(box.confidence * 100)}%</span>
                  </div>
                  <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-1 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-300"
                      style={{ width: `${box.confidence * 100}%`, backgroundColor: statusColor }}
                    />
                  </div>
                </div>
              )}

              {/* Validation Errors list */}
              {box.validation_errors && box.validation_errors.length > 0 && (
                <div className="flex flex-col gap-0.5 border-t border-slate-100 dark:border-slate-800 pt-1 mt-0.5">
                  <ul className="list-disc pl-3 text-red-650 dark:text-red-300 text-[9px] font-semibold space-y-0.5">
                    {box.validation_errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Tooltip arrow at bottom (pointing down) */}
            {!isTooHigh && (
              <div className="w-2.5 h-2.5 bg-white/95 dark:bg-slate-900/95 rotate-45 -mt-1.5 border-r border-b border-slate-200 dark:border-slate-700/80 z-10"></div>
            )}
          </div>
        </div>
      );
    });
  };

  if (!files || files.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-on-surface-variant dark:text-surface-variant p-8 bg-surface-container-low/10 border border-dashed border-border-subtle dark:border-outline-variant rounded-xl min-h-[400px]">
        <div className="text-center">
          <span className="material-symbols-outlined text-[48px] text-outline opacity-40 mb-2">visibility_off</span>
          <p className="text-body-sm font-semibold">Belum Ada Berkas yang Diunggah</p>
          <p className="text-[12px] opacity-70">Unggah PDF atau gambar untuk melihat pratinjau</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={
        isEmbedded
          ? "flex-1 flex flex-col min-h-0 overflow-hidden transition-colors duration-300"
          : "bg-white dark:bg-inverse-surface border border-border-subtle dark:border-outline-variant rounded-xl shadow-sm flex flex-col h-[650px] lg:h-[calc(100vh-12rem)] min-h-[500px] transition-colors duration-300 overflow-hidden"
      }
      id="document-previewer-container"
    >
      {/* Top Header Controls */}
      <div className="px-6 py-3 border-b border-border-subtle dark:border-outline-variant flex items-center justify-between bg-surface-ice dark:bg-on-surface-variant/5 gap-4">
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          <span className="material-symbols-outlined text-on-surface-variant dark:text-surface-variant flex-shrink-0">visibility</span>
          <span className="font-label-caps text-label-caps font-bold dark:text-on-primary select-none truncate">
            Pratinjau: {fileType === "pdf" ? files[activePdfIndex]?.name || files[0].name : files[activeImageIndex]?.name || "Gambar"}
          </span>
        </div>
        <div className="flex items-center gap-2 bg-white dark:bg-on-background rounded-lg p-1 border border-outline-variant dark:border-outline shadow-sm flex-shrink-0">
          <button
            onClick={handleZoomOut}
            className="material-symbols-outlined p-1 hover:bg-surface-container dark:hover:bg-on-surface-variant/20 text-on-surface-variant dark:text-surface-variant rounded transition-all text-[18px]"
            title="Zoom Out"
          >
            zoom_out
          </button>
          <span className="text-body-sm px-2 border-x border-outline-variant dark:border-outline dark:text-on-primary font-semibold select-none min-w-[45px] text-center">
            {zoom}%
          </span>
          <button
            onClick={handleZoomIn}
            className="material-symbols-outlined p-1 hover:bg-surface-container dark:hover:bg-on-surface-variant/20 text-on-surface-variant dark:text-surface-variant rounded transition-all text-[18px]"
            title="Zoom In"
          >
            zoom_in
          </button>
        </div>
      </div>

      {/* Main Canvas / Image Render Area */}
      <div className="flex-1 overflow-auto p-4 flex bg-surface-container-lowest/30 dark:bg-on-background/30 custom-scrollbar preview-container relative">
        {isLoading && (
          <div className="absolute inset-0 bg-white/70 dark:bg-slate-900/70 backdrop-blur-[1px] flex items-center justify-center z-10 transition-all duration-300">
            <div className="flex flex-col items-center gap-3">
              <div className="w-10 h-10 border-4 border-slate-200 dark:border-slate-800 border-t-blue-600 rounded-full animate-spin"></div>
              <span className="text-xs font-semibold text-slate-650 dark:text-slate-350 bg-white dark:bg-slate-900 px-3 py-1.5 rounded-full shadow-sm border border-slate-100 dark:border-slate-850">
                Memproses pratinjau PDF...
              </span>
            </div>
          </div>
        )}
        <div className="m-auto relative select-none">
          {fileType === "pdf" ? (
            <canvas
              ref={canvasRef}
              className={`preview-canvas ${zoom <= 100 ? "max-w-full" : "max-w-none"
                }`}
            />
          ) : (
            imageUrls[activeImageIndex] && (
              <img
                ref={imageRef}
                src={imageUrls[activeImageIndex]}
                alt="Document Preview"
                onLoad={updateOverlaySize}
                className={`preview-image ${zoom <= 100 ? "max-w-full max-h-full" : "max-w-none max-h-none"
                  }`}
                style={{
                  width: zoom <= 100 ? "auto" : `${zoom}%`,
                  height: "auto",
                }}
              />
            )
          )}

          {/* Absolute overlay container matching the exact client dimensions of the element */}
          {overlaySize.width > 0 && (
            <div
              className="absolute pointer-events-none"
              style={{
                left: `${overlaySize.left}px`,
                top: `${overlaySize.top}px`,
                width: `${overlaySize.width}px`,
                height: `${overlaySize.height}px`,
                zIndex: 10,
              }}
            >
              {renderOverlays()}
            </div>
          )}
        </div>
      </div>

      {/* PDF Selector Strip for Multiple PDFs */}
      {fileType === "pdf" && files.length > 1 && (
        <div className="px-6 py-2 bg-surface-container-lowest dark:bg-on-background border-t border-border-subtle dark:border-outline-variant flex gap-2 overflow-x-auto custom-scrollbar items-center">
          {files.map((file, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setActivePdfIndex(idx)}
              className={`flex-shrink-0 px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition-all select-none cursor-pointer ${activePdfIndex === idx
                ? "bg-secondary/15 border-secondary text-secondary dark:bg-secondary/35 dark:border-primary-fixed dark:text-primary-fixed-dim"
                : "border-outline-variant hover:bg-surface-container dark:hover:bg-on-surface-variant/20 text-on-surface-variant dark:text-surface-variant bg-white dark:bg-inverse-surface"
                }`}
            >
              <span className="material-symbols-outlined text-[16px]">picture_as_pdf</span>
              <span className="truncate max-w-[120px]">{file.name}</span>
            </button>
          ))}
        </div>
      )}

      {/* Image Strip for Multiple Images */}
      {fileType === "images" && imageUrls.length > 1 && (
        <div className="px-6 py-2 bg-surface-container-lowest dark:bg-on-background border-t border-border-subtle dark:border-outline-variant flex gap-2 overflow-x-auto custom-scrollbar items-center">
          {imageUrls.map((url, idx) => (
            <button
              key={idx}
              onClick={() => setActiveImageIndex(idx)}
              className={`flex-shrink-0 w-12 h-12 rounded border-2 overflow-hidden transition-all ${activeImageIndex === idx ? "border-primary dark:border-primary-fixed" : "border-outline-variant"
                }`}
            >
              <img src={url} alt={`Thumb ${idx + 1}`} className="w-full h-full object-cover" />
            </button>
          ))}
        </div>
      )}

      {/* Bottom Page Navigator / Checker Bar */}
      <div className="px-6 py-3.5 border-t border-border-subtle dark:border-outline-variant bg-white dark:bg-inverse-surface rounded-b-xl flex flex-wrap items-center justify-between gap-4 transition-colors duration-300">
        {fileType === "pdf" ? (
          <div className="flex items-center gap-3">
            <button
              onClick={handlePrevPage}
              disabled={currentPage === 1}
              className="p-1.5 hover:bg-surface-container dark:hover:bg-on-surface-variant/20 rounded disabled:opacity-40 text-on-surface-variant dark:text-surface-variant flex items-center justify-center transition-all"
            >
              <span className="material-symbols-outlined text-[20px]">chevron_left</span>
            </button>
            <span className="text-body-sm font-semibold select-none dark:text-on-primary">
              Halaman {currentPage} dari {totalPages}
            </span>
            <button
              onClick={handleNextPage}
              disabled={currentPage === totalPages}
              className="p-1.5 hover:bg-surface-container dark:hover:bg-on-surface-variant/20 rounded disabled:opacity-40 text-on-surface-variant dark:text-surface-variant flex items-center justify-center transition-all"
            >
              <span className="material-symbols-outlined text-[20px]">chevron_right</span>
            </button>
          </div>
        ) : (
          <div className="text-body-sm font-semibold select-none dark:text-on-primary">
            Gambar {activeImageIndex + 1} dari {totalPages}
          </div>
        )}

        {/* Visual Checkbox Per Page (Only for PDF, and only for Fields & Custom Prompt modes per PRD) */}
        {fileType === "pdf" && showPageSelector && (
          <div className="flex flex-col gap-1 items-start md:items-end">
            <span className="text-[10px] font-bold text-on-surface-variant dark:text-surface-variant uppercase tracking-wider select-none">
              Pilih Halaman Pemrosesan
            </span>
            <div className="flex gap-2 max-w-[200px] overflow-x-auto custom-scrollbar py-0.5">
              {Array.from({ length: totalPages }).map((_, idx) => {
                const pageNo = idx + 1;
                return (
                  <label key={pageNo} className="flex items-center gap-1 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={selectedPages.includes(pageNo)}
                      onChange={() => togglePageCheckbox(pageNo)}
                      className="rounded border-outline-variant dark:border-outline text-secondary dark:bg-on-background focus:ring-secondary w-3.5 h-3.5"
                    />
                    <span className="text-[12px] dark:text-on-primary font-medium">{pageNo}</span>
                  </label>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
