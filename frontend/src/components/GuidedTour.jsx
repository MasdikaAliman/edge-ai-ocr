import { driver } from "driver.js";
import "driver.js/dist/driver.css";

export function startGuidedTour({ setActivePage, setUploadedFiles, setOcrResult }) {
  const steps = [
    {
      element: "#health-indicator-top",
      popover: {
        title: "1. Status Layanan",
        description: "Menampilkan status server OCR secara real-time. Jika offline, proses OCR tidak dapat dijalankan.",
        side: "right",
        align: "center",
      },
    },
    {
      element: "#sidebar-navigation",
      popover: {
        title: "2. Navigasi Fitur",
        description: "Akses 4 fitur utama OCR: Ekstraksi Dokumen tunggal, Ekstraksi COO, Batch Processing, dan Custom Prompt.",
        side: "right",
        align: "center",
        onNextClick: (element, step, { driver }) => {
          // Transition to Dokumen page Step 1
          setActivePage("dokumen");
          setUploadedFiles([]);
          setOcrResult(null);
          setTimeout(() => {
            driver.moveNext();
          }, 150);
        },
      },
    },
    {
      element: "#upload-zone-container",
      popover: {
        title: "3. Unggah Berkas",
        description: "Tarik & lepas berkas PDF atau gambar di sini untuk memulai pemrosesan dokumen.",
        side: "bottom",
        align: "center",
        onPrevClick: (element, step, { driver }) => {
          // Go back to Dashboard
          setActivePage("dashboard");
          setTimeout(() => {
            driver.movePrevious();
          }, 150);
        },
        onNextClick: (element, step, { driver }) => {
          // Mock uploading a file to transition to Step 2 (Configuration & Preview)
          const dummyFile = new File([""], "dummy_faktur.pdf", { type: "application/pdf" });
          setUploadedFiles([dummyFile]);
          setTimeout(() => {
            driver.moveNext();
          }, 300); // Wait slightly longer for PDF.js to initialize preview container
        },
      },
    },
    {
      element: "#extraction-config-container",
      popover: {
        title: "4. Parameter Konfigurasi",
        description: "Atur tipe dokumen, target data fields, atau kustomisasi lainnya di sini sebelum menjalankan OCR.",
        side: "right",
        align: "center",
        onPrevClick: (element, step, { driver }) => {
          // Go back to Step 1 (Upload zone)
          setUploadedFiles([]);
          setTimeout(() => {
            driver.movePrevious();
          }, 150);
        },
      },
    },
    {
      element: "#document-previewer-container",
      popover: {
        title: "5. Pratinjau Dokumen",
        description: "Membantu Anda melihat pratinjau dokumen secara visual, melakukan zoom, serta memilih halaman.",
        side: "left",
        align: "center",
        onNextClick: (element, step, { driver }) => {
          // Mock OCR results to transition to Step 3 (Hasil)
          setOcrResult({
            invoice_number: "INV-2026-999",
            date: "2026-06-16",
            vendor: "PT Antigravity Global",
            total: "Rp 10.000.000",
            tax: "Rp 1.100.000"
          });
          setTimeout(() => {
            driver.moveNext();
          }, 200);
        },
      },
    },
    {
      element: "#ocr-results-container",
      popover: {
        title: "6. Hasil OCR & Ekspor",
        description: "Menampilkan output JSON hasil ekstraksi AI yang dapat Anda sunting, unduh, atau ekspor ke Excel.",
        side: "left",
        align: "center",
        onPrevClick: (element, step, { driver }) => {
          // Go back to Step 2 (Configuration)
          setOcrResult(null);
          setTimeout(() => {
            driver.movePrevious();
          }, 150);
        },
      },
    },
  ];

  const driverObj = driver({
    showProgress: true,
    animate: true,
    allowClose: true,
    overlayColor: "rgba(11, 28, 48, 0.6)",
    nextBtnText: "Lanjut",
    prevBtnText: "Kembali",
    doneBtnText: "Selesai",
    steps: steps,
    onDestroyed: () => {
      // Return user to dashboard and reset mock states when tour ends
      setActivePage("dashboard");
      setUploadedFiles([]);
      setOcrResult(null);
    }
  });

  driverObj.drive();
}
