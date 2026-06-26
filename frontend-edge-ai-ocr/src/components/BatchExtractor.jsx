import React, { useState } from "react";
import ResultViewer from "./ResultViewer";
import DocumentPreviewer from "./DocumentPreviewer";

export default function BatchExtractor({
  currentStep,
  uploadedFiles,
  setUploadedFiles,
  docTypes,
  selectedDocType,
  setSelectedDocType,
  pageSelectionText,
  setPageSelectionText,
  concurrencyLimit,
  setConcurrencyLimit,
  isServiceReady,
  handleRunOcr,
  handleFileChange,
  ocrResult,
  setOcrResult,
  directoryHandle,
  isProcessing,
  progressInfo,
  handleDragOver,
  handleDrop,
  onSelectDirectory,
  activeMode,
  setActiveMode,
  fieldsList,
  setFieldsList,
  customPrompt,
  setCustomPrompt,
  selectedPages,
  setSelectedPages,
  handleAppendFileChange,
}) {
  const [newField, setNewField] = useState("");

  const handleAddField = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const val = newField.trim().toLowerCase().replace(/\s+/g, "_");
      if (val && !fieldsList.includes(val)) {
        setFieldsList([...fieldsList, val]);
      }
      setNewField("");
    }
  };

  const handleRemoveField = (fieldToRemove) => {
    setFieldsList(fieldsList.filter((f) => f !== fieldToRemove));
  };
  if (currentStep === 1) {
    return (
      <div className="grid grid-cols-12 gap-6 max-w-5xl mx-auto">
        <div className="col-span-12 lg:col-span-8">
          <div 
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onClick={() => document.getElementById("batch-file-input").click()}
            className="border-2 border-dashed border-slate-200 dark:border-slate-700 p-12 rounded-2xl flex flex-col items-center justify-center text-center group hover:border-purple-500 dark:hover:border-purple-500 transition-all cursor-pointer bg-white dark:bg-slate-900/40 relative overflow-hidden h-[300px]"
            id="upload-zone-container"
          >
            <input
              type="file"
              id="batch-file-input"
              multiple
              accept=".pdf, image/*"
              onChange={handleFileChange}
              className="hidden"
            />
            <div className="w-14 h-14 bg-purple-50 dark:bg-purple-950/20 text-purple-600 dark:text-purple-400 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <span className="material-symbols-outlined text-[32px]">upload_file</span>
            </div>
            <h4 className="font-bold text-slate-800 dark:text-slate-100 text-sm mb-1">
              Seret & lepas beberapa berkas di sini
            </h4>
            <p className="text-[11px] text-slate-400 mb-4">atau klik untuk memilih berkas batch</p>
            <button className="bg-purple-600 hover:bg-purple-700 text-white px-5 py-2 rounded-xl text-xs font-semibold transition-colors shadow-sm cursor-pointer">
              Pilih Berkas Batch
            </button>
            <span className="text-[10px] text-slate-400 mt-3">Maksimal 50 berkas per batch • PDF/Gambar</span>
          </div>
        </div>

        <div className="col-span-12 lg:col-span-4">
          <div className="bg-purple-50/30 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm space-y-4">
            <h4 className="font-bold text-slate-800 dark:text-slate-100 text-xs uppercase tracking-wider flex items-center gap-2">
              <span className="material-symbols-outlined text-purple-500 text-[18px]">lightbulb</span>
              Panduan Batch
            </h4>
            <ul className="space-y-3">
              {[
                "Disarankan menggunakan concurrency 3-5 untuk performa optimal.",
                "Semua berkas akan diproses paralel dan digabungkan menjadi satu output.",
                "Pastikan jenis tipe dokumen sama untuk hasil yang seragam."
              ].map((tip, idx) => (
                <li key={idx} className="flex gap-2 text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  <span className="text-purple-500 shrink-0 font-bold">•</span>
                  <span>{tip}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    );
  }

  if (currentStep === 2) {
    return (
      <div className="grid grid-cols-12 gap-6 items-start" id="extraction-config-container">
        {/* Col 1: Uploaded list (Scrollable) */}
        <div className="col-span-12 md:col-span-4 space-y-4">
          <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-4 flex flex-col h-[300px]">
            <h4 className="font-bold text-slate-800 dark:text-slate-200 text-xs border-b border-slate-100 dark:border-slate-800 pb-2 flex justify-between items-center">
              <span>File yang diunggah ({uploadedFiles.length})</span>
              {uploadedFiles.length > 0 && (
                <button 
                  onClick={() => setUploadedFiles([])}
                  className="text-xs text-red-500 hover:text-red-600 font-semibold cursor-pointer"
                >
                  Hapus Semua
                </button>
              )}
            </h4>
            <div className="flex-1 overflow-y-auto custom-scrollbar space-y-2 pr-1">
              {uploadedFiles.map((file, idx) => {
                const isPdf = file.type === "application/pdf" || /\.pdf$/i.test(file.name);
                return (
                  <div key={idx} className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/20 group hover:border-purple-500/25 dark:hover:border-purple-500/25 transition-all text-xs">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className={`material-symbols-outlined shrink-0 text-[18px] ${isPdf ? "text-red-500" : "text-blue-500"}`}>
                        {isPdf ? "picture_as_pdf" : "image"}
                      </span>
                      <div className="min-w-0">
                        <p className="font-semibold text-slate-700 dark:text-slate-200 truncate max-w-[130px]" title={file.name}>
                          {file.name}
                        </p>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          {(file.size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        setUploadedFiles(uploadedFiles.filter((_, i) => i !== idx));
                      }}
                      className="material-symbols-outlined text-slate-400 hover:text-red-500 transition-colors text-[16px] cursor-pointer"
                    >
                      close
                    </button>
                  </div>
                );
              })}
            </div>
            <button
              onClick={() => document.getElementById("batch-file-input").click()}
              className="w-full py-2 border border-dashed border-slate-300 dark:border-slate-700 text-slate-500 hover:border-purple-500 hover:text-purple-600 dark:text-slate-400 text-xs font-semibold rounded-lg transition-colors cursor-pointer flex items-center justify-center gap-1.5"
            >
              <span className="material-symbols-outlined text-[16px]">add</span>
              Tambah File
            </button>
            <input
              type="file"
              id="batch-file-input"
              multiple
              accept=".pdf, image/*"
              onChange={handleAppendFileChange}
              className="hidden"
            />
          </div>

          {activeMode === "prompt" && (
            <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm space-y-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Template Cepat</span>
              <div className="flex flex-col gap-2">
                {[
                  { label: "Data Supplier", value: "Ekstrak nama supplier, alamat, nomor telepon, email, tanggal invoice, nomor invoice, total amount, dan items dari dokumen ini." },
                  { label: "Tabel Produk", value: "Ekstrak semua tabel produk yang ada di dalam dokumen ini, termasuk nama produk, jumlah (quantity), harga satuan, dan total harga." },
                  { label: "Faktur Singkat", value: "Temukan dan ekstrak nomor faktur, tanggal faktur, tanggal jatuh tempo, dan nomor referensi pemesanan (PO)." }
                ].map((ex, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setCustomPrompt(ex.value)}
                    className="w-full text-left p-2.5 bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 hover:border-purple-500 rounded-lg text-[11px] font-semibold text-slate-600 dark:text-slate-400 transition-colors shadow-sm truncate cursor-pointer"
                  >
                    {ex.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Col 2: Configuration */}
        <div className="col-span-12 md:col-span-4 space-y-4">
          <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm space-y-4">
            <h3 className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest pb-1 border-b border-slate-100 dark:border-slate-800">
              Konfigurasi Batch
            </h3>

            {/* Sub-mode Selector: Document Type, Custom Fields, or Custom Prompt */}
            <div className="bg-slate-100 dark:bg-slate-950 p-1 rounded-xl flex gap-1 border border-slate-200 dark:border-slate-800">
              {[
                { id: "doc-type", label: "Tipe Dokumen" },
                { id: "fields", label: "Custom Fields" },
                { id: "prompt", label: "Custom Prompt" },
              ].map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setActiveMode(m.id)}
                  className={`flex-1 text-[10px] py-1.5 rounded-lg font-bold transition-all cursor-pointer ${
                    activeMode === m.id
                      ? "bg-white dark:bg-slate-800 text-purple-650 dark:text-purple-400 shadow-sm"
                      : "text-slate-400 hover:bg-white/50 dark:hover:bg-slate-900/50"
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>

            <div className="space-y-3">
              {activeMode === "doc-type" && (
                <label className="block">
                  <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 block">Tipe Dokumen</span>
                  <select
                    value={selectedDocType}
                    onChange={(e) => setSelectedDocType(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-100 text-xs rounded-xl px-3.5 py-2.5 outline-none focus:border-purple-500 transition-colors"
                  >
                    {docTypes.map((type) => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                </label>
              )}

              {activeMode === "fields" && (
                <div className="space-y-3">
                  <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 block">
                    Target Data (Tekan Enter)
                  </span>
                  <div className="flex flex-wrap gap-1.5 p-2 bg-slate-50 dark:bg-slate-900 border border-dashed border-slate-200 dark:border-slate-700 rounded-xl min-h-[90px] items-center">
                    {fieldsList.map((field) => (
                      <span
                        key={field}
                        className="bg-purple-50 dark:bg-purple-950/30 text-purple-650 dark:text-purple-400 px-2 py-0.5 rounded-md text-[10px] flex items-center gap-1 font-bold"
                      >
                        {field}
                        <button
                          type="button"
                          onClick={() => handleRemoveField(field)}
                          className="material-symbols-outlined text-[12px] cursor-pointer hover:text-red-500 font-bold"
                        >
                          close
                        </button>
                      </span>
                    ))}
                    <input
                      type="text"
                      value={newField}
                      onChange={(e) => setNewField(e.target.value)}
                      onKeyDown={handleAddField}
                      className="bg-transparent border-none text-xs w-24 py-0.5 dark:text-slate-100 outline-none focus:ring-0 focus:outline-none"
                      placeholder="+ Tambah Field"
                    />
                  </div>
                  <p className="text-[10px] text-slate-400 leading-normal block">
                    * Target data akan otomatis dikonversi ke snake_case.
                  </p>
                </div>
              )}

              {activeMode === "prompt" && (
                <label className="block">
                  <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 block">Masukan instruksi untuk AI</span>
                  <textarea
                    value={customPrompt}
                    onChange={(e) => setCustomPrompt(e.target.value)}
                    maxLength={2000}
                    className="w-full font-data-mono text-data-mono bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-100 text-xs rounded-xl p-3 outline-none focus:border-purple-500 transition-colors resize-none"
                    rows="5"
                    placeholder="Tulis instruksi ekstraksi di sini..."
                  />
                  <span className="text-[10px] text-slate-400 mt-1 block text-right leading-none">
                    {customPrompt.length}/2000
                  </span>
                </label>
              )}

              <label className="block">
                <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 block">Halaman (opsional)</span>
                <input
                  type="text"
                  value={pageSelectionText}
                  onChange={(e) => setPageSelectionText(e.target.value)}
                  placeholder="Contoh: 1,2,3-5"
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-100 text-xs rounded-xl px-3.5 py-2.5 outline-none focus:border-purple-500 transition-colors"
                />
              </label>

              <label className="block">
                <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 block">Concurrency (Proses Paralel)</span>
                <select
                  value={concurrencyLimit}
                  onChange={(e) => setConcurrencyLimit(parseInt(e.target.value))}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-100 text-xs rounded-xl px-3.5 py-2.5 outline-none focus:border-purple-500 transition-colors"
                >
                  {[1, 2, 3, 4, 5].map((val) => (
                    <option key={val} value={val}>{val === 3 ? `${val} (Direkomendasikan)` : val}</option>
                  ))}
                </select>
              </label>

              <div className="pt-2 pb-1 border-t border-slate-100 dark:border-slate-800">
                <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2.5 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[18px] text-purple-500">folder_open</span>
                  Folder Penyimpanan (Opsional)
                </span>
                {directoryHandle ? (
                  <div className="flex items-center justify-between p-2.5 bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 text-xs">
                    <span className="truncate max-w-[130px] font-medium text-slate-700 dark:text-slate-300" title={directoryHandle.name}>
                      📂 {directoryHandle.name}
                    </span>
                    <button
                      type="button"
                      onClick={onSelectDirectory}
                      className="text-[10px] font-bold text-purple-600 dark:text-purple-400 hover:text-purple-750 transition-colors cursor-pointer shrink-0"
                    >
                      Ubah
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={onSelectDirectory}
                    className="w-full flex items-center justify-center gap-1.5 border border-dashed border-slate-200 dark:border-slate-700 hover:border-purple-500 hover:text-purple-600 dark:hover:text-purple-400 font-semibold py-2 px-3 rounded-xl text-xs transition-all cursor-pointer bg-slate-50/50 dark:bg-slate-900/40"
                  >
                    <span className="material-symbols-outlined text-[16px]">create_new_folder</span>
                    Pilih Folder
                  </button>
                )}
              </div>
            </div>

            <button
              onClick={handleRunOcr}
              disabled={!isServiceReady}
              className="w-full mt-4 py-2.5 bg-purple-600 hover:bg-purple-700 disabled:bg-slate-200 disabled:dark:bg-slate-800 disabled:text-slate-400 text-white rounded-xl text-xs font-semibold transition-colors shadow-sm cursor-pointer flex items-center justify-center gap-1.5"
            >
              <span>Mulai Proses</span>
              <span className="material-symbols-outlined text-[16px]">play_arrow</span>
            </button>
          </div>
        </div>

        {/* Col 3: Preview */}
        <div className="col-span-12 md:col-span-4">
          <DocumentPreviewer
            files={uploadedFiles}
            selectedPages={selectedPages}
            onPagesChange={setSelectedPages}
            showPageSelector={false}
            ocrResult={ocrResult}
          />
        </div>
      </div>
    );
  }

  if (currentStep === 3) {
    // Step 3: Proses running
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg mx-auto shadow-sm space-y-6 min-h-[350px]">
        <div className="relative w-16 h-16 flex items-center justify-center">
          <div className="absolute inset-0 rounded-full border-4 border-purple-500/10 animate-pulse"></div>
          <div className="absolute inset-0 rounded-full border-4 border-purple-600 border-t-transparent animate-spin"></div>
          <span className="material-symbols-outlined text-purple-600 dark:text-purple-400 text-[28px] animate-pulse">
            sync_saved_locally
          </span>
        </div>
        <div className="text-center space-y-2">
          <h4 className="font-bold text-slate-800 dark:text-slate-100 text-sm">
            Pemrosesan Batch Sedang Berjalan
          </h4>
          <p className="text-xs text-slate-400 truncate max-w-[350px] mx-auto font-mono">
            📁 {progressInfo?.filename || "Menghubungi server..."}
          </p>
        </div>

        <div className="w-full space-y-2">
          <div className="flex justify-between text-[11px] font-bold text-slate-500">
            <span>Progress Batch ({progressInfo?.current || 0}/{progressInfo?.total || uploadedFiles.length})</span>
            <span>{progressInfo?.percentage || 0}%</span>
          </div>
          <div className="progress-track">
            <div
              className="progress-bar-purple"
              style={{ width: `${progressInfo?.percentage || 0}%` }}
            />
          </div>
        </div>
        <p className="text-[10px] text-slate-400 italic text-center">
          Mohon jangan menutup halaman ini selama proses ekstraksi batch berlangsung.
        </p>
      </div>
    );
  }

  // Step 4: Hasil view
  return (
    <div className="bg-white dark:bg-inverse-surface border border-border-subtle dark:border-outline-variant rounded-2xl shadow-sm flex flex-col h-[750px] lg:h-[calc(100vh-10rem)] min-h-[600px] transition-colors duration-300 overflow-hidden" id="batch-results-unified-card">
      {/* Unified Card Header */}
      <div className="px-6 py-4 border-b border-border-subtle dark:border-outline-variant flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-surface-ice dark:bg-on-surface-variant/5 select-none">
        <div>
          <h3 className="font-bold text-slate-850 dark:text-slate-100 text-sm flex items-center gap-2">
            <span className="material-symbols-outlined text-purple-650 dark:text-purple-400">task</span>
            Hasil Ekstraksi & Pratinjau Batch
          </h3>
          <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">
            Tinjau data JSON yang terekstraksi berdampingan dengan pratinjau dokumen PDF/Gambar.
          </p>
        </div>

        {/* Mini Stats Summary */}
        <div className="flex gap-2 shrink-0">
          <span className="px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600 dark:text-emerald-400 font-bold text-[10px] flex items-center gap-1 border border-emerald-100/50 dark:border-emerald-950/50">
            <span className="material-symbols-outlined text-[13px]">check_circle</span>
            <span>{(ocrResult?.batch_summary?.processed_files ?? 0) - (ocrResult?.batch_summary?.failed_files ?? 0)} Sukses</span>
          </span>
          {ocrResult?.batch_summary?.failed_files > 0 && (
            <span className="px-2.5 py-1 rounded-full bg-red-50 dark:bg-red-950/20 text-red-650 dark:text-red-400 font-bold text-[10px] flex items-center gap-1 border border-red-100/50 dark:border-red-950/50">
              <span className="material-symbols-outlined text-[13px]">cancel</span>
              <span>{ocrResult.batch_summary.failed_files} Gagal</span>
            </span>
          )}
        </div>
      </div>

      {/* Card Content - 3 Panels Horizontal Layout on Large Screens */}
      <div className="flex-1 flex flex-col lg:flex-row min-h-0 divide-y lg:divide-y-0 lg:divide-x divide-border-subtle dark:divide-outline-variant overflow-hidden">
        {/* Panel 1: Hasil Log Batch Sidebar */}
        <div className="w-full lg:w-64 bg-slate-50/50 dark:bg-slate-900/10 flex flex-col shrink-0 min-h-[150px] lg:min-h-0 select-none">
          <div className="px-4 py-3 border-b border-border-subtle dark:border-outline-variant bg-slate-150/40 dark:bg-slate-900/30 flex items-center justify-between shrink-0">
            <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Daftar Berkas ({uploadedFiles.length})</span>
          </div>
          <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2 max-h-[160px] lg:max-h-none">
            {uploadedFiles.map((file, idx) => {
              const isFailed = ocrResult?.batch_summary?.failures?.some(f => f.startsWith(file.name));
              return (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 rounded-lg border border-slate-200/60 dark:border-slate-800 bg-white dark:bg-slate-950/20 text-xs shadow-xs hover:border-purple-500/25 dark:hover:border-purple-500/25 transition-all"
                >
                  <span className="truncate max-w-[130px] font-medium text-slate-650 dark:text-slate-350" title={file.name}>
                    {file.name}
                  </span>
                  <span className={`flex items-center gap-1 font-bold shrink-0 ${isFailed ? "text-red-500" : "text-emerald-500"}`}>
                    <span className="material-symbols-outlined text-[14px]">
                      {isFailed ? "cancel" : "check_circle"}
                    </span>
                    <span className="text-[10px]">{isFailed ? "Gagal" : "Sukses"}</span>
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Panel 2: ResultViewer (Embedded) */}
        <div className="flex-1 flex flex-col min-h-0 min-w-0">
          <ResultViewer
            ocrResult={ocrResult}
            setOcrResult={setOcrResult}
            activeMode={activeMode}
            selectedDocType={selectedDocType}
            directoryHandle={directoryHandle}
            uploadedFiles={uploadedFiles}
            isProcessing={isProcessing}
            progressInfo={progressInfo}
            isEmbedded={true}
          />
        </div>

        {/* Panel 3: DocumentPreviewer (Embedded) */}
        <div className="flex-1 flex flex-col min-h-0 min-w-0">
          <DocumentPreviewer
            files={uploadedFiles}
            selectedPages={selectedPages}
            onPagesChange={setSelectedPages}
            showPageSelector={false}
            ocrResult={ocrResult}
            isEmbedded={true}
          />
        </div>
      </div>
    </div>
  );
}
