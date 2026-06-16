import React from "react";
import DocumentPreviewer from "./DocumentPreviewer";
import ResultViewer from "./ResultViewer";

export default function CooExtractor({
  currentStep,
  uploadedFiles,
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
            className="border-2 border-dashed border-slate-250 dark:border-slate-750 p-12 rounded-2xl flex flex-col items-center justify-center text-center group hover:border-emerald-500 dark:hover:border-emerald-500 transition-all cursor-pointer bg-white dark:bg-slate-900/40 relative overflow-hidden h-[300px]"
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
            <div className="w-14 h-14 bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600 dark:text-emerald-400 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <span className="material-symbols-outlined text-[32px]">upload_file</span>
            </div>
            <h4 className="font-bold text-slate-800 dark:text-slate-100 text-sm mb-1">
              Seret & lepas berkas COO di sini
            </h4>
            <p className="text-[11px] text-slate-400 mb-4">atau klik untuk memilih beberapa berkas (maks. 4)</p>
            <button className="bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2 rounded-xl text-xs font-semibold transition-colors shadow-sm cursor-pointer">
              Pilih Berkas COO
            </button>
            <span className="text-[10px] text-slate-400 mt-3">Maksimal 4 berkas: PEB, BL, PL, Invoice COO</span>
          </div>
        </div>

        <div className="col-span-12 lg:col-span-4">
          <div className="bg-emerald-50/30 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm space-y-4">
            <h4 className="font-bold text-slate-850 dark:text-slate-105 text-xs uppercase tracking-wider flex items-center gap-2">
              <span className="material-symbols-outlined text-emerald-500 text-[18px]">lightbulb</span>
              Panduan COO
            </h4>
            <ul className="space-y-3">
              {[
                "Gunakan file template resmi USER TEMPLATE.XLSX untuk hasil terbaik.",
                "Unggah dokumen pendukung lengkap (PEB, BL, PL, INV).",
                "Nama berkas disarankan mengandung kata kunci: BL, PEB, PL, INV.",
                "Unduh hasil langsung dalam format template excel resmi."
              ].map((tip, idx) => (
                <li key={idx} className="flex gap-2 text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  <span className="text-emerald-500 shrink-0 font-bold">•</span>
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
        {/* Col 1: Uploaded Files List */}
        <div className="col-span-12 lg:col-span-3 space-y-4">
          <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm space-y-3">
            <h4 className="font-bold text-slate-800 dark:text-slate-200 text-xs border-b border-slate-100 dark:border-slate-800 pb-2">
              Berkas COO ({uploadedFiles.length})
            </h4>
            <div className="space-y-2 max-h-[180px] overflow-y-auto custom-scrollbar">
              {uploadedFiles.map((file, idx) => (
                <div key={idx} className="flex items-center justify-between p-2 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/20 text-xs">
                  <span className="truncate max-w-[120px] font-medium text-slate-700 dark:text-slate-300" title={file.name}>
                    {file.name}
                  </span>
                  <button
                    onClick={() => {
                      setUploadedFiles(uploadedFiles.filter((_, i) => i !== idx));
                    }}
                    className="material-symbols-outlined text-slate-400 hover:text-red-500 transition-colors text-[16px] cursor-pointer"
                  >
                    close
                  </button>
                </div>
              ))}
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => document.getElementById("file-input").click()}
                className="flex-1 flex items-center justify-center gap-1 py-1.5 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 font-semibold rounded-lg text-xs hover:border-emerald-500 hover:text-emerald-600 transition-all cursor-pointer bg-slate-50/50 dark:bg-slate-900 shadow-sm"
              >
                Tambah
              </button>
              <button
                onClick={() => { setUploadedFiles([]); setOcrResult(null); }}
                className="flex items-center justify-center py-1.5 px-3 bg-red-50 hover:bg-red-100 dark:bg-red-950/20 dark:hover:bg-red-950/30 text-red-600 dark:text-red-400 border border-red-150 dark:border-red-900/50 rounded-lg text-xs transition-all cursor-pointer shadow-sm font-semibold"
              >
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
        </div>

        {/* Col 2: Configuration */}
        <div className="col-span-12 lg:col-span-3 space-y-4">
          <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm space-y-4">
            <h3 className="text-xs font-bold text-slate-455 uppercase tracking-widest pb-1 border-b border-slate-100 dark:border-slate-850">
              Konfigurasi COO
            </h3>

            <div className="space-y-3">
              <label className="block">
                <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 block">Tipe Dokumen</span>
                <input
                  type="text"
                  readOnly
                  value="COO"
                  className="w-full bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 text-xs rounded-xl px-3.5 py-2.5 outline-none cursor-not-allowed font-bold"
                />
              </label>

              <label className="block">
                <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 block">Halaman (opsional)</span>
                <input
                  type="text"
                  value={pageSelectionText}
                  onChange={(e) => setPageSelectionText(e.target.value)}
                  placeholder="Contoh: 1,2,3-5"
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-250 dark:border-slate-750 text-slate-800 dark:text-slate-100 text-xs rounded-xl px-3.5 py-2.5 outline-none focus:border-emerald-500 transition-colors"
                />
              </label>

              <div className="pt-2 pb-1 border-t border-slate-100 dark:border-slate-850">
                <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2.5 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[18px] text-emerald-500">folder_open</span>
                  Folder Penyimpanan (Opsional)
                </span>
                {directoryHandle ? (
                  <div className="flex items-center justify-between p-2.5 bg-slate-50 dark:bg-slate-955 rounded-xl border border-slate-200 dark:border-slate-800 text-xs">
                    <span className="truncate max-w-[130px] font-medium text-slate-700 dark:text-slate-300" title={directoryHandle.name}>
                      📂 {directoryHandle.name}
                    </span>
                    <button
                      type="button"
                      onClick={onSelectDirectory}
                      className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 hover:text-emerald-750 transition-colors cursor-pointer shrink-0"
                    >
                      Ubah
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={onSelectDirectory}
                    className="w-full flex items-center justify-center gap-1.5 border border-dashed border-slate-250 dark:border-slate-750 hover:border-emerald-500 hover:text-emerald-600 dark:hover:text-emerald-400 font-semibold py-2 px-3 rounded-xl text-xs transition-all cursor-pointer bg-slate-50/50 dark:bg-slate-900/40"
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
              className="w-full mt-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-200 disabled:dark:bg-slate-800 disabled:text-slate-400 text-white rounded-xl text-xs font-semibold transition-colors shadow-sm cursor-pointer flex items-center justify-center gap-1.5"
            >
              <span>Mulai Ekstraksi</span>
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
          />
        </div>

        {/* Col 4: Tips */}
        <div className="col-span-12 lg:col-span-2">
          <div className="bg-emerald-50/30 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm space-y-3">
            <h4 className="font-bold text-slate-850 dark:text-slate-200 text-[11px] uppercase tracking-wider">Masing-Masing</h4>
            <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-normal">
              Pastikan 4 berkas diunggah: BL, PEB, PL, INV. OCR akan menggabungkan data secara otomatis.
            </p>
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
          activeMode="doc-type"
          selectedDocType="COO"
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
        />
      </div>
    </div>
  );
}
