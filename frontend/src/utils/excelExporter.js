import * as XLSX from 'xlsx';

/**
 * Helper to translate raw snake_case keys into Indonesian Title Case headers.
 */
function formatHeader(key) {
  if (key === "_source" || key === "source") return "Source";
  return key
    .split(/[_\s]+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

/**
 * Automatically adjusts column widths in a worksheet based on content.
 */
function autoFitColumns(ws, rowsData) {
  if (!rowsData || rowsData.length === 0) return;

  const keys = Object.keys(rowsData[0]);
  ws["!cols"] = keys.map((key) => {
    let maxLen = key.toString().length;
    rowsData.forEach((row) => {
      const val = row[key];
      if (val !== undefined && val !== null) {
        let str = "";
        if (typeof val === "object") {
          str = JSON.stringify(val);
        } else {
          str = val.toString();
        }
        if (str.length > maxLen) {
          maxLen = str.length;
        }
      }
    });
    // Add extra padding (4 chars) and clamp width between 12 and 60
    return { wch: Math.min(Math.max(maxLen + 4, 12), 60) };
  });
}

/**
 * Generates an Excel Workbook Blob from OCR JSON data.
 * - Flat fields go to the "Ringkasan Data" sheet.
 * - Array/List fields get their own sheets (e.g., "Items", "Daftar Barang"), linked via "Sumber Berkas".
 * Handles both backend responses and batch lists.
 */
export function getExcelBlob(ocrData) {
  // Normalize input to an array of rows
  let rows = [];
  if (Array.isArray(ocrData)) {
    rows = ocrData;
  } else if (ocrData && typeof ocrData === "object") {
    // Check if it's the batch merged format
    if (ocrData.extracted_data) {
      if (Array.isArray(ocrData.extracted_data)) {
        rows = ocrData.extracted_data;
      } else {
        rows = [ocrData.extracted_data];
      }
    } else if (ocrData.data) {
      // Single backend response structure: { success: true, data: { ... } }
      rows = [ocrData.data];
    } else {
      rows = [ocrData];
    }
  }

  if (rows.length === 0) {
    throw new Error("Tidak ada data untuk diexport.");
  }

  const wb = XLSX.utils.book_new();

  // 1. Separate flat fields for the main sheet
  const dataSheetRows = [];
  const arrayKeys = new Set();

  rows.forEach((row) => {
    const flatRow = {};
    Object.entries(row).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        arrayKeys.add(key);
      } else if (value && typeof value === "object") {
        Object.entries(value).forEach(([nestedKey, nestedValue]) => {
          if (Array.isArray(nestedValue)) {
            arrayKeys.add(`${key}_${nestedKey}`);
          } else if (typeof nestedValue !== "object") {
            flatRow[`${key}_${nestedKey}`] = nestedValue;
          }
        });
      } else {
        flatRow[key] = value;
      }
    });
    dataSheetRows.push(flatRow);
  });

  // Format main sheet rows
  const formattedDataRows = dataSheetRows.map((row) => {
    const newRow = {};
    Object.entries(row).forEach(([k, v]) => {
      newRow[formatHeader(k)] = v;
    });
    return newRow;
  });

  // Create main "Ringkasan Data" sheet
  const dataSheet = XLSX.utils.json_to_sheet(formattedDataRows);
  autoFitColumns(dataSheet, formattedDataRows);
  XLSX.utils.book_append_sheet(wb, dataSheet, "data");

  // 2. Separate array/list fields into new sheets
  arrayKeys.forEach((arrayKey) => {
    const listSheetRows = [];

    rows.forEach((row) => {
      const source = row._source || "document";
      let listData = [];

      // Check top-level first, then nested (avoids splitting keys with underscores like list_item)
      if (Array.isArray(row[arrayKey])) {
        listData = row[arrayKey];
      } else if (arrayKey.includes("_")) {
        const [parentKey, ...childKeys] = arrayKey.split("_");
        const childKey = childKeys.join("_");
        if (row[parentKey] && Array.isArray(row[parentKey][childKey])) {
          listData = row[parentKey][childKey];
        }
      }

      listData.forEach((item) => {
        if (item && typeof item === "object") {
          listSheetRows.push({
            _source: source,
            ...item,
          });
        } else if (item !== undefined && item !== null) {
          listSheetRows.push({
            _source: source,
            value: item,
          });
        }
      });
    });

    if (listSheetRows.length > 0) {
      // Format sheet rows
      const formattedListRows = listSheetRows.map((row) => {
        const newRow = {};
        Object.entries(row).forEach(([k, v]) => {
          newRow[formatHeader(k)] = v;
        });
        return newRow;
      });

      const listSheet = XLSX.utils.json_to_sheet(formattedListRows);
      autoFitColumns(listSheet, formattedListRows);

      // Clean sheet name (Title Case, max 31 characters required by Excel)
      const rawSheetName = formatHeader(arrayKey);
      const sheetName = rawSheetName.substring(0, 31);
      XLSX.utils.book_append_sheet(wb, listSheet, sheetName);
    }
  });

  const excelBuffer = XLSX.write(wb, { bookType: "xlsx", type: "array" });
  return new Blob([excelBuffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

/**
 * Standard client download helper.
 */
export function exportToExcel(ocrData, fileName) {
  const blob = getExcelBlob(ocrData);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
