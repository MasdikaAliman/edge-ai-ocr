import React, { useState, useEffect, useRef } from "react";
import * as pdfjsLib from "pdfjs-dist";

// Standard PDF.js jsdelivr CDN worker url supporting v6+
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`;

const PALETTE_COLORS = [
  "#ef4444", // red
  "#3b82f6", // blue
  "#10b981", // emerald
  "#f59e0b", // amber
  "#8b5cf6", // violet
  "#ec4899", // pink
  "#06b6d4", // cyan
  "#14b8a6", // teal
  "#f97316", // orange
  "#a855f7", // purple
];

function getFieldColor(key) {
  let hash = 0;
  for (let i = 0; i < key.length; i++) {
    hash = key.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % PALETTE_COLORS.length;
  return PALETTE_COLORS[index];
}

function findBboxLeaves(val, currentKey = "") {
  if (val === null || val === undefined) return [];

  if (typeof val === "object") {
    if ("bbox_2d" in val) {
      if (Array.isArray(val.bbox_2d) && val.bbox_2d.length === 4) {
        return [{
          key: currentKey,
          bbox_2d: val.bbox_2d,
          confidence: "confidence" in val && typeof val.confidence === "number" ? val.confidence : null,
          value: val.value
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
}) {
  const [fileType, setFileType] = useState(null); // 'pdf' or 'images'
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [zoom, setZoom] = useState(100); // percentage

  // Image states
  const [activeImageIndex, setActiveImageIndex] = useState(0);
  const [imageUrls, setImageUrls] = useState([]);

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

    // 3. Find response matching current page index
    const activePageNo = fileType === "pdf" ? currentPage : 1;

    const pageEntries = fileResponse.messages_log?.filter(
      (entry) => entry.page_no === activePageNo
    ) || [];

    if (pageEntries.length > 0) {
      // Merge responses of all entries for this page (earliest to latest so reprocessed overrides/adds to it)
      let mergedResponse = {};
      pageEntries.forEach((entry) => {
        if (entry.response) {
          mergedResponse = { ...mergedResponse, ...entry.response };
        }
      });
      return mergedResponse;
    }

    return fileResponse.data;
  };

  const renderOverlays = () => {
    const pageResponse = getActivePageResponse();
    if (!pageResponse) return null;

    const bboxes = findBboxLeaves(pageResponse);
    if (!bboxes || bboxes.length === 0) return null;

    const width = (overlaySize.width || 1);
    const height = (overlaySize.height || 1);
    return bboxes.map((box, idx) => {
      const [x1_norm, y1_norm, x2_norm, y2_norm] = box.bbox_2d;
      const color = getFieldColor(box.key);

      // Convert [0, 1000] normalized coordinates to absolute pixels based on current rendered width & height
      let abs_x1 = (x1_norm / 999) * width;
      let abs_y1 = (y1_norm / 999) * height;
      let abs_x2 = (x2_norm / 999) * width;
      let abs_y2 = (y2_norm / 999) * height;
      // Handle coordinate sorting to ensure positive widths and heights
      if (abs_x1 > abs_x2) {
        [abs_x1, abs_x2] = [abs_x2, abs_x1];
      }
      if (abs_y1 > abs_y2) {
        [abs_y1, abs_y2] = [abs_y2, abs_y1];
      }

      const left = abs_x1;
      const top = abs_y1;
      const boxWidth = abs_x2 - abs_x1;
      const boxHeight = abs_y2 - abs_y1;

      return (
        <div
          key={idx}
          className="absolute border-2 rounded hover:bg-black/10 group cursor-pointer transition-all duration-150 ease-in-out"
          style={{
            left: `${left}px`,
            top: `${top}px`,
            width: `${boxWidth}px`,
            height: `${boxHeight}px`,
            borderColor: color,
            zIndex: 10,
          }}
        >
          {/* Tooltip Badge on hover */}
          <div
            className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-1.5 hidden group-hover:flex flex-col items-center pointer-events-none select-none z-50 animate-fade-in"
            style={{ minWidth: "120px" }}
          >
            <div className="bg-slate-900/95 dark:bg-slate-950/95 text-white text-[10px] rounded px-2.5 py-1.5 shadow-lg border border-slate-700/30 flex flex-col items-center gap-0.5">
              <span className="font-bold text-slate-350 tracking-wide uppercase text-[9px]">{box.key}</span>
              {box.confidence !== null && (
                <span className="font-mono text-emerald-400 font-semibold">Conf: {Math.round(box.confidence * 100)}%</span>
              )}
            </div>
            <div className="w-1.5 h-1.5 bg-slate-900/95 dark:bg-slate-950/95 rotate-45 -mt-1 border-r border-b border-slate-700/30"></div>
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
      className="bg-white dark:bg-inverse-surface border border-border-subtle dark:border-outline-variant rounded-xl shadow-sm flex flex-col h-[650px] lg:h-[calc(100vh-12rem)] min-h-[500px] transition-colors duration-300 overflow-hidden"
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
