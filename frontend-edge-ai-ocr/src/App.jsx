import React, { useState, useEffect, useRef } from "react";
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
import Login from "./components/Login";
import Settings from "./components/Settings";
import { startGuidedTour } from "./components/GuidedTour";
import { processBatch } from "./utils/batchProcessor";
import {
  loadDirectoryHandle,
  saveDirectoryHandle,
} from "./utils/fileSystem";

export default function App() {
  const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:5030";

  // Auth States
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [user, setUser] = useState(() => {
    try {
      const savedUser = localStorage.getItem("user");
      return savedUser ? JSON.parse(savedUser) : null;
    } catch {
      return null;
    }
  });

  const handleLoginSuccess = (newToken, newUser) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem("token", newToken);
    localStorage.setItem("user", JSON.stringify(newUser));
  };

  const handleLogout = () => {
    setToken("");
    setUser(null);
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setActivePage("dashboard");
    toast.success("Berhasil keluar aplikasi");
  };

  // Navigation: "dashboard", "dokumen", "coo", "batch", "prompt", "settings"
  const [activePage, setActivePage] = useState("dashboard");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);

  // App States
  const [isServiceReady, setIsServiceReady] = useState(true);
  const [theme, setTheme] = useState("light");

  // Config States
  const [docTypes, setDocTypes] = useState([]);
  const [selectedDocType, setSelectedDocType] = useState("");
  const [activeMode, setActiveMode] = useState("doc-type"); // doc-type, fields
  const [fieldsList, setFieldsList] = useState(["nomor_faktur", "tanggal_transaksi", "total_harga"]);
  const [customPrompt, setCustomPrompt] = useState(
    "Ekstrak semua informasi faktur termasuk tabel item barang, vendor, total harga sebelum dan sesudah pajak."
  );
  const [concurrencyLimit, setConcurrencyLimit] = useState(3);

  // Page-specific states stored in a single object to maintain state when switching tabs
  const [pageStates, setPageStates] = useState({
    dokumen: { uploadedFiles: [], selectedPages: [], pageSelectionText: "", ocrResult: null, isProcessing: false, progressInfo: null },
    coo: { uploadedFiles: [], selectedPages: [], pageSelectionText: "", ocrResult: null, isProcessing: false, progressInfo: null },
    batch: { uploadedFiles: [], selectedPages: [], pageSelectionText: "", ocrResult: null, isProcessing: false, progressInfo: null },
    prompt: { uploadedFiles: [], selectedPages: [], pageSelectionText: "", ocrResult: null, isProcessing: false, progressInfo: null },
  });

  // Create a ref to track the active page so that closures (like in the Guided Tour) always use the correct state
  const activePageRef = useRef(activePage);
  activePageRef.current = activePage;

  const updatePageState = (page, key, value) => {
    if (page === "dashboard") return;
    setPageStates((prev) => {
      const currentPageState = prev[page] || {
        uploadedFiles: [],
        selectedPages: [],
        pageSelectionText: "",
        ocrResult: null,
        isProcessing: false,
        progressInfo: null,
      };

      const newValue = typeof value === "function" ? value(currentPageState[key]) : value;

      return {
        ...prev,
        [page]: {
          ...currentPageState,
          [key]: newValue,
        },
      };
    });
  };

  // Keep these active-page bound functions specifically for GuidedTour to work correctly
  const setUploadedFiles = (val) => updatePageState(activePageRef.current, "uploadedFiles", val);
  const setOcrResult = (val) => updatePageState(activePageRef.current, "ocrResult", val);

  const getStepperStepForPage = (page) => {
    const pageState = pageStates[page];
    if (!pageState) return 1;
    if (page === "batch") {
      if (pageState.ocrResult) return 4;
      if (pageState.isProcessing) return 3;
      if (pageState.uploadedFiles.length > 0) return 2;
      return 1;
    } else {
      if (pageState.ocrResult) return 3;
      if (pageState.isProcessing) return 3;
      if (pageState.uploadedFiles.length > 0) return 2;
      return 1;
    }
  };

  const getPropsForPage = (page) => {
    const pageState = pageStates[page] || {
      uploadedFiles: [],
      selectedPages: [],
      pageSelectionText: "",
      ocrResult: null,
      isProcessing: false,
      progressInfo: null,
    };
    
    return {
      currentStep: getStepperStepForPage(page),
      uploadedFiles: pageState.uploadedFiles,
      setUploadedFiles: (val) => updatePageState(page, "uploadedFiles", val),
      pageSelectionText: pageState.pageSelectionText,
      setPageSelectionText: (val) => updatePageState(page, "pageSelectionText", val),
      isServiceReady,
      handleRunOcr: () => handleRunOcr(page),
      handleFileChange,
      handleAppendFileChange,
      selectedPages: pageState.selectedPages,
      setSelectedPages: (val) => updatePageState(page, "selectedPages", val),
      ocrResult: pageState.ocrResult,
      setOcrResult: (val) => updatePageState(page, "ocrResult", val),
      directoryHandle,
      onSelectDirectory: handleSelectDirectory,
      isProcessing: pageState.isProcessing,
      progressInfo: pageState.progressInfo,
      activeMode,
      setActiveMode,
      fieldsList,
      setFieldsList,
      customPrompt,
      setCustomPrompt,
      handleDragOver,
      handleDrop,
    };
  };

  // Map active state variables for general layouts
  const activeState = pageStates[activePage] || {
    uploadedFiles: [],
    selectedPages: [],
    pageSelectionText: "",
    ocrResult: null,
    isProcessing: false,
    progressInfo: null,
  };
  const { uploadedFiles, isProcessing } = activeState;

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
  const validateAndSetFiles = (filesListToValidate, isAppend = false) => {
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

    let finalFiles = [];
    if (isAppend) {
      // Validate that we don't mix incoming files type with existing files type
      const existingPdfFiles = uploadedFiles.filter(
        (f) => f.type === "application/pdf" || /\.pdf$/i.test(f.name)
      );
      const existingImageFiles = uploadedFiles.filter(
        (f) => f.type.startsWith("image/") || /\.(png|jpe?g|webp|gif|tiff)$/i.test(f.name)
      );
      
      const hasExistingPdf = existingPdfFiles.length > 0;
      const hasExistingImg = existingImageFiles.length > 0;

      if ((hasExistingPdf && isImg) || (hasExistingImg && isPdf)) {
        toast.error("Tidak boleh mencampur PDF dan gambar dalam satu unggahan");
        return;
      }

      finalFiles = [...uploadedFiles, ...fileArray];
    } else {
      finalFiles = fileArray;
    }

    finalFiles.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: "base" }));

    if (activePage === "coo") {
      if (finalFiles.length > 4) {
        toast.error("Maksimal mengunggah 4 berkas untuk COO.");
        return;
      }
      setUploadedFiles(finalFiles);
      setOcrResult(null);
      setSelectedPages([]);
      toast.success(isAppend ? `Berhasil menambahkan ${fileArray.length} berkas COO.` : `Berhasil mengunggah ${fileArray.length} berkas COO.`);
    } else if (activePage === "batch") {
      if (finalFiles.length > 50) {
        toast.error("Maksimal mengunggah 50 berkas sekaligus.");
        return;
      }
      setUploadedFiles(finalFiles);
      setOcrResult(null);
      setSelectedPages([]);
      toast.success(isAppend ? `Berhasil menambahkan ${fileArray.length} berkas batch.` : `Berhasil mengunggah ${fileArray.length} berkas batch.`);
    } else {
      // activePage === "dokumen" or "prompt"
      if (finalFiles.length > 20) {
        toast.error("Maksimal mengunggah 20 berkas sekaligus.");
        return;
      }
      setUploadedFiles(finalFiles);
      setOcrResult(null);
      setSelectedPages([]);
      if (finalFiles.length === 1) {
        toast.success(`Berhasil mengunggah ${finalFiles[0].name}`);
      } else {
        toast.success(isAppend ? `Berhasil menambahkan ${fileArray.length} berkas.` : `Berhasil mengunggah ${finalFiles.length} berkas.`);
      }
    }
  };

  const handleFileChange = (e) => {
    validateAndSetFiles(e.target.files, false);
  };

  const handleAppendFileChange = (e) => {
    validateAndSetFiles(e.target.files, true);
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
  const handleRunOcr = async (page) => {
    const pageState = pageStates[page];
    if (!pageState || pageState.uploadedFiles.length === 0) {
      toast.error("Silakan unggah dokumen terlebih dahulu.");
      return;
    }

    updatePageState(page, "isProcessing", true);
    updatePageState(page, "ocrResult", null);

    const pagesString = pageState.pageSelectionText || (pageState.selectedPages.length > 0 ? pageState.selectedPages.join(",") : "");

    // Run as batch if active page is batch, or if multiple files are uploaded (except COO which processes multiple files in a single request)
    const runAsBatch = page === "batch" || (pageState.uploadedFiles.length > 1 && page !== "coo");

    if (runAsBatch) {
      let endpoint = "";
      let params = {};

      if (page === "batch" || page === "dokumen") {
        if (activeMode === "fields") {
          endpoint = "/ocr/process/fields";
          params = { fields: fieldsList, pages: pagesString, show_only_mismatch: true };
        } else if (activeMode === "prompt") {
          endpoint = "/ocr/process/prompt";
          params = { custom_prompt: customPrompt, pages: pagesString, show_only_mismatch: true };
        } else {
          endpoint = "/ocr/process/document";
          params = { document_type: selectedDocType, pages: pagesString, show_only_mismatch: true };
        }
      } else if (page === "prompt") {
        endpoint = "/ocr/process/prompt";
        params = { custom_prompt: customPrompt, pages: pagesString, show_only_mismatch: true };
      }

      const handleProgress = (prog) => {
        updatePageState(page, "progressInfo", prog);
      };

      try {
        const result = await processBatch({
          files: pageState.uploadedFiles,
          endpoint,
          params,
          token,
          baseUrl,
          concurrencyLimit,
          onProgress: handleProgress,
          mapError: mapBackendError,
        });

        updatePageState(page, "ocrResult", result);

        if (result.batch_summary.failed_files > 0) {
          toast.error(
            `${result.batch_summary.failed_files} berkas gagal diproses.`,
            { duration: 6000 }
          );
        } else {
          toast.success(`Semua berkas dalam batch (${pageState.uploadedFiles.length} berkas) berhasil diproses!`);
        }
      } catch (err) {
        toast.error("Terjadi kegagalan saat memproses batch berkas.");
      } finally {
        updatePageState(page, "isProcessing", false);
        updatePageState(page, "progressInfo", null);
      }
    } else {
      const isCooMode = page === "coo";
      let endpoint = "";
      let params = {};

      if (page === "dokumen" || page === "batch") {
        if (activeMode === "fields") {
          endpoint = "/ocr/process/fields";
          params = { fields: fieldsList, pages: pagesString, show_only_mismatch: true };
        } else if (activeMode === "prompt") {
          endpoint = "/ocr/process/prompt";
          params = { custom_prompt: customPrompt, pages: pagesString, show_only_mismatch: true };
        } else {
          endpoint = "/ocr/process/document";
          params = { document_type: selectedDocType, pages: pagesString, show_only_mismatch: true };
        }
      } else if (page === "coo") {
        endpoint = "/ocr/process/document";
        params = { document_type: "COO", pages: pagesString, show_only_mismatch: true };
      } else if (page === "prompt") {
        endpoint = "/ocr/process/prompt";
        params = { custom_prompt: customPrompt, pages: pagesString, show_only_mismatch: true };
      }

      updatePageState(page, "progressInfo", {
        current: 1,
        total: 1,
        filename: isCooMode ? `${pageState.uploadedFiles.length} berkas COO` : pageState.uploadedFiles[0].name,
        percentage: 0,
      });

      const formData = new FormData();
      pageState.uploadedFiles.forEach((file) => {
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
        const headers = {};
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }
        const response = await fetch(`${baseUrl}${endpoint}`, {
          method: "POST",
          headers,
          body: formData,
        });

        if (!response.ok) {
          const errData = await response.json();
          const errType = errData?.detail?.error_type || errData?.error_type;
          const errMsg = errData?.detail?.message || errData?.message;
          throw new Error(mapBackendError(errType, errMsg));
        }

        const data = await response.json();
        updatePageState(page, "progressInfo", {
          current: 1,
          total: 1,
          filename: isCooMode ? `${pageState.uploadedFiles.length} berkas COO` : pageState.uploadedFiles[0].name,
          percentage: 100,
        });
        updatePageState(page, "ocrResult", data);
        toast.success(isCooMode ? "Ekstraksi berkas COO berhasil diselesaikan!" : "Ekstraksi berhasil diselesaikan!");
      } catch (err) {
        toast.error(err.message);
      } finally {
        updatePageState(page, "isProcessing", false);
        updatePageState(page, "progressInfo", null);
      }
    }
  };

  const handlePageChange = (newPage) => {
    setActivePage(newPage);
  };

  const handlePromptExampleClick = (ex) => {
    setCustomPrompt(ex.value);
    toast.success("Prompt contoh berhasil diterapkan!");
  };

  // Steps Calculator
  const getStepperStep = () => {
    return getStepperStepForPage(activePage);
  };

  // Click handler to go back to previous steps
  const handleStepClick = (targetStep) => {
    const page = activePage;
    const currentStep = getStepperStepForPage(page);
    if (targetStep >= currentStep) return;

    if (targetStep === 1) {
      updatePageState(page, "uploadedFiles", []);
      updatePageState(page, "ocrResult", null);
      updatePageState(page, "isProcessing", false);
      updatePageState(page, "progressInfo", null);
      updatePageState(page, "selectedPages", []);
      updatePageState(page, "pageSelectionText", "");
    } else if (targetStep === 2) {
      if (pageStates[page].uploadedFiles.length > 0) {
        updatePageState(page, "ocrResult", null);
        updatePageState(page, "isProcessing", false);
        updatePageState(page, "progressInfo", null);
      }
    } else if (targetStep === 3 && page === "batch") {
      if (pageStates[page].uploadedFiles.length > 0 && !pageStates[page].isProcessing) {
        handleRunOcr(page);
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
      case "settings":
        return { title: "Pengaturan", desc: "Manajemen pengguna dan sistem keamanan Satnusa AI OCR." };
      default:
        return { title: "Satnusa AI OCR", desc: "Local AI Document Extraction" };
    }
  };

  const pageInfo = getPageInfo();

  const handleStartGuidedTour = (tourId) => {
    const selectedTourId = typeof tourId === "string" ? tourId : (activePage === "dashboard" ? "dokumen" : activePage);
    startGuidedTour({
      tourId: selectedTourId,
      setActivePage,
      setUploadedFiles,
      setOcrResult,
    });
  };

  if (!token) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-[#080d1a] transition-colors duration-300">
        <Toaster position="top-right" reverseOrder={false} />
        <Login baseUrl={baseUrl} onLoginSuccess={handleLoginSuccess} />
      </div>
    );
  }

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
        isCollapsed={sidebarCollapsed}
        setIsCollapsed={setSidebarCollapsed}
        user={user}
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
          user={user}
          onLogout={handleLogout}
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
              {activePage !== "settings" && (
                <Stepper 
                  activePage={activePage}
                  currentStep={getStepperStep()}
                  onStepClick={handleStepClick}
                  isProcessing={pageStates[activePage]?.isProcessing}
                />
              )}

              {/* Action Pages Switches (rendered with CSS visibility toggles to keep each tab's state & DocumentPreviewer alive) */}
              <div className={activePage === "dokumen" ? "block" : "hidden"}>
                <DokumenExtractor
                  {...getPropsForPage("dokumen")}
                  docTypes={docTypes}
                  selectedDocType={selectedDocType}
                  setSelectedDocType={setSelectedDocType}
                />
              </div>

              <div className={activePage === "coo" ? "block" : "hidden"}>
                <CooExtractor
                  {...getPropsForPage("coo")}
                />
              </div>

              <div className={activePage === "batch" ? "block" : "hidden"}>
                <BatchExtractor
                  {...getPropsForPage("batch")}
                  docTypes={docTypes}
                  selectedDocType={selectedDocType}
                  setSelectedDocType={setSelectedDocType}
                  concurrencyLimit={concurrencyLimit}
                  setConcurrencyLimit={setConcurrencyLimit}
                />
              </div>

              <div className={activePage === "prompt" ? "block" : "hidden"}>
                <CustomPromptExtractor
                  {...getPropsForPage("prompt")}
                  handlePromptExampleClick={handlePromptExampleClick}
                />
              </div>

              <div className={activePage === "settings" ? "block" : "hidden"}>
                {user?.role === "admin" && (
                  <Settings baseUrl={baseUrl} token={token} currentUser={user} />
                )}
              </div>
            </div>
          )}
        </main>

        {/* Footer */}
        <footer className="py-3 px-6 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0f172a] text-center text-[10px] text-slate-400 dark:text-slate-500 transition-colors duration-300">
          <p>© {new Date().getFullYear()} Powered by DIT Department Versi 1.0.0</p>
        </footer>
      </div>
    </div>
  );
}
