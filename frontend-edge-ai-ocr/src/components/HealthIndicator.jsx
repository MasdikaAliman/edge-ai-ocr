import React, { useState, useEffect, useRef } from "react";

export default function HealthIndicator({ baseUrl, onStatusChange }) {
  const [status, setStatus] = useState("checking"); // checking, healthy, offline
  const [details, setDetails] = useState(null);
  const intervalRef = useRef(null);

  const checkHealth = async () => {
    try {
      const response = await fetch(`${baseUrl.replace(/\/$/, "")}/health`, {
        method: "GET",
        headers: { Accept: "application/json" },
      });
      if (response.ok) {
        const data = await response.json();
        if (data.status === "Healthy" && data.model_ready) {
          setStatus("healthy");
          setDetails(data);
          onStatusChange(true);
          return;
        }
      }
      setStatus("offline");
      setDetails(null);
      onStatusChange(false);
    } catch (error) {
      setStatus("offline");
      setDetails(null);
      onStatusChange(false);
    }
  };

  useEffect(() => {
    checkHealth(); // initial check

    intervalRef.current = setInterval(checkHealth, 30000); // poll every 30s

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [baseUrl]);

  return (
    <div className="flex items-center gap-4" id="health-indicator-container">
      <div className="h-6 w-[1px] bg-outline-variant dark:bg-outline hidden md:block"></div>
      <div className="flex items-center gap-2">
        {status === "checking" ? (
          <>
            <span className="w-2.5 h-2.5 rounded-full bg-outline animate-pulse"></span>
            <span className="font-label-caps text-label-caps text-on-surface-variant dark:text-surface-variant">Checking Service...</span>
          </>
        ) : status === "healthy" ? (
          <>
            <span className="w-2.5 h-2.5 rounded-full bg-service-ready animate-pulse"></span>
            <div className="flex flex-col">
              <span className="font-label-caps text-label-caps text-on-surface-variant dark:text-primary-fixed font-semibold">Service Ready</span>
              {/* {details && (
                <span className="text-[9px] text-on-surface-variant dark:text-surface-variant leading-none">
                  VLLM Len: {details.vllm_max_model_len}
                </span>
              )} */}
            </div>
          </>
        ) : (
          <>
            <span className="w-2.5 h-2.5 rounded-full bg-service-offline animate-ping"></span>
            <div className="flex flex-col">
              <span className="font-label-caps text-label-caps text-service-offline font-bold">Service Offline</span>
              <span className="text-[9px] text-service-offline leading-none">vLLM server unreachable</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
