import React, { useState, useEffect, useRef } from "react";

export default function TopBar({
  pageTitle,
  pageDesc,
  isServiceReady,
  theme,
  toggleTheme,
  startGuidedTour,
  user,
  onLogout,
}) {
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const profileDropdownRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (profileDropdownRef.current && !profileDropdownRef.current.contains(event.target)) {
        setIsProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);
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

        {/* Profile Dropdown */}
        {user && (
          <div className="relative" ref={profileDropdownRef}>
            <button
              onClick={() => setIsProfileOpen(!isProfileOpen)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900 transition-all cursor-pointer"
            >
              <div className="w-8 h-8 rounded-full bg-blue-600/10 text-blue-600 flex items-center justify-center font-bold text-sm select-none">
                {user.username.substring(0, 2).toUpperCase()}
              </div>
              <div className="hidden md:flex flex-col text-left">
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200 leading-none">
                  {user.username}
                </span>
                <span className="text-[9px] text-slate-400 dark:text-slate-500 font-semibold mt-0.5">
                  {user.employee} • {user.role === "admin" ? "Admin" : "User"}
                </span>
              </div>
              <span className="material-symbols-outlined text-[16px] text-slate-400">
                keyboard_arrow_down
              </span>
            </button>

            {isProfileOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-[#0f172a] border border-slate-200/60 dark:border-slate-800 rounded-2xl shadow-lg p-2 z-50 animate-in fade-in slide-in-from-top-1 duration-200">
                <div className="px-3 py-2 border-b border-slate-100 dark:border-slate-800 mb-1">
                  <p className="text-xs font-bold text-slate-800 dark:text-slate-200 mt-1 truncate">{user.username}</p>
                  <p className="text-[10px] text-slate-500 truncate">{user.employee}</p>
                </div>
                <button
                  onClick={() => {
                    setIsProfileOpen(false);
                    onLogout();
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 rounded-xl transition-colors text-xs font-semibold text-left cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[16px]">logout</span>
                  <span>Keluar</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
