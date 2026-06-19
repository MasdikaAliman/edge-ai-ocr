/**
 * Batch processing helper that queues requests to the Edge-AI-OCR API
 * with a strict concurrency limit (default = 3).
 * It merges the results client-side as required by the PRD.
 */

export async function processBatch({
  files,
  endpoint,
  params,
  baseUrl = "http://localhost:5030",
  concurrencyLimit = 3,
  onProgress = () => {},
  mapError = null,
}) {
  const total = files.length;
  let processedCount = 0;
  const results = [];
  const failures = [];

  // Clone files array so we can shift items
  const queue = [...files];
  const activeRequests = new Set();

  return new Promise((resolve) => {
    const runNext = async () => {
      // If queue is empty and no active requests, we're done!
      if (queue.length === 0 && activeRequests.size === 0) {
        // Perform merge logic
        const mergedData = mergeResults(results);
        resolve({
          success: failures.length < total,
          batch_summary: {
            total_files: total,
            processed_files: results.length,
            failed_files: failures.length,
            failures: failures.map((f) => `${f.filename}: ${f.error}`),
          },
          extracted_data: mergedData,
          raw_results: results,
        });
        return;
      }

      // Fill up to concurrency limit
      while (queue.length > 0 && activeRequests.size < concurrencyLimit) {
        const file = queue.shift();
        const promise = (async () => {
          try {
            // Update progress for starting this file
            processedCount++;
            onProgress({
              current: processedCount,
              total,
              filename: file.name,
              percentage: Math.round(((results.length + failures.length) / total) * 100),
            });

            const formData = new FormData();
            formData.append("files", file);

            // Add other parameters
            if (params) {
              for (const [key, value] of Object.entries(params)) {
                if (Array.isArray(value)) {
                  value.forEach((v) => formData.append(key, v));
                } else if (value !== undefined && value !== null) {
                  formData.append(key, value);
                }
              }
            }

            const response = await fetch(`${baseUrl.replace(/\/$/, "")}${endpoint}`, {
              method: "POST",
              body: formData,
            });

            if (!response.ok) {
              // Extract error payload if possible
              let errorMsg = `HTTP Error ${response.status}`;
              let errorType = null;
              try {
                const errData = await response.json();
                errorType = errData?.detail?.error_type || errData?.error_type;
                const detailMsg = errData?.detail?.message || errData?.message;
                if (detailMsg) {
                  errorMsg = detailMsg;
                }
              } catch (e) {
                // Ignore parsing error, fallback to default HTTP error
              }
              if (mapError) {
                throw new Error(mapError(errorType, errorMsg));
              }
              throw new Error(errorMsg);
            }

            const data = await response.json();
            // console.log(data);
            results.push({
              filename: file.name,
              data: data,
            });
          } catch (error) {
            console.error(`Gagal memproses berkas ${file.name}:`, error);
            failures.push({
              filename: file.name,
              error: error.message || "Kesalahan tidak diketahui",
            });
          } finally {
            activeRequests.delete(promise);
            // Complete percentage update
            onProgress({
              current: Math.min(processedCount, total),
              total,
              filename: file.name,
              percentage: Math.round(((results.length + failures.length) / total) * 100),
            });
            runNext();
          }
        })();

        activeRequests.add(promise);
      }
    };

    // Kick off first round
    runNext();
  });
}

/**
 * Merge logic (PRD 4.4):
 * - Add `_source` field containing original filename to each result
 * - Combine results into an array of objects
 * - Ensure uniform structure by padding missing fields with `null`
 */
function mergeResults(results) {
  if (results.length === 0) return [];

  // Extract inner extracted_data objects and add _source
  const itemDataList = results.map((res) => {
    const rawData = res.data.data || {};
    // Ensure it's an object
    const obj = typeof rawData === "object" && !Array.isArray(rawData) ? { ...rawData } : { raw_output: rawData };
    obj._source = res.filename;
    return obj;
  });

  // Find all unique keys across all records
  const allKeys = new Set();
  itemDataList.forEach((item) => {
    Object.keys(item).forEach((key) => allKeys.add(key));
  });

  // Normalize each record so it contains all keys, with missing keys set to null
  return itemDataList.map((item) => {
    const normalized = {};
    allKeys.forEach((key) => {
      normalized[key] = item[key] !== undefined ? item[key] : null;
    });
    return normalized;
  });
}
