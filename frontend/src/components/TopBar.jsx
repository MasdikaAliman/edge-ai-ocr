import React from "react";

export default function TopBar({
  pageTitle,
  pageDesc,
  isServiceReady,
  theme,
  toggleTheme,
  startGuidedTour,
}) {
  return (
    <header className="h-16 flex items-center justify-between px-8 bg-white dark:bg-[#0f172a] border-b border-slate-200 dark:border-slate-800 transition-colors duration-300">
      <div className="space-y-0.5">
        <h1 className="text-md font-bold text-slate-800 dark:text-slate-100 leading-tight">
          {pageTitle}
        </h1>
        <p className="text-xs text-slate-400 truncate max-w-[500px]">
          {pageDesc}
        </p>
      </div>

      <div className="flex items-center gap-4">
        {/* Topbar Service Status */}
        <div 
          className="hidden sm:flex flex-col text-right items-end justify-center"
          id="health-indicator-top"
        >
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${isServiceReady ? "bg-emerald-500 animate-pulse" : "bg-red-500 animate-ping"}`} />
            <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              API Server
            </span>
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${isServiceReady ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400" : "bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-400"}`}>
              {isServiceReady ? "Online" : "Offline"}
            </span>
          </div>
        </div>

        {/* Panduan Outline Button */}
        <button
          onClick={startGuidedTour}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-900 hover:text-blue-600 dark:hover:text-blue-400 transition-all font-semibold text-xs cursor-pointer"
        >
          <span className="material-symbols-outlined text-[16px]">book</span>
          <span>Panduan</span>
        </button>

        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          className="relative w-12 h-6 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 transition-colors duration-500 focus:outline-none overflow-hidden cursor-pointer"
          id="theme-toggle"
          title="Ubah Tema"
        >
          <div
            className={`absolute top-0.5 left-0.5 w-4.5 h-4.5 flex items-center justify-center transition-transform duration-500 ease-in-out pointer-events-none transform ${
              theme === "dark" ? "translate-x-[24px]" : "translate-x-0"
            }`}
          >
            {theme === "light" ? (
              <span className="material-symbols-outlined text-orange-500 text-[14px]">light_mode</span>
            ) : (
              <span className="material-symbols-outlined text-blue-300 text-[14px]">dark_mode</span>
            )}
          </div>
        </button>
      </div>
    </header>
  );
}
