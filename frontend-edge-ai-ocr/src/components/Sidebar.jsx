import React from "react";

export default function Sidebar({
  activePage,
  onPageChange,
  isServiceReady,
  startGuidedTour,
  isCollapsed,
  setIsCollapsed,
  user,
}) {
  return (
    <aside 
      className={`shrink-0 h-screen flex flex-col justify-between border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0f172a] transition-all duration-300 ${
        isCollapsed ? "w-20" : "w-64"
      }`}
      id="sidebar-navigation"
    >
      {/* Scrollable container for branding, menu, and help button */}
      <div className="flex-1 flex flex-col justify-between p-5 overflow-y-auto custom-scrollbar">
        <div className="space-y-6">
          {/* Brand Header */}
          <div 
            onClick={() => onPageChange("dashboard")}
            className={`flex items-center gap-3 cursor-pointer group pb-4 border-b border-slate-100 dark:border-slate-800 ${
              isCollapsed ? "justify-center" : ""
            }`}
          >
            <img 
              src="/icon-ocr.svg" 
              alt="Satnusa AI OCR Logo" 
              className="w-10 h-10 rounded-xl group-hover:scale-105 transition-transform shadow-md shrink-0 object-contain"
            />
            {!isCollapsed && (
              <div className="min-w-0">
                <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors leading-tight truncate">Satnusa AI OCR</h2>
                <span className="text-[10px] text-slate-400 leading-none block truncate">Local AI Document Extraction</span>
              </div>
            )}
          </div>

          {/* Menu Items */}
          <nav className="space-y-1">
            {(() => {
              const menuItems = [
                { id: "dashboard", label: "Home", icon: "home" },
                { id: "dokumen", label: "Ekstraksi Dokumen", icon: "description" },
                { id: "coo", label: "Ekstraksi COO (Multi-Doc)", icon: "layers" },
                { id: "batch", label: "Batch Processing", icon: "grid_view" },
                { id: "prompt", label: "Custom Prompt", icon: "chat" }
              ];
              if (user?.role === "admin") {
                menuItems.push({ id: "settings", label: "Pengaturan", icon: "settings" });
              }
              return menuItems.map((item) => {
                const isSelected = activePage === item.id;
                let selectClass = "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/40";
                
                if (isSelected) {
                  if (item.id === "dashboard") selectClass = "bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 font-bold border-l-4 border-blue-600";
                  if (item.id === "dokumen") selectClass = "bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 font-bold border-l-4 border-blue-600";
                  if (item.id === "coo") selectClass = "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400 font-bold border-l-4 border-emerald-600";
                  if (item.id === "batch") selectClass = "bg-purple-50 dark:bg-purple-950/30 text-purple-600 dark:text-purple-400 font-bold border-l-4 border-purple-600";
                  if (item.id === "prompt") selectClass = "bg-orange-50 dark:bg-orange-950/30 text-orange-600 dark:text-orange-400 font-bold border-l-4 border-orange-600";
                  if (item.id === "settings") selectClass = "bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 font-bold border-l-4 border-blue-600";
                }

                return (
                  <button
                    key={item.id}
                    onClick={() => onPageChange(item.id)}
                    title={isCollapsed ? item.label : ""}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                      isCollapsed ? "justify-center" : ""
                    } ${selectClass}`}
                  >
                    <span className="material-symbols-outlined text-[18px] shrink-0">{item.icon}</span>
                    {!isCollapsed && <span className="truncate">{item.label}</span>}
                  </button>
                );
              });
            })()}
          </nav>
        </div>

        {/* Panduan Button */}
        <div className="mt-auto pt-6">
          <button
            onClick={startGuidedTour}
            title={isCollapsed ? "Panduan" : ""}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-900 transition-all font-semibold text-xs cursor-pointer shadow-sm"
          >
            <span className="material-symbols-outlined text-[16px]">help</span>
            {!isCollapsed && <span>Panduan</span>}
          </button>
        </div>
      </div>

      {/* Collapse/Expand Toggle Bar - Aligned perfectly with page footer */}
      <div 
        className={`flex items-center justify-between border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/20 px-5 py-3 transition-all duration-300 ${
          isCollapsed ? "justify-center" : ""
        }`}
      >
        {!isCollapsed && (
          <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest select-none">
            Sidebar
          </span>
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className={`flex items-center justify-center text-slate-500 hover:text-blue-600 dark:hover:text-blue-400 transition-all cursor-pointer ${
            isCollapsed ? "w-8 h-8 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm" : "w-6 h-6 hover:scale-105"
          }`}
          title={isCollapsed ? "Perbesar Sidebar" : "Ciutkan Sidebar"}
        >
          <span className="material-symbols-outlined text-[18px]">
            {isCollapsed ? "chevron_right" : "chevron_left"}
          </span>
        </button>
      </div>
    </aside>
  );
}
