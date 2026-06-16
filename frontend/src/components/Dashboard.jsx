import React from "react";

export default function Dashboard({ onPageChange, startGuidedTour }) {
  return (
    <div className="w-full space-y-6 max-w-7xl mx-auto">
      <div className="grid grid-cols-12 gap-6 items-start">
        {/* Left side grid */}
        <div className="col-span-12 lg:col-span-9 space-y-6">
          <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 tracking-tight">Pilih Fitur Ekstraksi</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Card 1: Ekstraksi Dokumen */}
            <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm hover:shadow-md hover:border-blue-500/30 transition-all flex flex-col justify-between group">
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950/20 flex items-center justify-center text-blue-600 dark:text-blue-400 group-hover:scale-105 transition-transform">
                  <span className="material-symbols-outlined text-[24px]">description</span>
                </div>
                <h4 className="font-bold text-slate-800 dark:text-slate-200 text-sm">Ekstraksi Dokumen</h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  Ekstrak data dari dokumen tunggal seperti KTP, NPWP, Invoice, dan lainnya.
                </p>
              </div>
              <button 
                onClick={() => onPageChange("dokumen")}
                className="mt-5 w-full py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl transition-all cursor-pointer flex items-center justify-center gap-1 shadow-sm"
              >
                <span>Mulai Ekstraksi</span>
                <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
              </button>
            </div>

            {/* Card 2: Ekstraksi COO */}
            <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm hover:shadow-md hover:border-emerald-500/30 transition-all flex flex-col justify-between group">
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-950/20 flex items-center justify-center text-emerald-600 dark:text-emerald-400 group-hover:scale-105 transition-transform">
                  <span className="material-symbols-outlined text-[24px]">layers</span>
                </div>
                <h4 className="font-bold text-slate-800 dark:text-slate-200 text-sm">Ekstraksi COO (Multi-Doc)</h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  Ekstrak data COO dari 4 dokumen utama sekaligus: BL, PEB, PL, dan Invoice COO.
                </p>
              </div>
              <button 
                onClick={() => onPageChange("coo")}
                className="mt-5 w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl transition-all cursor-pointer flex items-center justify-center gap-1 shadow-sm"
              >
                <span>Mulai Ekstraksi</span>
                <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
              </button>
            </div>

            {/* Card 3: Batch Processing */}
            <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm hover:shadow-md hover:border-purple-500/30 transition-all flex flex-col justify-between group">
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-xl bg-purple-50 dark:bg-purple-950/20 flex items-center justify-center text-purple-600 dark:text-purple-400 group-hover:scale-105 transition-transform">
                  <span className="material-symbols-outlined text-[24px]">grid_view</span>
                </div>
                <h4 className="font-bold text-slate-800 dark:text-slate-200 text-sm">Batch Processing</h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  Proses banyak dokumen sekaligus dan gabungkan hasilnya secara efisien.
                </p>
              </div>
              <button 
                onClick={() => onPageChange("batch")}
                className="mt-5 w-full py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold rounded-xl transition-all cursor-pointer flex items-center justify-center gap-1 shadow-sm"
              >
                <span>Mulai Batch</span>
                <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
              </button>
            </div>

            {/* Card 4: Custom Prompt */}
            <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm hover:shadow-md hover:border-orange-500/30 transition-all flex flex-col justify-between group">
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-xl bg-orange-50 dark:bg-orange-950/20 flex items-center justify-center text-orange-600 dark:text-orange-400 group-hover:scale-105 transition-transform">
                  <span className="material-symbols-outlined text-[24px]">chat</span>
                </div>
                <h4 className="font-bold text-slate-800 dark:text-slate-200 text-sm">Custom Prompt</h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  Ekstraksi bebas dengan prompt kustom sesuai kebutuhan AI spesifik Anda.
                </p>
              </div>
              <button 
                onClick={() => onPageChange("prompt")}
                className="mt-5 w-full py-2 bg-orange-600 hover:bg-orange-700 text-white text-xs font-semibold rounded-xl transition-all cursor-pointer flex items-center justify-center gap-1 shadow-sm"
              >
                <span>Mulai</span>
                <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
              </button>
            </div>
          </div>

          {/* Tips notice banner */}
          <div className="bg-blue-50/50 dark:bg-blue-950/10 border border-blue-100 dark:border-blue-900/30 p-4 rounded-xl flex items-center gap-3">
            <span className="material-symbols-outlined text-blue-500 shrink-0">info</span>
            <p className="text-xs text-blue-700 dark:text-blue-300 font-medium">
              Tip: Gunakan tombol Panduan di atas atau panel kanan untuk mempelajari cara menggunakan setiap fitur.
            </p>
          </div>

          {/* Flowchart row */}
          <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 p-6 rounded-2xl shadow-sm">
            <h3 className="text-xs font-bold text-slate-440 uppercase tracking-widest mb-6 flex items-center gap-2">
              <span className="material-symbols-outlined text-[16px]">timeline</span>
              Cara Kerja Singkat
            </h3>
            <div className="flex flex-col md:flex-row items-center justify-between gap-6 md:gap-4">
              {[
                { icon: "upload_file", title: "Unggah File", desc: "Pilih dan unggah file dokumen Anda", color: "text-blue-500 bg-blue-50 dark:bg-blue-950/20" },
                { icon: "tune", title: "Konfigurasi", desc: "Atur tipe dokumen dan opsi ekstraksi", color: "text-indigo-500 bg-indigo-50 dark:bg-indigo-950/20" },
                { icon: "memory", title: "Proses", desc: "AI lokal memproses dan mengekstrak data", color: "text-emerald-500 bg-emerald-50 dark:bg-emerald-950/20" },
                { icon: "download", title: "Hasil", desc: "Lihat hasil dan ekspor ke Excel / JSON", color: "text-purple-500 bg-purple-50 dark:bg-purple-950/20" }
              ].map((fStep, idx, arr) => (
                <React.Fragment key={idx}>
                  <div className="flex flex-col items-center text-center max-w-[160px]">
                    <div className={`w-11 h-11 rounded-xl flex items-center justify-center mb-3 ${fStep.color} shadow-sm`}>
                      <span className="material-symbols-outlined text-[20px]">{fStep.icon}</span>
                    </div>
                    <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 mb-1">{fStep.title}</h4>
                    <p className="text-[10px] text-slate-400 leading-relaxed">{fStep.desc}</p>
                  </div>
                  {idx < arr.length - 1 && (
                    <span className="hidden md:block material-symbols-outlined text-slate-300 dark:text-slate-700 text-[20px]">
                      arrow_forward
                    </span>
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>

        {/* Right side guide panel */}
        <div className="col-span-12 lg:col-span-3">
          <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm space-y-4">
            <div>
              <h4 className="font-bold text-slate-800 dark:text-slate-200 text-sm">Panduan Penggunaan</h4>
              <p className="text-[11px] text-slate-450 mt-1 leading-relaxed">
                Klik fitur di bawah untuk melihat panduan langkah demi langkah.
              </p>
            </div>

            <div className="space-y-3">
              {[
                { id: "dokumen", label: "Ekstraksi Dokumen", text: "Pelajari cara mengekstrak data dari dokumen tunggal", icon: "description", iconBg: "bg-blue-50 text-blue-500 dark:bg-blue-950/30" },
                { id: "coo", label: "Ekstraksi COO (Multi-Doc)", text: "Pelajari cara mengekstrak data COO dari 4 dokumen", icon: "layers", iconBg: "bg-emerald-50 text-emerald-500 dark:bg-emerald-950/30" },
                { id: "batch", label: "Batch Processing", text: "Pelajari cara memproses banyak dokumen sekaligus", icon: "grid_view", iconBg: "bg-purple-50 text-purple-500 dark:bg-purple-950/30" },
                { id: "prompt", label: "Custom Prompt", text: "Pelajari cara menggunakan prompt kustom", icon: "chat", iconBg: "bg-orange-50 text-orange-500 dark:bg-orange-950/30" }
              ].map((item) => (
                <div
                  key={item.id}
                  onClick={() => {
                    onPageChange(item.id);
                    setTimeout(() => startGuidedTour(), 500);
                  }}
                  className="flex items-center justify-between p-3 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-transparent hover:border-slate-300 dark:hover:border-slate-700 transition-all cursor-pointer group"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${item.iconBg}`}>
                      <span className="material-symbols-outlined text-[16px]">{item.icon}</span>
                    </div>
                    <div className="min-w-0">
                      <h5 className="text-xs font-bold text-slate-700 dark:text-slate-200 truncate leading-none">{item.label}</h5>
                      <p className="text-[10px] text-slate-450 mt-1 truncate">{item.text}</p>
                    </div>
                  </div>
                  <span className="material-symbols-outlined text-slate-355 dark:text-slate-655 group-hover:translate-x-0.5 transition-transform text-[16px]">
                    chevron_right
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
