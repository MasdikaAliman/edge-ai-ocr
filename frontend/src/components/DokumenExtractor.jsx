import React, { useState } from "react";
import DocumentPreviewer from "./DocumentPreviewer";
import ResultViewer from "./ResultViewer";

export default function DokumenExtractor({
  currentStep,
  uploadedFiles,
  docTypes,
  selectedDocType,
  setSelectedDocType,
  pageSelectionText,
  setPageSelectionText,
  isServiceReady,
  handleRunOcr,
  handleFileChange,
  setUploadedFiles,
  setOcrResult,
  selectedPages,
  setSelectedPages,
  ocrResult,
  directoryHandle,
  isProcessing,
  progressInfo,
  handleDragOver,
  handleDrop,
  activeMode,
  setActiveMode,

  onSelectDirectory,
}) {


  if (currentStep === 1) {
    return (
      <div className="grid grid-cols-12 gap-6 max-w-5xl mx-auto">
        <div className="col-span-12 lg:col-span-8">
          <div 
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onClick={() => document.getElementById("file-input").click()}
            className="border-2 border-dashed border-slate-200 dark:border-slate-700 p-12 rounded-2xl flex flex-col items-center justify-center text-center group hover:border-blue-500 dark:hover:border-blue-500 transition-all cursor-pointer bg-white dark:bg-slate-900/40 relative overflow-hidden h-[300px]"
            id="upload-zone-container"
          >
            <input
              type="file"
              id="file-input"
              accept=".pdf, image/*"
              onChange={handleFileChange}
              className="hidden"
            />
            <div className="w-14 h-14 bg-blue-50 dark:bg-blue-950/20 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <span className="material-symbols-outlined text-[32px]">upload_file</span>
            </div>
            <h4 className="font-bold text-slate-800 dark:text-slate-100 text-sm mb-1">
              Seret & lepas file di sini
            </h4>
            <p className="text-[11px] text-slate-400 mb-4">atau klik untuk menelusuri folder</p>
            <button className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-xl text-xs font-semibold transition-colors shadow-sm cursor-pointer">
              Pilih File
            </button>
            <span className="text-[10px] text-slate-400 mt-3">PDF, JPG, PNG • Maks. 50MB</span>
          </div>

        </div>

        <div className="col-span-12 lg:col-span-4">
          <div className="bg-blue-50/30 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm space-y-4">
            <h4 className="font-bold text-slate-800 dark:text-slate-100 text-xs uppercase tracking-wider flex items-center gap-2">
              <span className="material-symbols-outlined text-blue-500 text-[18px]">lightbulb</span>
              Tips Penggunaan
            </h4>
            <ul className="space-y-3">
              {[
                "Gunakan file dengan kualitas yang jelas untuk hasil terbaik.",
                "Untuk PDF multi-halaman, tentukan halaman yang ingin diekstrak.",
                "Aktifkan OCR Reprocess jika hasil kurang lengkap."
              ].map((tip, idx) => (
                <li key={idx} className="flex gap-2 text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  <span className="text-blue-500 shrink-0 font-bold">•</span>
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
        {/* Col 1: Uploaded File Info */}
        <div className="col-span-12 lg:col-span-3 space-y-4">
          <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-blue-50 dark:bg-blue-950/20 text-blue-600 dark:text-blue-400 rounded-lg flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-[24px]">
                  {uploadedFiles[0]?.type === "application/pdf" || /\.pdf$/i.test(uploadedFiles[0]?.name) ? "picture_as_pdf" : "image"}
                </span>
              </div>
              <div className="min-w-0">
                <h5 className="text-xs font-bold text-slate-700 dark:text-slate-200 truncate" title={uploadedFiles[0]?.name}>
                  {uploadedFiles[0]?.name}
                </h5>
                <p className="text-[10px] text-slate-400">
                  {uploadedFiles[0] ? `${(uploadedFiles[0].size / 1024).toFixed(1)} KB` : ""}
                </p>
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => document.getElementById("file-input").click()}
                className="flex-1 flex items-center justify-center gap-1 py-1.5 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 font-semibold rounded-lg text-xs hover:border-blue-500 hover:text-blue-600 transition-all cursor-pointer bg-slate-50/50 dark:bg-slate-900 shadow-sm"
              >
                <span className="material-symbols-outlined text-[16px]">cached</span>
                Ganti File
              </button>
              <button
                onClick={() => { setUploadedFiles([]); setOcrResult(null); }}
                className="flex items-center justify-center py-1.5 px-3 bg-red-50 hover:bg-red-100 dark:bg-red-950/20 dark:hover:bg-red-950/30 text-red-600 dark:text-red-400 border border-red-150 dark:border-red-900/50 rounded-lg text-xs transition-all cursor-pointer shadow-sm font-semibold"
              >
                <span className="material-symbols-outlined text-[16px]">delete</span>
              </button>
            </div>
            <input
              type="file"
              id="file-input"
              accept=".pdf, image/*"
              onChange={handleFileChange}
              className="hidden"
            />
          </div>
        </div>

        {/* Col 2: Configuration */}
        <div className="col-span-12 lg:col-span-3 space-y-4">
          <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm space-y-4">
            <h3 className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest pb-1 border-b border-slate-100 dark:border-slate-800">
              Konfigurasi Ekstraksi
            </h3>


            <div className="space-y-3">
                <label className="block">
                  <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 block">Tipe Dokumen</span>
                  <select
                    value={selectedDocType}
                    onChange={(e) => setSelectedDocType(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-100 text-xs rounded-xl px-3.5 py-2.5 outline-none focus:border-blue-500 transition-colors"
                  >
                    {docTypes.length === 0 ? (
                      <option>Memuat tipe dokumen...</option>
                    ) : (
                      docTypes.map((type) => (
                        <option key={type} value={type}>{type}</option>
                      ))
                    )}
                  </select>
                </label>
            

              <label className="block">
                <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 block">Halaman (opsional)</span>
                <input
                  type="text"
                  value={pageSelectionText}
                  onChange={(e) => setPageSelectionText(e.target.value)}
                  placeholder="Contoh: 1,2,3-5"
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-100 text-xs rounded-xl px-3.5 py-2.5 outline-none focus:border-blue-500 transition-colors"
                />
                <span className="text-[10px] text-slate-400 mt-1 block leading-tight">Kosongkan untuk semua halaman</span>
              </label>

              <div className="pt-2 pb-1 border-t border-slate-100 dark:border-slate-800">
                <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2.5 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[18px] text-blue-500">folder_open</span>
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
                      className="text-[10px] font-bold text-blue-600 dark:text-blue-400 hover:text-blue-750 transition-colors cursor-pointer shrink-0"
                    >
                      Ubah
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={onSelectDirectory}
                    className="w-full flex items-center justify-center gap-1.5 border border-dashed border-slate-200 dark:border-slate-700 hover:border-blue-500 hover:text-blue-600 dark:hover:text-blue-400 font-semibold py-2 px-3 rounded-xl text-xs transition-all cursor-pointer bg-slate-50/50 dark:bg-slate-900/40"
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
              className="w-full mt-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-200 disabled:dark:bg-slate-800 disabled:text-slate-400 text-white rounded-xl text-xs font-semibold transition-colors shadow-sm cursor-pointer flex items-center justify-center gap-1.5"
            >
              <span>Lanjutkan ke Hasil</span>
              <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
            </button>
          </div>
        </div>

        {/* Col 3: Preview */}
        <div className="col-span-12 lg:col-span-4">
          <DocumentPreviewer
            files={uploadedFiles}
            selectedPages={selectedPages}
            onPagesChange={setSelectedPages}
            showPageSelector={false}
            ocrResult={ocrResult}
          />
        </div>

        {/* Col 4: Tips */}
        <div className="col-span-12 lg:col-span-2">
          <div className="bg-blue-50/30 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm space-y-3">
            <h4 className="font-bold text-slate-800 dark:text-slate-200 text-[11px] uppercase tracking-wider">Tips</h4>
            <ul className="space-y-2 text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
              <li>• Kualitas file yang jelas meningkatkan akurasi.</li>
              <li>• Tentukan halaman spesifik jika berkas besar.</li>
              <li>• Simpan output ke folder lokal Anda.</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  // Step 3: Hasil view
  return (
    <div className="grid grid-cols-12 gap-6 items-start">
      <div className="col-span-12 lg:col-span-6">
        <ResultViewer
          ocrResult={ocrResult}
          setOcrResult={setOcrResult}
          activeMode={activeMode}
          selectedDocType={selectedDocType}
          directoryHandle={directoryHandle}
          uploadedFiles={uploadedFiles}
          isProcessing={isProcessing}
          progressInfo={progressInfo}
        />
      </div>
      <div className="col-span-12 lg:col-span-6">
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
