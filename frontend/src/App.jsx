import React, { useState, useEffect } from "react";
import toast, { Toaster } from "react-hot-toast";

import HealthIndicator from "./components/HealthIndicator";
import ConfigPanel from "./components/ConfigPanel";
import DocumentPreviewer from "./components/DocumentPreviewer";
import ResultViewer from "./components/ResultViewer";
import { startGuidedTour } from "./components/GuidedTour";
import { processBatch } from "./utils/batchProcessor";
import {
  loadDirectoryHandle,
  saveDirectoryHandle,
} from "./utils/fileSystem";

export default function App() {
  const baseUrl = "http://localhost:5030";

  // App States
  const [activeMode, setActiveMode] = useState("doc-type"); // doc-type, fields, custom-prompt
  const [isServiceReady, setIsServiceReady] = useState(true);
  const [theme, setTheme] = useState("light");

  // Config States
  const [docTypes, setDocTypes] = useState([]);
  const [selectedDocType, setSelectedDocType] = useState("");
  const [fieldsList, setFieldsList] = useState(["nomor_faktur", "tanggal_transaksi", "total_harga"]);
  const [customPrompt, setCustomPrompt] = useState(
    "Ekstrak semua informasi faktur termasuk tabel item barang, vendor, total harga sebelum dan sesudah pajak."
  );

  // File & Preview States
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [selectedPages, setSelectedPages] = useState([]);

  // Processing & Results
  const [isProcessing, setIsProcessing] = useState(false);
  const [progressInfo, setProgressInfo] = useState(null); // { current, total, filename, percentage }
  const [ocrResult, setOcrResult] = useState(null);

  // Local Directory Handles
  const [directoryHandle, setDirectoryHandle] = useState(null);

  // Load saved directory handle on mount
  useEffect(() => {
    const initDirectory = async () => {
      try {
        const handle = await loadDirectoryHandle();
        if (handle) {
          setDirectoryHandle(handle);
        }
      } catch (err) {
        console.error("Gagal memuat direktori penyimpanan:", err);
      }
    };
    initDirectory();
  }, []);

  const handleSelectDirectory = async () => {
    if (!window.showDirectoryPicker) {
      toast.error("Browser Anda tidak mendukung pemilihan folder secara langsung. Harap gunakan browser Chrome atau Edge.");
      return;
    }
    try {
      const handle = await window.showDirectoryPicker();
      setDirectoryHandle(handle);
      await saveDirectoryHandle(handle);
      toast.success(`Berhasil memilih folder: ${handle.name}`);
    } catch (err) {
      if (err.name !== "AbortError") {
        toast.error("Gagal memilih folder: " + err.message);
      }
    }
  };

  // Load Document Types dynamically from API
  useEffect(() => {
    const fetchDocTypes = async () => {
      try {
        const response = await fetch(baseUrl);
        if (response.ok) {
          const data = await response.json();
          if (data.supported_document_types) {
            setDocTypes(data.supported_document_types);
            if (data.supported_document_types.length > 0) {
              setSelectedDocType(data.supported_document_types[0]);
            }
          }
        }
      } catch (err) {
        console.error("Gagal mengambil daftar tipe dokumen:", err);
      }
    };
    fetchDocTypes();
  }, []);

  // Theme Syncing
  useEffect(() => {
    const savedTheme = localStorage.getItem("theme");
    const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const initialTheme = savedTheme === "dark" || (!savedTheme && systemPrefersDark) ? "dark" : "light";
    setTheme(initialTheme);
    updateDocumentTheme(initialTheme);
  }, []);

  const updateDocumentTheme = (newTheme) => {
    const html = document.documentElement;
    if (newTheme === "dark") {
      html.classList.add("dark");
      html.classList.remove("light");
    } else {
      html.classList.add("light");
      html.classList.remove("dark");
    }
  };

  const toggleTheme = () => {
    const newTheme = theme === "light" ? "dark" : "light";
    setTheme(newTheme);
    localStorage.setItem("theme", newTheme);
    updateDocumentTheme(newTheme);
  };

  // Drag and Drop validation helpers
  const validateAndSetFiles = (filesListToValidate) => {
    const fileArray = Array.from(filesListToValidate);
    if (fileArray.length === 0) return;

    // Check for multiple PDFs or mixed PDF + Image
    const pdfFiles = fileArray.filter(
      (f) => f.type === "application/pdf" || /\.pdf$/i.test(f.name)
    );
    const imageFiles = fileArray.filter(
      (f) => f.type.startsWith("image/") || /\.(png|jpe?g|webp|gif|tiff)$/i.test(f.name)
    );

    if (pdfFiles.length > 0 && imageFiles.length > 0) {
      toast.error("Tidak boleh mencampur PDF dan gambar dalam satu unggahan");
      return;
    }

    if (pdfFiles.length > 0) {
      if (pdfFiles.length > 20) {
        toast.error("Maksimal mengunggah 20 berkas PDF sekaligus");
        return;
      }
      setUploadedFiles(pdfFiles);
      setOcrResult(null);
      if (pdfFiles.length === 1) {
        toast.success("Berhasil mengunggah berkas PDF");
      } else {
        toast.success(`Berhasil mengunggah ${pdfFiles.length} berkas PDF`);
      }
    } else if (imageFiles.length > 0) {
      if (imageFiles.length > 20) {
        toast.error("Maksimal mengunggah 20 gambar sekaligus");
        return;
      }
      setUploadedFiles(imageFiles);
      setOcrResult(null);
      toast.success(`Berhasil mengunggah ${imageFiles.length} gambar`);
    } else {
      toast.error("Format file tidak didukung. Harap unggah PDF atau gambar.");
    }
  };

  const handleFileChange = (e) => {
    validateAndSetFiles(e.target.files);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    validateAndSetFiles(e.dataTransfer.files);
  };

  // Mapping backend errors to friendly Indonesian descriptions
  const mapBackendError = (errType, errMsg = "") => {
    const mappings = {
      llm_bad_request: "Input terlalu panjang, coba kurangi ukuran file atau halaman",
      llm_auth_error: "Gagal autentikasi ke server LLM. Harap periksa API Key Anda.",
      llm_rate_limit: "Server sedang sibuk, silakan coba beberapa saat lagi",
      llm_server_error: "Server LLM mengembalikan kesalahan internal.",
      llm_unreachable: "LLM server tidak dapat dijangkau",
      llm_timeout: "Server timeout, coba file yang lebih kecil",
      internal_error: "Terjadi kesalahan internal pada server.",
      page_limit_exceeded: "PDF terlalu banyak halaman (maksimal 20 halaman)",
      unsupported_media_type: "Format file tidak didukung",
      multiple_pdfs: "Hanya boleh mengunggah 1 file PDF",
      empty_file: "File yang diunggah kosong",
      no_files: "Silakan unggah setidaknya satu berkas.",
      file_pages_required: "Berkas tidak didukung, pastikan berkas berkaitan dengan tipe dokumen",
      too_many_images: "Jumlah gambar melebihi batas maksimum halaman.",
      file_read_error: "Gagal membaca berkas.",
      invalid_page_range: "Rentang halaman tidak valid.",
      invalid_page_number: "Nomor halaman tidak valid.",
      no_image_provided: "Tidak ada gambar atau PDF yang disediakan.",
      image_limit_exceeded: "Jumlah halaman melebihi batas maksimum.",
      url_not_allowed: "URL gambar eksternal tidak didukung.",
    };
    
    return mappings[errType] || errMsg || "Gagal memproses berkas. Terjadi kesalahan pada server.";
  };

  // Run OCR trigger
  const handleRunOcr = async () => {
    if (uploadedFiles.length === 0) {
      toast.error("Silakan unggah dokumen terlebih dahulu.");
      return;
    }

    setIsProcessing(true);
    setOcrResult(null);

    const isPdf = uploadedFiles[0].type === "application/pdf" || /\.pdf$/i.test(uploadedFiles[0].name);

    // Build params based on active mode
    let endpoint = "";
    let params = {};

    if (activeMode === "doc-type") {
      endpoint = "/ocr/process/document";
      params = { document_type: selectedDocType };
    } else if (activeMode === "fields") {
      endpoint = "/ocr/process/fields";
      params = { fields: fieldsList };
    } else if (activeMode === "custom-prompt") {
      endpoint = "/ocr/process/prompt";
      params = { custom_prompt: customPrompt };
    }

    const isCooMode = activeMode === "doc-type" && selectedDocType === "COO";

    // PDF processing logic for a single PDF or COO mode
    if ((uploadedFiles.length === 1 && isPdf) || isCooMode) {
      setProgressInfo({
        current: 1,
        total: 1,
        filename: isCooMode ? `${uploadedFiles.length} berkas COO` : uploadedFiles[0].name,
        percentage: 0,
      });

      // Format page filter string
      // Only send page selection for Fields and Custom Prompt
      const pagesString =
        activeMode !== "doc-type" && selectedPages.length > 0
          ? selectedPages.join(",")
          : "";
      params.pages = pagesString;

      const formData = new FormData();
      uploadedFiles.forEach((file) => {
        formData.append("files", file);
      });
      Object.entries(params).forEach(([key, value]) => {
        if (Array.isArray(value)) {
          value.forEach((v) => formData.append(key, v));
        } else {
          formData.append(key, value);
        }
      });

      try {
        const response = await fetch(`${baseUrl}${endpoint}`, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const errData = await response.json();
          const errType = errData?.detail?.error_type || errData?.error_type;
          const errMsg = errData?.detail?.message || errData?.message;
          console.log(errType, errMsg);
          throw new Error(mapBackendError(errType, errMsg));
        }

        const data = await response.json();
        console.log(data)
        setProgressInfo({
          current: 1,
          total: 1,
          filename: isCooMode ? `${uploadedFiles.length} berkas COO` : uploadedFiles[0].name,
          percentage: 100,
        });
        setOcrResult(data);
        toast.success(isCooMode ? "Ekstraksi berkas COO berhasil diselesaikan!" : "Ekstraksi PDF berhasil diselesaikan!");
      } catch (err) {
        toast.error(err.message);
      } finally {
        setIsProcessing(false);
        setProgressInfo(null);
      }
    } else {
      // Batch processing logic (multiple PDFs or images)
      // Progress handler
      const handleProgress = (prog) => {
        setProgressInfo(prog);
      };

      try {
        const result = await processBatch({
          files: uploadedFiles,
          endpoint,
          params,
          baseUrl,
          onProgress: handleProgress,
          mapError: mapBackendError,
        });

        setOcrResult(result);

        if (result.batch_summary.failed_files > 0) {
          toast.error(
            `${result.batch_summary.failed_files} berkas gagal diproses: ${result.batch_summary.failures.join(", ")}`,
            { duration: 6000 }
          );
        } else {
          toast.success(`Semua berkas dalam batch (${uploadedFiles.length} berkas) berhasil diproses!`);
        }
      } catch (err) {
        toast.error("Terjadi kegagalan saat memproses batch berkas.");
      } finally {
        setIsProcessing(false);
        setProgressInfo(null);
      }
    }
  };

  const isPdfFile = uploadedFiles.length > 0 && (uploadedFiles[0].type === "application/pdf" || /\.pdf$/i.test(uploadedFiles[0].name));

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-surface dark:bg-on-background font-body-main text-on-surface dark:text-on-primary transition-colors duration-300">
      <Toaster position="top-right" reverseOrder={false} />

      {/* TopNavBar */}
      <header className="fixed top-0 left-0 w-full h-16 z-50 flex justify-between items-center px-gutter bg-white dark:bg-inverse-surface border-b border-border-subtle dark:border-outline-variant transition-colors duration-300 shadow-sm">
        <div className="flex items-center gap-4">
          <span className="font-headline-md text-headline-md font-bold text-primary dark:text-primary-fixed-dim">
            Edge-AI-OCR
          </span>
          <HealthIndicator baseUrl={baseUrl} onStatusChange={setIsServiceReady} />
        </div>
        <div className="flex items-center gap-4">
          {/* Theme Toggle Button */}
          <button
            onClick={toggleTheme}
            className="relative w-14 h-7 rounded-full bg-surface-container-high dark:bg-primary-container border border-outline-variant transition-colors duration-500 focus:outline-none overflow-hidden"
            id="theme-toggle"
            title="Ubah Tema"
          >
            <div
              className={`absolute top-1 left-1 w-5 h-5 flex items-center justify-center transition-transform duration-500 ease-in-out pointer-events-none transform ${
                theme === "dark" ? "translate-x-[28px]" : "translate-x-0"
              }`}
            >
              {theme === "light" ? (
                <span className="material-symbols-outlined text-orange-500 text-[18px] sun-icon">light_mode</span>
              ) : (
                <span className="material-symbols-outlined text-blue-300 text-[18px] moon-icon">dark_mode</span>
              )}
            </div>
          </button>

          {/* Panduan Button */}
          <button
            onClick={startGuidedTour}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl border border-outline-variant dark:border-outline text-on-surface-variant dark:text-surface-variant hover:bg-surface-container dark:hover:bg-on-surface-variant/20 hover:text-primary dark:hover:text-primary-fixed-dim transition-all font-semibold text-sm cursor-pointer"
          >
            <span className="material-symbols-outlined text-[18px]">help</span>
            <span className="font-body-main">Panduan</span>
          </button>

          {/* Future Fiture: User info */}
          {/* <div className="flex items-center gap-3 pl-4 border-l border-outline-variant dark:border-outline">
            <div className="text-right hidden sm:block">
              <p className="font-label-caps text-label-caps font-bold dark:text-on-primary leading-tight">Operator Utama</p>
              <p className="text-[10px] text-on-surface-variant dark:text-surface-variant uppercase tracking-wider">Level 4 Access</p>
            </div>
            <img
              alt="Profil Operator"
              className="w-8 h-8 rounded-full border border-outline-variant bg-surface-container-low"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuAkhehBT5Hec_26IUmJnKED6XonTSn351j44MXU_QO69ljwmRnrMSUAExoAQKmJFoj44WH0UP-WAW1tiibSGdKNWftxu3F6Y9v3Yp-fMtwkE626sR5RKIwukF4hWFE_CICauJE-cG62TCNqSQiXcoRJjLVO8r63-QEEdTtfeXj94PVMFk4GBQoC0JPvk7QuzAn6z3voDMZOpZUoZk4DF99CBNbaG-XkGeuT6UsniX-t6xDIdNu2HGkZQkw7PBgtmqwpc96JBf3Vkc0F"
            />
          </div> */}
        </div>
      </header>

      {/* Main Layout Body */}
      <div className="flex pt-16 h-full overflow-hidden">

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto custom-scrollbar p-6 bg-surface dark:bg-on-background transition-colors duration-300">
          <div className="w-full max-w-none space-y-6">
            {/* Centered Mode Selector */}
            <section className="flex justify-center mb-6">
              <div
                className="bg-surface-container-low dark:bg-inverse-surface p-1 rounded-xl flex gap-1 border border-border-subtle dark:border-outline-variant transition-colors duration-300"
                id="mode-selector-container"
              >
                {[
                  { id: "doc-type", label: "Document Type" },
                  { id: "fields", label: "Fields" },
                  { id: "custom-prompt", label: "Custom Prompt" },
                ].map((mode) => (
                  <button
                    key={mode.id}
                    onClick={() => {
                      setActiveMode(mode.id);
                      setOcrResult(null);
                    }}
                    className={`px-6 py-2 rounded-lg text-body-sm font-semibold transition-all ${
                      activeMode === mode.id
                        ? "bg-white dark:bg-secondary text-secondary dark:text-white shadow-sm"
                        : "text-on-surface-variant dark:text-surface-variant hover:bg-white/50 dark:hover:bg-on-surface-variant/20"
                    }`}
                  >
                    {mode.label}
                  </button>
                ))}
              </div>
            </section>

            <div className="grid grid-cols-12 gap-6 items-start">
              {/* Left Column: Combined Config & Upload Card */}
              <div className="col-span-12 lg:col-span-3 space-y-4">
                <div className="bg-white dark:bg-inverse-surface border border-border-subtle dark:border-outline-variant p-5 rounded-xl shadow-sm space-y-6 transition-colors duration-300">
                  {/* Configuration Panel */}
                  <ConfigPanel
                    activeMode={activeMode}
                    docTypes={docTypes}
                    selectedDocType={selectedDocType}
                    setSelectedDocType={setSelectedDocType}
                    fieldsList={fieldsList}
                    setFieldsList={setFieldsList}
                    customPrompt={customPrompt}
                    setCustomPrompt={setCustomPrompt}
                    directoryHandle={directoryHandle}
                    onSelectDirectory={handleSelectDirectory}
                  />

                  <hr className="border-border-subtle dark:border-outline-variant" />

                  {/* Upload Zone */}
                  {uploadedFiles.length === 0 ? (
                    <div
                      onDragOver={handleDragOver}
                      onDrop={handleDrop}
                      onClick={() => document.getElementById("file-input").click()}
                      className="border-2 border-dashed border-outline-variant dark:border-outline p-6 rounded-xl flex flex-col items-center justify-center text-center group hover:border-secondary dark:hover:border-primary transition-all cursor-pointer relative overflow-hidden bg-surface-ice/30 dark:bg-transparent"
                      id="upload-zone-container"
                    >
                      <input
                        type="file"
                        id="file-input"
                        multiple
                        accept=".pdf, image/*"
                        onChange={handleFileChange}
                        className="hidden"
                      />
                      <div className="w-12 h-12 bg-secondary/10 dark:bg-secondary/20 rounded-full flex items-center justify-center text-secondary dark:text-primary-fixed-dim mb-3 group-hover:scale-110 transition-transform">
                        <span className="material-symbols-outlined text-[28px]">upload_file</span>
                      </div>
                      <h4 className="font-headline-md text-[16px] text-primary dark:text-primary-fixed-dim mb-1 font-bold">
                        Unggah Dokumen
                      </h4>
                      <p className="text-[11px] text-on-surface-variant dark:text-surface-variant mb-3">
                        Tarik & lepas PDF/Gambar di sini
                      </p>
                      <button className="bg-secondary dark:bg-primary-container text-white px-4 py-1.5 rounded-lg text-xs font-semibold hover:bg-primary-container dark:hover:bg-primary transition-colors">
                        Pilih File
                      </button>
                    </div>
                  ) : (
                    <div
                      onDragOver={handleDragOver}
                      onDrop={handleDrop}
                      className="border border-solid border-outline-variant dark:border-outline p-5 rounded-xl bg-surface-ice/30 dark:bg-on-surface-variant/5 transition-all relative overflow-hidden"
                      id="upload-zone-container"
                    >
                      <div className="flex items-center gap-3 mb-4 min-w-0">
                        <div className="w-10 h-10 bg-secondary/10 dark:bg-secondary/20 rounded-lg flex items-center justify-center text-secondary dark:text-primary-fixed-dim shrink-0">
                          <span className="material-symbols-outlined text-[24px]">
                            {uploadedFiles[0].type === "application/pdf" || /\.pdf$/i.test(uploadedFiles[0].name) ? "picture_as_pdf" : "image"}
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <h5 className="text-body-sm font-bold text-primary dark:text-primary-fixed-dim truncate" title={uploadedFiles.length === 1 ? uploadedFiles[0].name : `${uploadedFiles.length} ${isPdfFile ? "PDF" : "Gambar"} terpilih`}>
                            {uploadedFiles.length === 1 ? uploadedFiles[0].name : `${uploadedFiles.length} ${isPdfFile ? "PDF" : "Gambar"} terpilih`}
                          </h5>
                          <p className="text-[10px] text-on-surface-variant dark:text-surface-variant truncate">
                            {uploadedFiles.length === 1 
                              ? `${(uploadedFiles[0].size / 1024).toFixed(1)} KB` 
                              : `${(uploadedFiles.reduce((acc, f) => acc + f.size, 0) / 1024).toFixed(1)} KB (Total)`
                            }
                          </p>
                        </div>
                      </div>

                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => document.getElementById("file-input").click()}
                          className="flex-1 flex items-center justify-center gap-1.5 border border-outline-variant dark:border-outline hover:border-secondary hover:text-secondary dark:hover:border-primary-fixed-dim text-on-surface-variant dark:text-surface-variant font-semibold py-1.5 px-3 rounded-lg text-xs transition-all cursor-pointer bg-white dark:bg-on-background shadow-sm"
                        >
                          <span className="material-symbols-outlined text-[16px]">cached</span>
                          Ganti File
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setUploadedFiles([]);
                            setOcrResult(null);
                          }}
                          className="flex items-center justify-center gap-1.5 bg-red-50 hover:bg-red-100 dark:bg-red-950/20 dark:hover:bg-red-950/30 text-red-600 dark:text-red-400 font-semibold py-1.5 px-3 rounded-lg text-xs transition-all cursor-pointer border border-red-200 dark:border-red-900/50 shadow-sm"
                        >
                          <span className="material-symbols-outlined text-[16px]">delete</span>
                          Hapus
                        </button>
                      </div>
                      
                      <input
                        type="file"
                        id="file-input"
                        multiple
                        accept=".pdf, image/*"
                        onChange={handleFileChange}
                        className="hidden"
                      />
                    </div>
                  )}
                </div>

                {/* OCR Execution Button (for non-empty preview) */}
                {uploadedFiles.length > 0 && !isProcessing && (
                  <button
                    onClick={handleRunOcr}
                    disabled={!isServiceReady}
                    className="w-full flex items-center justify-center gap-2 py-3 bg-secondary dark:bg-secondary-container disabled:bg-gray-300 disabled:dark:bg-outline-variant disabled:cursor-not-allowed text-white rounded-lg font-semibold hover:bg-primary-container transition-colors shadow-md text-sm cursor-pointer"
                  >
                    <span className="material-symbols-outlined text-[20px]">play_arrow</span>
                    Jalankan OCR
                  </button>
                )}
              </div>

              {/* Center Column: Preview & OCR Trigger */}
              <div className="col-span-12 lg:col-span-6 space-y-4" id="document-previewer-container" >
                <DocumentPreviewer
                  files={uploadedFiles}
                  selectedPages={selectedPages}
                  onPagesChange={setSelectedPages}
                  showPageSelector={activeMode !== "doc-type"}
                />
              </div>

              {/* Right Column: Results Viewer */}
              <div className="col-span-12 lg:col-span-3" id="ocr-results-container">
                <ResultViewer
                  ocrResult={ocrResult}
                  activeMode={activeMode}
                  selectedDocType={selectedDocType}
                  directoryHandle={directoryHandle}
                  uploadedFiles={uploadedFiles}
                  isProcessing={isProcessing}
                  progressInfo={progressInfo}
                />
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
