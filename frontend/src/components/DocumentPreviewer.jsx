import React, { useState, useEffect, useRef } from "react";
import * as pdfjsLib from "pdfjs-dist";

// Standard PDF.js jsdelivr CDN worker url supporting v6+
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`;

export default function DocumentPreviewer({
  files,
  selectedPages,
  onPagesChange,
  showPageSelector,
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
  const [pdfDoc, setPdfDoc] = useState(null);
  const renderTaskRef = useRef(null);
  const [activePdfIndex, setActivePdfIndex] = useState(0);

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
      return;
    }

    const firstFile = files[0];
    const isPdf = firstFile.type === "application/pdf" || /\.pdf$/i.test(firstFile.name);

    if (isPdf) {
      setFileType("pdf");
      setCurrentPage(1);
      
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
        }
      };
      fileReader.readAsArrayBuffer(fileToLoad);
    } else {
      setFileType("images");
      setActiveImageIndex(0);
      setTotalPages(files.length);
      
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
        // Cancel any pending render task to avoid collision
        if (renderTaskRef.current) {
          renderTaskRef.current.cancel();
        }

        const page = await pdfDoc.getPage(currentPage);
        const canvas = canvasRef.current;
        if (!canvas) return;

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
      } catch (err) {
        if (err.name !== "RenderingCancelledException") {
          console.error("Error rendering PDF canvas:", err);
        }
      }
    };

    renderPage();
  }, [pdfDoc, currentPage, zoom, fileType]);

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
      <div className="flex-1 overflow-auto p-4 flex bg-surface-container-lowest/30 dark:bg-on-background/30 custom-scrollbar preview-container">
        {fileType === "pdf" ? (
          <div className="m-auto">
            <canvas
              ref={canvasRef}
              className={`preview-canvas ${
                zoom <= 100 ? "max-w-full" : "max-w-none"
              }`}
            />
          </div>
        ) : (
          <div className="m-auto flex justify-center items-center">
            {imageUrls[activeImageIndex] && (
              <img
                src={imageUrls[activeImageIndex]}
                alt="Document Preview"
                className={`preview-image ${
                  zoom <= 100 ? "max-w-full max-h-full" : "max-w-none max-h-none"
                }`}
                style={{
                  width: `${zoom}%`,
                }}
              />
            )}
          </div>
        )}
      </div>

      {/* PDF Selector Strip for Multiple PDFs */}
      {fileType === "pdf" && files.length > 1 && (
        <div className="px-6 py-2 bg-surface-container-lowest dark:bg-on-background border-t border-border-subtle dark:border-outline-variant flex gap-2 overflow-x-auto custom-scrollbar items-center">
          {files.map((file, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setActivePdfIndex(idx)}
              className={`flex-shrink-0 px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition-all select-none cursor-pointer ${
                activePdfIndex === idx 
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
              className={`flex-shrink-0 w-12 h-12 rounded border-2 overflow-hidden transition-all ${
                activeImageIndex === idx ? "border-primary dark:border-primary-fixed" : "border-outline-variant"
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
