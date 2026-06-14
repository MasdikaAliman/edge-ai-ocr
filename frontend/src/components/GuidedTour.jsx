import { driver } from "driver.js";
import "driver.js/dist/driver.css";

export function startGuidedTour() {
  const driverObj = driver({
    showProgress: true,
    animate: true,
    allowClose: true,
    overlayColor: "rgba(11, 28, 48, 0.5)", // Match deep blue background opacity
    nextBtnText: "Lanjut",
    prevBtnText: "Kembali",
    doneBtnText: "Selesai",
    steps: [
      {
        element: "#health-indicator-container",
        popover: {
          title: "1. Service Health Indicator",
          description: "Menampilkan status kesiapan service OCR secara real-time. Jika service offline, tombol submit akan dinonaktifkan.",
          side: "bottom",
          align: "start",
        },
      },
      {
        element: "#mode-selector-container",
        popover: {
          title: "2. Pilihan Mode Pemrosesan",
          description: "Pilih salah satu dari 3 mode: Document Type (predefined), Fields (custom fields), atau Custom Prompt (LLM instructions).",
          side: "bottom",
          align: "center",
        },
      },
      {
        element: "#extraction-config-container",
        popover: {
          title: "3. Parameter Input",
          description: "Konfigurasikan ekstraksi dokumen Anda di sini (pilih tipe dokumen, daftarkan field target, atau buat prompt kustom).",
          side: "right",
          align: "center",
        },
      },
      {
        element: "#upload-zone-container",
        popover: {
          title: "4. Area Unggah Berkas",
          description: "Tarik & lepas satu atau beberapa berkas PDF/gambar sekaligus untuk pemrosesan batch.",
          side: "right",
          align: "center",
        },
      },
      {
        element: "#document-previewer-container",
        popover: {
          title: "5. Document Preview",
          description: "Melihat pratinjau berkas Anda, melakukan zoom, memilih halaman PDF (jika tunggal), dan berpindah antar berkas batch dengan mudah.",
          side: "top",
          align: "center",
        },
      },
      {
        element: "#ocr-results-container",
        popover: {
          title: "6. Results Preview",
          description: "Melihat output JSON terformat hasil OCR. Anda dapat memberi nama file kustom lalu mengunduh hasil sebagai berkas JSON atau Excel.",
          side: "left",
          align: "center",
        },
      },
    ],
  });

  driverObj.drive();
}
