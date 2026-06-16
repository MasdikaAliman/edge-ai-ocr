import React from "react";

export default function Sidebar({
  activePage,
  onPageChange,
  isServiceReady,
  startGuidedTour,
}) {
  return (
    <aside 
      className="w-64 shrink-0 h-screen flex flex-col justify-between p-5 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0f172a] transition-all duration-300"
      id="sidebar-navigation"
    >
      <div className="space-y-6">
        {/* Brand Header */}
        <div 
          onClick={() => onPageChange("dashboard")}
          className="flex items-center gap-3 cursor-pointer group pb-4 border-b border-slate-100 dark:border-slate-850"
        >
          <div className="w-10 h-10 rounded-full bg-blue-600 dark:bg-blue-500/10 flex items-center justify-center text-white dark:text-blue-400 group-hover:scale-105 transition-transform shadow-md">
            <span className="material-symbols-outlined text-[24px]">analytics</span>
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors leading-tight">Edge AI OCR</h2>
            <span className="text-[10px] text-slate-400 leading-none">Local AI Document Extraction</span>
          </div>
        </div>

        {/* Menu Items */}
        <nav className="space-y-1">
          {[
            { id: "dashboard", label: "Home", icon: "home" },
            { id: "dokumen", label: "Ekstraksi Dokumen", icon: "description" },
            { id: "coo", label: "Ekstraksi COO (Multi-Doc)", icon: "layers" },
            { id: "batch", label: "Batch Processing", icon: "grid_view" },
            { id: "prompt", label: "Custom Prompt", icon: "chat" }
          ].map((item) => {
            const isSelected = activePage === item.id;
            let selectClass = "text-slate-650 dark:text-slate-450 hover:bg-slate-100 dark:hover:bg-slate-800/40";
            
            if (isSelected) {
              if (item.id === "dashboard") selectClass = "bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 font-bold border-l-4 border-blue-600";
              if (item.id === "dokumen") selectClass = "bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 font-bold border-l-4 border-blue-600";
              if (item.id === "coo") selectClass = "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400 font-bold border-l-4 border-emerald-600";
              if (item.id === "batch") selectClass = "bg-purple-50 dark:bg-purple-950/30 text-purple-600 dark:text-purple-400 font-bold border-l-4 border-purple-600";
              if (item.id === "prompt") selectClass = "bg-orange-50 dark:bg-orange-950/30 text-orange-600 dark:text-orange-400 font-bold border-l-4 border-orange-600";
            }

            return (
              <button
                key={item.id}
                onClick={() => onPageChange(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${selectClass}`}
              >
                <span className="material-symbols-outlined text-[18px] shrink-0">{item.icon}</span>
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

      </div>

      {/* Panduan Button */}
      <button
        onClick={startGuidedTour}
        className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-650 dark:text-slate-350 hover:bg-slate-50 dark:hover:bg-slate-900 transition-all font-semibold text-xs cursor-pointer shadow-sm"
      >
        <span className="material-symbols-outlined text-[16px]">help</span>
        <span>Panduan</span>
      </button>
    </aside>
  );
}
