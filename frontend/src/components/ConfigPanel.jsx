import React, { useState } from "react";

export default function ConfigPanel({
  activeMode,
  docTypes,
  selectedDocType,
  setSelectedDocType,
  fieldsList,
  setFieldsList,
  customPrompt,
  setCustomPrompt,
  directoryHandle,
  onSelectDirectory,
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

  return (
    <div
      className="transition-colors duration-300"
      id="extraction-config-container"
    >
      <h3 className="font-label-caps text-label-caps text-secondary dark:text-secondary-fixed-dim uppercase mb-4 tracking-widest font-bold">
        Konfigurasi Ekstraksi
      </h3>

      {/* Mode: Document Type */}
      {activeMode === "doc-type" && (
        <div className="space-y-4">
          <label className="block">
            <span className="text-body-sm font-semibold text-on-surface dark:text-on-primary mb-2 block">
              Pilih Tipe Dokumen
            </span>
            <select
              value={selectedDocType}
              onChange={(e) => setSelectedDocType(e.target.value)}
              className="w-full bg-surface-ice dark:bg-on-surface-variant/10 border-outline-variant dark:border-outline text-on-surface dark:text-on-primary rounded-lg px-4 py-3 focus:ring-secondary focus:border-secondary transition-all outline-none"
            >
              {docTypes.length === 0 ? (
                <option>Memuat tipe dokumen...</option>
              ) : (
                docTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))
              )}
            </select>
          </label>
        </div>
      )}

      {/* Mode: Fields */}
      {activeMode === "fields" && (
        <div className="space-y-4">
          <span className="text-body-sm font-semibold text-on-surface dark:text-on-primary mb-2 block">
            Field yang akan diekstrak (Tekan Enter)
          </span>
          <div className="flex flex-wrap gap-2 p-3 bg-surface-ice dark:bg-on-surface-variant/10 border border-dashed border-outline-variant dark:border-outline rounded-lg min-h-[100px] items-center">
            {fieldsList.map((field) => (
              <span
                key={field}
                className="bg-secondary/10 dark:bg-secondary/30 text-secondary dark:text-primary-fixed-dim px-3 py-1 rounded-full text-body-sm flex items-center gap-2 font-medium"
              >
                {field}
                <button
                  type="button"
                  onClick={() => handleRemoveField(field)}
                  className="material-symbols-outlined text-[16px] cursor-pointer hover:text-red-500 font-bold"
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
              className="bg-transparent border-none focus:ring-0 text-body-sm w-32 py-1 dark:text-on-primary outline-none focus:outline-none"
              placeholder="+ Tambah Field"
            />
          </div>
          <p className="text-[10px] text-on-surface-variant dark:text-surface-variant italic">
            * Field akan otomatis dikonversi ke format snake_case.
          </p>
        </div>
      )}

      {/* Mode: Custom Prompt */}
      {activeMode === "custom-prompt" && (
        <div className="space-y-4">
          <label className="block">
            <span className="text-body-sm font-semibold text-on-surface dark:text-on-primary mb-2 block">
              Instruksi Ekstraksi Khusus (LLM Prompt)
            </span>
            <textarea
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              className="w-full font-data-mono text-data-mono bg-surface-ice dark:bg-on-surface-variant/10 border-outline-variant dark:border-outline text-on-surface dark:text-on-primary rounded-lg p-4 focus:ring-secondary focus:border-secondary resize-none outline-none"
              placeholder="Contoh: Ekstrak semua tabel transaksi dan ubah format tanggal ke DD/MM/YYYY..."
              rows="4"
            />
          </label>
        </div>
      )}

      {/* Folder Output Section */}
      <div className="mt-6 pt-6 border-t border-border-subtle dark:border-outline-variant">
        <span className="text-body-sm font-semibold text-on-surface dark:text-on-primary mb-2 flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px]">folder_open</span>
          Folder Penyimpanan Lokal (Opsional)
        </span>
        
        {directoryHandle ? (
          <div className="flex items-center justify-between p-3 bg-surface-ice dark:bg-on-surface-variant/10 rounded-lg border border-outline-variant dark:border-outline">
            <span className="text-body-sm font-medium text-on-surface dark:text-on-primary truncate">
              📂 {directoryHandle.name}
            </span>
            <button
              type="button"
              onClick={onSelectDirectory}
              className="text-[12px] font-semibold text-secondary hover:text-primary transition-colors cursor-pointer shrink-0 ml-2"
            >
              Ubah Folder
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={onSelectDirectory}
            className="w-full flex items-center justify-center gap-2 border border-dashed border-outline-variant dark:border-outline hover:border-secondary hover:text-secondary dark:hover:border-primary-fixed-dim text-on-surface-variant dark:text-surface-variant font-semibold py-3 px-4 rounded-lg text-body-sm transition-all cursor-pointer bg-surface-ice/30 dark:bg-transparent"
          >
            <span className="material-symbols-outlined text-[18px]">create_new_folder</span>
            Pilih Folder Tujuan
          </button>
        )}
      </div>
    </div>

  );
}
