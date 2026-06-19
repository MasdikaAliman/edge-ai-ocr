import React from "react";

export default function Stepper({ activePage, currentStep, onStepClick, isProcessing }) {
  const steps = activePage === "batch" 
    ? ["Unggah File", "Konfigurasi", "Proses", "Hasil"] 
    : ["Unggah File", activePage === "prompt" ? "Konfigurasi Prompt" : "Konfigurasi", "Hasil"];

  return (
    <div className="flex items-center justify-center w-full max-w-3xl mx-auto mb-6 px-4">
      {steps.map((stepName, idx) => {
        const stepNum = idx + 1;
        const isActive = currentStep === stepNum;
        const isCompleted = currentStep > stepNum;
        const isClickable = !isProcessing && stepNum < currentStep; // Allow going back to completed steps only when not processing
        const isLast = stepNum === steps.length;

        return (
          <React.Fragment key={idx}>
            <div 
              onClick={() => isClickable && onStepClick && onStepClick(stepNum)}
              className={`flex items-center gap-2.5 transition-all duration-200 ${
                isClickable 
                  ? "cursor-pointer group hover:scale-[1.03]" 
                  : "cursor-default"
              }`}
            >
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300 ${
                  isCompleted
                    ? "bg-emerald-500 text-white shadow-sm group-hover:bg-emerald-600 group-hover:shadow-md"
                    : isActive
                    ? "bg-blue-600 text-white shadow-md scale-105 ring-4 ring-blue-100 dark:ring-blue-950"
                    : "bg-slate-200 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-300 dark:border-slate-700"
                }`}
              >
                {isCompleted ? (
                  <span className="material-symbols-outlined text-xs font-bold transition-transform group-hover:scale-110">check</span>
                ) : (
                  stepNum
                )}
              </div>
              <span
                className={`text-xs font-semibold whitespace-nowrap transition-colors duration-300 ${
                  isActive
                    ? "text-blue-600 dark:text-blue-400 font-bold"
                    : isCompleted
                    ? "text-emerald-500 dark:text-emerald-400 group-hover:text-emerald-600 dark:group-hover:text-emerald-300 group-hover:underline decoration-emerald-500/30"
                    : "text-slate-400"
                }`}
              >
                {stepName}
              </span>
            </div>
            {!isLast && (
              <div
                className={`flex-1 h-[2px] mx-4 transition-all duration-500 ${
                  isCompleted ? "bg-emerald-500" : "bg-slate-200 dark:bg-slate-800"
                }`}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
