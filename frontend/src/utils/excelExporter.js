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

// ─────────────────────────────────────────────────────────────────────────────
//  COO Template-Based Export
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Fills the COO Excel template (public/coo_template.xlsx) with OCR result data
 * and returns a Blob ready for download or directory save.
 *
 * Mapping:
 *   "CREATE COO" sheet (column D):
 *     D25  ← consignee
 *     D33  ← vessel_voyage_no
 *     D36  ← ship_date
 *     D39  ← document_no_bl
 *     D40  ← date_bl
 *     D44  ← total_amount  (Value EWP USD)
 *     D45  ← document_no_peb
 *     D46  ← date_peb
 *     D49  ← document_no_pl
 *     D50  ← date_pl
 *     D54  ← invoice_no
 *     D55  ← invoice_date
 *     D57  ← total_amount  (Total Invoice EWP USD)
 *
 *   "Sheet1" table (rows 2+, header row 1 preserved):
 *     A=No, B=kategori_barang, C=model, D=quantity_ctns, E=quantity_pcs,
 *     F=unit_price, G=amount_usd, H=bruto, I=netto
 */
export async function getCooExcelBlob(ocrResult) {
  // 1. Fetch the template served from /public
  const response = await fetch("/coo_template.xlsx");
  if (!response.ok) {
    throw new Error("Gagal memuat template COO. Pastikan file coo_template.xlsx ada di folder public.");
  }
  const arrayBuffer = await response.arrayBuffer();

  // 2. Read workbook preserving styles
  const wb = XLSX.read(new Uint8Array(arrayBuffer), {
    type: "array",
    cellStyles: true,
    cellDates: true,
  });

  // 3. Extract OCR data
  const data = ocrResult?.data || ocrResult || {};

  // Helper: write a value into an existing cell while preserving its style
  const writeCell = (ws, address, value, cellType) => {
    const existing = ws[address] || {};
    ws[address] = {
      ...existing,          // keep style (s), any formula metadata, etc.
      v: value,
      t: cellType,
      w: String(value ?? ""),
    };
  };

  // Safely coerce to string (null/undefined → empty string)
  const str = (v) => (v !== null && v !== undefined ? String(v) : "");

  // Safely coerce to number (falls back to the raw value as string if not parseable)
  const num = (v) => {
    const n = parseFloat(v);
    return isNaN(n) ? str(v) : n;
  };

  // 4. Fill "CREATE COO" sheet scalars
  const cooSheet = wb.Sheets["CREATE COO"];
  if (cooSheet) {
    writeCell(cooSheet, "D25", str(data.consignee), "s");
    writeCell(cooSheet, "D33", str(data.vessel_voyage_no), "s");
    writeCell(cooSheet, "D36", str(data.ship_date), "s");
    writeCell(cooSheet, "D39", str(data.document_no_bl), "s");
    writeCell(cooSheet, "D40", str(data.date_bl), "s");
    writeCell(cooSheet, "D44", num(data.total_amount), "n");
    writeCell(cooSheet, "D45", str(data.document_no_peb), "s");
    writeCell(cooSheet, "D46", str(data.date_peb), "s");
    writeCell(cooSheet, "D49", str(data.document_no_pl), "s");
    writeCell(cooSheet, "D50", str(data.date_pl), "s");
    writeCell(cooSheet, "D54", str(data.invoice_no), "s");
    writeCell(cooSheet, "D55", str(data.invoice_date), "s");
    writeCell(cooSheet, "D57", num(data.total_amount), "n");
  }

  // 5. Fill "Sheet1" with table items
  const sheet1 = wb.Sheets["Sheet1"];
  if (sheet1 && Array.isArray(data.table) && data.table.length > 0) {
    const tableItems = data.table;

    // Clear existing sample data rows (rows 2+ in 1-indexed = r>=1 in 0-indexed)
    // Row 1 header (r=0) and K1 formula are NOT touched.
    const currentRange = XLSX.utils.decode_range(sheet1["!ref"] || "A1:K18");
    for (let r = 1; r <= currentRange.e.r; r++) {
      for (let c = currentRange.s.c; c <= currentRange.e.c; c++) {
        const addr = XLSX.utils.encode_cell({ r, c });
        delete sheet1[addr];
      }
    }

    // Write new rows from OCR table data
    const safeNum = (v) => {
      if (v === null || v === undefined || v === "") return 0;
      const n = parseFloat(v);
      return isNaN(n) ? v : n;
    };
    const safeStr = (v) => (v !== null && v !== undefined ? String(v) : "");

    tableItems.forEach((item, idx) => {
      const r = idx + 2; // Excel row (1-indexed), data starts at row 2
      sheet1[`A${r}`] = { v: idx + 1,                        t: "n" };
      sheet1[`B${r}`] = { v: safeStr(item.kategori_barang),  t: "s" };
      sheet1[`C${r}`] = { v: safeStr(item.model),            t: "s" };
      sheet1[`D${r}`] = { v: safeNum(item.quantity_ctns),    t: "n" };
      sheet1[`E${r}`] = { v: safeNum(item.quantity_pcs),     t: "n" };
      sheet1[`F${r}`] = { v: safeNum(item.unit_price),       t: "n" };
      sheet1[`G${r}`] = { v: safeNum(item.amount_usd),       t: "n" };
      sheet1[`H${r}`] = { v: safeNum(item.bruto),            t: "n" };
      sheet1[`I${r}`] = { v: safeNum(item.netto),            t: "n" };
    });

    // Update sheet range to cover the new data extent (A1 : K{lastRow})
    const lastDataRow = tableItems.length + 1; // +1 for header row
    sheet1["!ref"] = XLSX.utils.encode_range({
      s: { r: 0, c: 0 },
      e: { r: lastDataRow, c: 10 }, // columns A–K (0-indexed 0–10)
    });
  }

  // 6. Serialize to Blob
  const excelBuffer = XLSX.write(wb, {
    bookType: "xlsx",
    type: "array",
    cellStyles: true,
  });
  return new Blob([excelBuffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

/**
 * Fetches the COO template, fills it with OCR data, and triggers a browser download.
 */
export async function exportCooToExcelTemplate(ocrResult, fileName) {
  const blob = await getCooExcelBlob(ocrResult);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
