import * as XLSX from 'xlsx';
import ExcelJS from 'exceljs';

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

  // 2. Load workbook into exceljs
  const workbook = new ExcelJS.Workbook();
  await workbook.xlsx.load(arrayBuffer);

  // 3. Extract OCR data
  const data = ocrResult?.data || ocrResult || {};

  // Safely coerce to string (null/undefined → empty string)
  const str = (v) => (v !== null && v !== undefined ? String(v) : "");

  // 4. Fill "CREATE COO" sheet scalars
  const cooSheet = workbook.getWorksheet("CREATE COO");
  if (cooSheet) {
    cooSheet.getCell("D4").value = str(data.country_of_destination);
    cooSheet.getCell("D6").value = str(data.form);
    const dikirim_oleh = str(data.vessel_voyage_no) + " / " + str(data.mvs);
    cooSheet.getCell("D25").value = str(data.consignee);
    cooSheet.getCell("D33").value = dikirim_oleh;
    cooSheet.getCell("D36").value = str(data.ship_date);
    cooSheet.getCell("D39").value = str(data.document_no_bl);
    cooSheet.getCell("D40").value = str(data.date_bl);
    cooSheet.getCell("D44").value = str(data.total_amount);
    cooSheet.getCell("D45").value = str(data.document_no_peb);
    cooSheet.getCell("D46").value = str(data.date_peb);
    cooSheet.getCell("D49").value = str(data.document_no_pl);
    cooSheet.getCell("D50").value = str(data.date_pl);
    cooSheet.getCell("D54").value = str(data.invoice_no);
    cooSheet.getCell("D55").value = str(data.invoice_date);
    cooSheet.getCell("D57").value = str(data.total_amount);
  }

  // 5. Fill "Sheet1" with table items
  const sheet1 = workbook.getWorksheet("Sheet1");
  if (sheet1 && Array.isArray(data.table) && data.table.length > 0) {
    const tableItems = data.table;

    // Clear existing sample data rows (rows 2 to 100)
    for (let r = 2; r <= 100; r++) {
      const row = sheet1.getRow(r);
      for (let c = 1; c <= 9; c++) {
        row.getCell(c).value = null;
      }
    }

    // Write new rows from OCR table data
    const safeNum = (v) => {
      if (v === null || v === undefined || v === "") return "";
      if (typeof v === "string") {
        v = v.replace(/,/g, "");
      }
      const n = parseFloat(v);
      return isNaN(n) ? v : n;
    };
    const safeStr = (v) => (v !== null && v !== undefined ? String(v) : "");

    tableItems.forEach((item, idx) => {
      const r = idx + 2; // Excel row (1-indexed), data starts at row 2
      const row = sheet1.getRow(r);
      row.getCell(1).value = idx + 1;
      row.getCell(2).value = safeStr(item.kategori_barang);
      row.getCell(3).value = safeStr(item.model);
      row.getCell(4).value = safeNum(item.quantity_ctns);
      row.getCell(5).value = safeNum(item.quantity_pcs);
      row.getCell(6).value = safeNum(item.unit_price);
      row.getCell(7).value = safeNum(item.amount_usd);
      row.getCell(8).value = safeNum(item.bruto);
      row.getCell(9).value = safeNum(item.netto);
    });
  }

  // 6. Serialize to Blob
  const excelBuffer = await workbook.xlsx.writeBuffer();
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
