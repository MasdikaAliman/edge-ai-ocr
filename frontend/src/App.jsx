import React, { useState, useEffect } from "react";
import toast, { Toaster } from "react-hot-toast";

import HealthIndicator from "./components/HealthIndicator";
import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import Dashboard from "./components/Dashboard";
import Stepper from "./components/Stepper";
import DokumenExtractor from "./components/DokumenExtractor";
import CooExtractor from "./components/CooExtractor";
import BatchExtractor from "./components/BatchExtractor";
import CustomPromptExtractor from "./components/CustomPromptExtractor";
import { startGuidedTour } from "./components/GuidedTour";
import { processBatch } from "./utils/batchProcessor";
import {
  loadDirectoryHandle,
  saveDirectoryHandle,
} from "./utils/fileSystem";

export default function App() {
  const baseUrl = "http://localhost:5030";

  // Navigation: "dashboard", "dokumen", "coo", "batch", "prompt"
  const [activePage, setActivePage] = useState("dashboard");

  // App States
  const [isServiceReady, setIsServiceReady] = useState(true);
  const [theme, setTheme] = useState("light");

  // Config States
  const [docTypes, setDocTypes] = useState([]);
  const [selectedDocType, setSelectedDocType] = useState("");
  const [activeMode, setActiveMode] = useState("doc-type"); // doc-type, fields
  const [fieldsList, setFieldsList] = useState(["nomor_faktur", "tanggal_transaksi", "total_harga"]);
  const [pageSelectionText, setPageSelectionText] = useState("");
  const [customPrompt, setCustomPrompt] = useState(
    "Ekstrak semua informasi faktur termasuk tabel item barang, vendor, total harga sebelum dan sesudah pajak."
  );
  const [concurrencyLimit, setConcurrencyLimit] = useState(3);

  // File & Preview States
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [selectedPages, setSelectedPages] = useState([]);

  // Processing & Results
  const [isProcessing, setIsProcessing] = useState(false);
  const [progressInfo, setProgressInfo] = useState(null);
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

    const pdfFiles = fileArray.filter(
      (f) => f.type === "application/pdf" || /\.pdf$/i.test(f.name)
    );
    const imageFiles = fileArray.filter(
      (f) => f.type.startsWith("image/") || /\.(png|jpe?g|webp|gif|tiff)$/i.test(f.name)
    );

    const isPdf = pdfFiles.length > 0;
    const isImg = imageFiles.length > 0;

    if (isPdf && isImg) {
      toast.error("Tidak boleh mencampur PDF dan gambar dalam satu unggahan");
      return;
    }

    if (!isPdf && !isImg) {
      toast.error("Format file tidak didukung. Harap unggah PDF atau Gambar.");
      return;
    }

    if (activePage === "coo") {
      if (fileArray.length > 4) {
        toast.error("Maksimal mengunggah 4 berkas untuk COO.");
        return;
      }
      setUploadedFiles(fileArray);
      setOcrResult(null);
      setSelectedPages([]);
      toast.success(`Berhasil mengunggah ${fileArray.length} berkas COO.`);
    } else if (activePage === "batch") {
      if (fileArray.length > 50) {
        toast.error("Maksimal mengunggah 50 berkas sekaligus.");
        return;
      }
      setUploadedFiles(fileArray);
      setOcrResult(null);
      setSelectedPages([]);
      toast.success(`Berhasil mengunggah ${fileArray.length} berkas batch.`);
    } else {
      // activePage === "dokumen" or "prompt"
      if (fileArray.length > 20) {
        toast.error("Maksimal mengunggah 20 berkas sekaligus.");
        return;
      }
      setUploadedFiles(fileArray);
      setOcrResult(null);
      setSelectedPages([]);
      if (fileArray.length === 1) {
        toast.success(`Berhasil mengunggah ${fileArray[0].name}`);
      } else {
        toast.success(`Berhasil mengunggah ${fileArray.length} berkas.`);
      }
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
      coo_files_limit_exceeded: "Unggahan berkas COO melebihi batas (maksimal 4 berkas: PEB, INV, PL, BL)",
      coo_invalid_composition: errMsg || "Komposisi berkas COO tidak lengkap atau tidak valid (harus terdiri dari BL, PEB, PL, dan Invoice)",
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

    const pagesString = pageSelectionText || (selectedPages.length > 0 ? selectedPages.join(",") : "");

    // Run as batch if active page is batch, or if multiple files are uploaded (except COO which processes multiple files in a single request)
    const runAsBatch = activePage === "batch" || (uploadedFiles.length > 1 && activePage !== "coo");

    if (runAsBatch) {
      let endpoint = "";
      let params = {};

      if (activePage === "batch" || activePage === "dokumen") {
        if (activeMode === "fields") {
          endpoint = "/ocr/process/fields";
          params = { fields: fieldsList, pages: pagesString };
        } else if (activeMode === "prompt") {
          endpoint = "/ocr/process/prompt";
          params = { custom_prompt: customPrompt, pages: pagesString };
        } else {
          endpoint = "/ocr/process/document";
          params = { document_type: selectedDocType, pages: pagesString };
        }
      } else if (activePage === "prompt") {
        endpoint = "/ocr/process/prompt";
        params = { custom_prompt: customPrompt, pages: pagesString };
      }

      const handleProgress = (prog) => {
        setProgressInfo(prog);
      };

      try {
        const result = await processBatch({
          files: uploadedFiles,
          endpoint,
          params,
          baseUrl,
          concurrencyLimit,
          onProgress: handleProgress,
          mapError: mapBackendError,
        });

        setOcrResult(result);

        if (result.batch_summary.failed_files > 0) {
          toast.error(
            `${result.batch_summary.failed_files} berkas gagal diproses.`,
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
    } else {
      const isCooMode = activePage === "coo";
      let endpoint = "";
      let params = {};

      if (activePage === "dokumen" || activePage === "batch") {
        if (activeMode === "fields") {
          endpoint = "/ocr/process/fields";
          params = { fields: fieldsList, pages: pagesString };
        } else if (activeMode === "prompt") {
          endpoint = "/ocr/process/prompt";
          params = { custom_prompt: customPrompt, pages: pagesString };
        } else {
          endpoint = "/ocr/process/document";
          params = { document_type: selectedDocType, pages: pagesString };
        }
      } else if (activePage === "coo") {
        endpoint = "/ocr/process/document";
        params = { document_type: "COO", pages: pagesString };
      } else if (activePage === "prompt") {
        endpoint = "/ocr/process/prompt";
        params = { custom_prompt: customPrompt, pages: pagesString };
      }

      setProgressInfo({
        current: 1,
        total: 1,
        filename: isCooMode ? `${uploadedFiles.length} berkas COO` : uploadedFiles[0].name,
        percentage: 0,
      });

      const formData = new FormData();
      uploadedFiles.forEach((file) => {
        formData.append("files", file);
      });
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (Array.isArray(value)) {
            value.forEach((v) => formData.append(key, v));
          } else {
            formData.append(key, value);
          }
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
          throw new Error(mapBackendError(errType, errMsg));
        }

        const data = await response.json();
        setProgressInfo({
          current: 1,
          total: 1,
          filename: isCooMode ? `${uploadedFiles.length} berkas COO` : uploadedFiles[0].name,
          percentage: 100,
        });
        setOcrResult(data);
        toast.success(isCooMode ? "Ekstraksi berkas COO berhasil diselesaikan!" : "Ekstraksi berhasil diselesaikan!");
      } catch (err) {
        toast.error(err.message);
      } finally {
        setIsProcessing(false);
        setProgressInfo(null);
      }
    }
  };

  const handlePageChange = (newPage) => {
    setActivePage(newPage);
    setUploadedFiles([]);
    setOcrResult(null);
    setSelectedPages([]);
    setIsProcessing(false);
    setProgressInfo(null);
    setPageSelectionText("");
  };

  const handleSupportTagClick = (tag) => {
    const matched = docTypes.find(t => t.toLowerCase() === tag.toLowerCase());
    if (matched) {
      setSelectedDocType(matched);
      toast.success(`Tipe dokumen diset ke: ${matched}`);
    } else {
      if (tag.toLowerCase() === "dll.") {
        toast("Silakan pilih tipe dokumen di menu konfigurasi.");
      } else {
        toast.error(`Tipe dokumen ${tag} tidak didukung.`);
      }
    }
  };

  const handlePromptExampleClick = (ex) => {
    setCustomPrompt(ex.value);
    toast.success("Prompt contoh berhasil diterapkan!");
  };

  // Steps Calculator
  const getStepperStep = () => {
    if (activePage === "batch") {
      if (ocrResult) return 4;
      if (isProcessing) return 3;
      if (uploadedFiles.length > 0) return 2;
      return 1;
    } else {
      if (ocrResult) return 3;
      if (isProcessing) return 3; // Show Step 3 (Hasil/Progress View) when processing
      if (uploadedFiles.length > 0) return 2;
      return 1;
    }
  };

  // Click handler to go back to previous steps
  const handleStepClick = (targetStep) => {
    const currentStep = getStepperStep();
    if (targetStep >= currentStep) return;

    if (targetStep === 1) {
      setUploadedFiles([]);
      setOcrResult(null);
      setIsProcessing(false);
      setProgressInfo(null);
      setSelectedPages([]);
      setPageSelectionText("");
    } else if (targetStep === 2) {
      if (uploadedFiles.length > 0) {
        setOcrResult(null);
        setIsProcessing(false);
        setProgressInfo(null);
      }
    } else if (targetStep === 3 && activePage === "batch") {
      if (uploadedFiles.length > 0 && !isProcessing) {
        handleRunOcr();
      }
    }
  };

  // Helper page title/desc
  const getPageInfo = () => {
    switch (activePage) {
      case "dashboard":
        return { title: "Ekstraksi Dokumen", desc: "Pilih fitur yang sesuai dengan kebutuhan Anda" };
      case "dokumen":
        return { title: "Ekstraksi Dokumen", desc: "Ekstrak data dari dokumen tunggal seperti KTP, NPWP, Invoice, dan lainnya." };
      case "coo":
        return { title: "Ekstraksi COO (Multi-Doc)", desc: "Ekstrak data COO dari 4 dokumen: BL, PEB, PL, dan Invoice COO." };
      case "batch":
        return { title: "Batch Processing", desc: "Proses banyak dokumen sekaligus dan gabungkan hasilnya dalam satu file." };
      case "prompt":
        return { title: "Custom Prompt", desc: "Ekstraksi bebas menggunakan prompt kustom sesuai kebutuhan Anda." };
      default:
        return { title: "Edge AI OCR", desc: "Local AI Document Extraction" };
    }
  };

  const pageInfo = getPageInfo();

  const handleStartGuidedTour = () => {
    startGuidedTour({
      setActivePage,
      setUploadedFiles,
      setOcrResult,
    });
  };

  // Props bundles for action pages
  const sharedProps = {
    currentStep: getStepperStep(),
    uploadedFiles,
    setUploadedFiles,
    pageSelectionText,
    setPageSelectionText,
    isServiceReady,
    handleRunOcr,
    handleFileChange,
    selectedPages,
    setSelectedPages,
    ocrResult,
    setOcrResult,
    directoryHandle,
    onSelectDirectory: handleSelectDirectory,
    isProcessing,
    progressInfo,
    handleDragOver,
    handleDrop,
    activeMode,
    setActiveMode,
    fieldsList,
    setFieldsList,
    customPrompt,
    setCustomPrompt,
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 dark:bg-[#080d1a] font-body-main text-slate-900 dark:text-slate-100 transition-colors duration-300">
      <Toaster position="top-right" reverseOrder={false} />
      <div className="hidden">
        <HealthIndicator baseUrl={baseUrl} onStatusChange={setIsServiceReady} />
      </div>

      {/* Sidebar navigation */}
      <Sidebar
        activePage={activePage}
        onPageChange={handlePageChange}
        isServiceReady={isServiceReady}
        startGuidedTour={handleStartGuidedTour}
      />

      {/* Main Content Area Wrapper */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Top Header Bar */}
        <TopBar
          pageTitle={pageInfo.title}
          pageDesc={pageInfo.desc}
          isServiceReady={isServiceReady}
          theme={theme}
          toggleTheme={toggleTheme}
          startGuidedTour={handleStartGuidedTour}
        />

        {/* Main View content */}
        <main className="flex-1 overflow-y-auto custom-scrollbar p-6 bg-slate-50 dark:bg-[#080d1a] transition-colors duration-300">
          {activePage === "dashboard" ? (
            <Dashboard 
              onPageChange={handlePageChange}
              startGuidedTour={handleStartGuidedTour}
            />
          ) : (
            <div className="w-full space-y-6">
              {/* Stepper Progress Indicator */}
              <Stepper 
                activePage={activePage}
                currentStep={getStepperStep()}
                onStepClick={handleStepClick}
              />

              {/* Action Pages Switches */}
              {activePage === "dokumen" && (
                <DokumenExtractor
                  {...sharedProps}
                  docTypes={docTypes}
                  selectedDocType={selectedDocType}
                  setSelectedDocType={setSelectedDocType}
                  handleSupportTagClick={handleSupportTagClick}
                />
              )}

              {activePage === "coo" && (
                <CooExtractor
                  {...sharedProps}
                />
              )}

              {activePage === "batch" && (
                <BatchExtractor
                  {...sharedProps}
                  docTypes={docTypes}
                  selectedDocType={selectedDocType}
                  setSelectedDocType={setSelectedDocType}
                  concurrencyLimit={concurrencyLimit}
                  setConcurrencyLimit={setConcurrencyLimit}
                />
              )}

              {activePage === "prompt" && (
                <CustomPromptExtractor
                  {...sharedProps}
                  customPrompt={customPrompt}
                  setCustomPrompt={setCustomPrompt}
                  handlePromptExampleClick={handlePromptExampleClick}
                />
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
