import React, { useState } from "react";
import toast from "react-hot-toast";
import { exportToExcel, getExcelBlob } from "../utils/excelExporter";
import { saveBlobToDirectory } from "../utils/fileSystem";

// Regex helper to format JSON with colors
function getHighlightedJson(jsonObj) {
  const json = JSON.stringify(jsonObj, null, 2);
  const safeJson = json
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  return safeJson.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
    (match) => {
      let cls = "text-slate-300"; // default
      if (/^"/.test(match)) {
        if (/:$/.test(match)) {
          cls = "text-blue-400 font-semibold"; // Key
        } else {
          cls = "text-amber-400"; // String value
        }
      } else if (/true|false/.test(match)) {
        cls = "text-emerald-400 font-bold"; // Boolean
      } else if (/null/.test(match)) {
        cls = "text-red-400 italic"; // Null
      } else {
        cls = "text-emerald-300 font-medium"; // Number
      }
      return `<span class="${cls}">${match}</span>`;
    }
  );
}

export default function ResultViewer({ 
  ocrResult, 
  activeMode, 
  selectedDocType, 
  directoryHandle, 
  uploadedFiles,
  isProcessing,
  progressInfo
}) {
  const [customFilename, setCustomFilename] = useState("");

  if (isProcessing) {
    const current = progressInfo?.current || 0;
    const total = progressInfo?.total || 0;
    const filename = progressInfo?.filename || "Menghubungi server...";
    const percentage = progressInfo?.percentage || 0;

    return (
      <div className="bg-white dark:bg-inverse-surface border border-border-subtle dark:border-outline-variant rounded-xl shadow-sm overflow-hidden p-8 flex flex-col justify-center h-[650px] lg:h-[calc(100vh-12rem)] min-h-[500px] transition-colors duration-300">
        <div className="max-w-md mx-auto w-full text-center space-y-6">
          {/* Animated Spinner Icon */}
          <div className="relative w-20 h-20 mx-auto flex items-center justify-center">
            <div className="absolute inset-0 rounded-full border-4 border-secondary/10 dark:border-secondary/20"></div>
            <div className="absolute inset-0 rounded-full border-4 border-secondary border-t-transparent animate-spin"></div>
            <span className="material-symbols-outlined text-[32px] text-secondary dark:text-secondary-fixed-dim animate-pulse">
              sync_saved_locally
            </span>
          </div>

          <div className="space-y-2">
            <h4 className="text-body-lg font-bold text-primary dark:text-primary-fixed-dim">
              Pemrosesan Dokumen Sedang Berjalan
            </h4>
            <p className="text-body-sm text-on-surface-variant dark:text-surface-variant truncate font-medium">
              📁 {filename}
            </p>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs font-bold text-on-surface-variant dark:text-surface-variant">
              <span>Progres Ekstraksi</span>
              <span>{percentage}%</span>
            </div>
            <div className="w-full bg-surface-container-highest dark:bg-on-surface-variant/20 h-2.5 rounded-full overflow-hidden shadow-inner">
              <div
                className="bg-gradient-to-r from-secondary to-blue-500 h-full rounded-full transition-all duration-300 ease-out"
                style={{ width: `${percentage}%` }}
              ></div>
            </div>
          </div>

          <p className="text-[11px] text-on-surface-variant dark:text-surface-variant italic">
            Mohon jangan menutup halaman ini selama proses ekstraksi AI berlangsung.
          </p>
        </div>
      </div>
    );
  }

  if (!ocrResult) {
    return (
      <div className="bg-white dark:bg-inverse-surface border border-border-subtle dark:border-outline-variant rounded-xl shadow-sm overflow-hidden p-8 flex items-center justify-center h-[650px] lg:h-[calc(100vh-12rem)] min-h-[500px]">
        <div className="text-center text-on-surface-variant dark:text-surface-variant">
          <span className="material-symbols-outlined text-[48px] opacity-40 mb-2">data_object</span>
          <p className="text-body-sm font-semibold">Hasil OCR Belum Tersedia</p>
          <p className="text-[12px] opacity-70">Jalankan proses OCR untuk melihat data terekstraksi</p>
        </div>
      </div>
    );
  }

  // Name calculation based on uploaded file name and local date & time
  const getExportFilename = (ext) => {
    let baseName = customFilename.trim();
    if (!baseName) {
      baseName = "ocr_result";
      if (uploadedFiles && uploadedFiles.length > 0) {
        // Remove extension (e.g. .pdf, .jpg, .png)
        baseName = uploadedFiles[0].name.replace(/\.[^/.]+$/, "");
        
        // If there are multiple files (batch images), append _batch
        if (uploadedFiles.length > 1) {
          baseName += "_batch";
        }
      }

      const now = new Date();
      const pad = (num) => String(num).padStart(2, '0');
      const dateStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
      const timeStr = `${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`;
      
      return `${baseName}_${dateStr}_${timeStr}.${ext}`;
    }

    if (baseName.toLowerCase().endsWith(`.${ext}`)) {
      return baseName;
    }
    return `${baseName}.${ext}`;
  };

  const handleDownloadJson = async () => {
    const filename = getExportFilename("json");
    const jsonStr = JSON.stringify(ocrResult, null, 2);
    const blob = new Blob([jsonStr], { type: "application/json" });

    if (directoryHandle) {
      try {
        await saveBlobToDirectory(directoryHandle, filename, blob);
        toast.success(`JSON berhasil disimpan di folder: ${directoryHandle.name}`);
      } catch (err) {
        toast.error("Gagal menyimpan ke folder: " + err.message);
      }
    } else {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("JSON berhasil diunduh.");
    }
  };

  const handleDownloadExcel = async () => {
    const filename = getExportFilename("xlsx");
    try {
      if (directoryHandle) {
        const blob = getExcelBlob(ocrResult);
        await saveBlobToDirectory(directoryHandle, filename, blob);
        toast.success(`Excel berhasil disimpan di folder: ${directoryHandle.name}`);
      } else {
        exportToExcel(ocrResult, filename);
        toast.success("Excel berhasil diunduh.");
      }
    } catch (err) {
      toast.error("Gagal mengekspor data ke Excel: " + err.message);
    }
  };

  return (
    <div
      className="bg-white dark:bg-inverse-surface border border-border-subtle dark:border-outline-variant rounded-xl shadow-sm overflow-hidden transition-colors duration-300 flex flex-col h-[650px] lg:h-[calc(100vh-12rem)] min-h-[500px]"
      id="ocr-results-container"
    >
      <div className="px-6 py-3 border-b border-border-subtle dark:border-outline-variant flex items-center justify-between bg-surface-container-low dark:bg-on-surface-variant/10">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-secondary dark:text-secondary-fixed-dim">data_object</span>
          <span className="font-label-caps text-label-caps font-bold dark:text-on-primary">Hasil Ekstraksi (JSON)</span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleDownloadJson}
            className="bg-white dark:bg-on-background border border-outline-variant dark:border-outline text-on-surface-variant dark:text-surface-variant px-4 py-1.5 rounded-lg text-body-sm font-semibold hover:bg-surface-container dark:hover:bg-on-surface-variant/20 transition-all flex items-center gap-2 shadow-sm cursor-pointer"
          >
            <span className="material-symbols-outlined text-[18px]">
              {directoryHandle ? "save" : "download"}
            </span>
            {directoryHandle ? "Simpan JSON" : "Unduh JSON"}
          </button>
          <button
            onClick={handleDownloadExcel}
            className="bg-service-ready/10 border border-service-ready text-service-ready px-4 py-1.5 rounded-lg text-body-sm font-semibold hover:bg-service-ready hover:text-white transition-all flex items-center gap-2 shadow-sm cursor-pointer"
          >
            <span className="material-symbols-outlined text-[18px]">
              {directoryHandle ? "save" : "table_view"}
            </span>
            {directoryHandle ? "Simpan Excel" : "Unduh Excel"}
          </button>
        </div>
      </div>
      {/* File Name Customizer */}
      <div className="px-6 py-2.5 border-b border-border-subtle dark:border-outline-variant bg-surface-container-lowest dark:bg-inverse-surface/40 flex items-center gap-3">
        <span className="material-symbols-outlined text-[18px] text-on-surface-variant dark:text-surface-variant select-none">drive_file_rename_outline</span>
        <input
          type="text"
          value={customFilename}
          onChange={(e) => setCustomFilename(e.target.value)}
          placeholder="Nama file ekspor kustom (opsional)..."
          className="flex-1 bg-transparent text-xs text-on-surface dark:text-on-primary placeholder-on-surface-variant/50 focus:outline-none"
        />
        {customFilename && (
          <button
            onClick={() => setCustomFilename("")}
            className="material-symbols-outlined text-[16px] text-on-surface-variant dark:text-surface-variant hover:text-red-500 transition-colors cursor-pointer"
            title="Bersihkan"
          >
            close
          </button>
        )}
      </div>
      <div className="p-6 bg-slate-900 font-data-mono text-data-mono overflow-auto flex-1 custom-scrollbar">

        <pre
          className="text-slate-300 whitespace-pre-wrap break-all"
          dangerouslySetInnerHTML={{ __html: getHighlightedJson(ocrResult) }}
        />
      </div>
    </div>
  );
}
