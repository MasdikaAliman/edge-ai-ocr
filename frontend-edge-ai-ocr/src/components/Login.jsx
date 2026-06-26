import React, { useState } from "react";
import toast from "react-hot-toast";

export default function Login({ baseUrl, onLoginSuccess }) {
  const [no_badge, setNoBadge] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!no_badge.trim() || !password.trim()) {
      toast.error("Nomor badge dan password tidak boleh kosong");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch(`${baseUrl}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nomor_badge: no_badge, password }),
      });

      if (!response.ok) {
        const errData = await response.json();
        const msg = errData?.detail?.message || errData?.message || "Username atau password salah.";
        throw new Error(msg);
      }

      const data = await response.json();
      toast.success(`Selamat datang kembali, ${data.user.username}!`);
      onLoginSuccess(data.access_token, data.user);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#080d1a] px-4 transition-colors duration-300 font-body-main relative overflow-hidden">
      {/* Decorative Gradients */}
      <div className="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] rounded-full bg-blue-400/20 dark:bg-blue-900/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[500px] h-[500px] rounded-full bg-purple-400/20 dark:bg-purple-900/10 blur-[120px] pointer-events-none" />

      <div className="w-full max-w-md bg-white/80 dark:bg-[#0f172a]/70 backdrop-blur-xl border border-slate-200/50 dark:border-slate-800/50 rounded-3xl p-8 shadow-2xl transition-all duration-300 relative z-10">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-50 dark:bg-blue-950/40 border border-blue-100 dark:border-blue-900/30 mb-4 shadow-sm">
            <img src="/icon-ocr.svg" alt="OCR Icon" className="w-10 h-10 object-contain" />
          </div>
          <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100 leading-tight">
            Satnusa AI OCR
          </h2>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1.5">
            Silakan login akun anda untuk mengakses ekstraksi dokumen
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-2 uppercase tracking-wider">
              Nomor Badge
            </label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 material-symbols-outlined text-[18px] text-slate-400">
                person
              </span>
              <input
                type="text"
                value={no_badge}
                onChange={(e) => setNoBadge(e.target.value)}
                placeholder="Masukkan Nomor Badge"
                className="w-full pl-11 pr-4 py-3 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50 text-xs font-semibold focus:outline-none focus:border-blue-500 dark:focus:border-blue-600 transition-colors"
                disabled={isSubmitting}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-2 uppercase tracking-wider">
              Kata Sandi
            </label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 material-symbols-outlined text-[18px] text-slate-400">
                lock
              </span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Masukkan password"
                className="w-full pl-11 pr-4 py-3 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50 text-xs font-semibold focus:outline-none focus:border-blue-500 dark:focus:border-blue-600 transition-colors"
                disabled={isSubmitting}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3.5 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition-colors flex items-center justify-center gap-2 cursor-pointer shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span>Menghubungkan...</span>
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-[16px]">login</span>
                <span>Masuk</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
