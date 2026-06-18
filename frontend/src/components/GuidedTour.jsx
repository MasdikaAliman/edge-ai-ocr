import { driver } from "driver.js";
import "driver.js/dist/driver.css";

export function startGuidedTour({ tourId, setActivePage, setUploadedFiles, setOcrResult }) {
  // Common steps at the beginning
  const commonHeaderSteps = [
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
          // Transition to the selected page
          setActivePage(tourId);
          setUploadedFiles([]);
          setOcrResult(null);
          setTimeout(() => {
            driver.moveNext();
          }, 150);
        },
      },
    },
  ];

  let featureSteps = [];

  if (tourId === "coo") {
    featureSteps = [
      {
        element: "#upload-zone-container",
        popover: {
          title: "3. Unggah Berkas COO",
          description: "Tarik & lepas berkas-berkas COO (PEB, BL, PL, Invoice COO) untuk memulai pemrosesan dokumen.",
          side: "bottom",
          align: "center",
          onPrevClick: (element, step, { driver }) => {
            setActivePage("dashboard");
            setTimeout(() => {
              driver.movePrevious();
            }, 150);
          },
          onNextClick: (element, step, { driver }) => {
            // Mock uploading COO files
            const dummyFiles = [
              new File([""], "PEB_12345.pdf", { type: "application/pdf" }),
              new File([""], "BL_67890.pdf", { type: "application/pdf" }),
              new File([""], "Packing_List.pdf", { type: "application/pdf" }),
              new File([""], "Invoice_COO.pdf", { type: "application/pdf" })
            ];
            setUploadedFiles(dummyFiles);
            setTimeout(() => {
              driver.moveNext();
            }, 300);
          },
        },
      },
      {
        element: "#extraction-config-container",
        popover: {
          title: "4. Parameter Konfigurasi COO",
          description: "Tinjau berkas yang diunggah, atur halaman opsional, atau pilih folder penyimpanan lokal untuk menyimpan hasil ekstraksi Excel.",
          side: "right",
          align: "center",
          onPrevClick: (element, step, { driver }) => {
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
          title: "5. Pratinjau Dokumen COO",
          description: "Lihat pratinjau dokumen COO secara visual sebelum melakukan pemrosesan data.",
          side: "left",
          align: "center",
          onNextClick: (element, step, { driver }) => {
            setOcrResult({
              peb_number: "PEB-998877",
              bl_number: "BL-TJK123",
              invoice_number: "INV-COO-99",
              exporter: "PT Global Trade Indonesia",
              consignee: "Tokyo Trading Co.",
              items: [
                { description: "Industrial Parts", qty: "1000 PCS", weight: "5000 KGS" }
              ]
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
          title: "6. Hasil OCR & Ekspor COO",
          description: "Menampilkan hasil penggabungan data COO. Anda dapat menyunting data atau langsung mengunduhnya ke template Excel resmi.",
          side: "left",
          align: "center",
          onPrevClick: (element, step, { driver }) => {
            setOcrResult(null);
            setTimeout(() => {
              driver.movePrevious();
            }, 150);
          },
        },
      },
    ];
  } else if (tourId === "batch") {
    featureSteps = [
      {
        element: "#upload-zone-container",
        popover: {
          title: "3. Unggah Berkas Batch",
          description: "Unggah banyak berkas sekaligus (maksimal 50 berkas) untuk diproses secara paralel.",
          side: "bottom",
          align: "center",
          onPrevClick: (element, step, { driver }) => {
            setActivePage("dashboard");
            setTimeout(() => {
              driver.movePrevious();
            }, 150);
          },
          onNextClick: (element, step, { driver }) => {
            // Mock uploading batch files
            const dummyFiles = [
              new File([""], "dokumen_faktur_1.pdf", { type: "application/pdf" }),
              new File([""], "dokumen_faktur_2.pdf", { type: "application/pdf" }),
              new File([""], "dokumen_faktur_3.pdf", { type: "application/pdf" })
            ];
            setUploadedFiles(dummyFiles);
            setTimeout(() => {
              driver.moveNext();
            }, 300);
          },
        },
      },
      {
        element: "#extraction-config-container",
        popover: {
          title: "4. Parameter Konfigurasi Batch",
          description: "Pilih sub-mode ekstraksi, atur tingkat concurrency proses paralel, dan tentukan folder penyimpanan hasil.",
          side: "right",
          align: "center",
          onPrevClick: (element, step, { driver }) => {
            setUploadedFiles([]);
            setTimeout(() => {
              driver.movePrevious();
            }, 150);
          },
          onNextClick: (element, step, { driver }) => {
            setOcrResult({
              batch_summary: {
                total_files: 3,
                successful_files: 3,
                failed_files: 0,
                failures: []
              },
              results: [
                { filename: "dokumen_faktur_1.pdf", data: { invoice_number: "INV-001", total: "Rp 1.500.000" } },
                { filename: "dokumen_faktur_2.pdf", data: { invoice_number: "INV-002", total: "Rp 3.200.000" } },
                { filename: "dokumen_faktur_3.pdf", data: { invoice_number: "INV-003", total: "Rp 850.000" } }
              ]
            });
            setTimeout(() => {
              driver.moveNext();
            }, 300);
          },
        },
      },
      {
        element: "#ocr-results-container",
        popover: {
          title: "5. Log & Hasil Batch",
          description: "Lihat status kesuksesan proses batch di panel log, sunting gabungan JSON, serta unduh file Excel hasil ekstraksi.",
          side: "left",
          align: "center",
          onPrevClick: (element, step, { driver }) => {
            setOcrResult(null);
            setTimeout(() => {
              driver.movePrevious();
            }, 150);
          },
        },
      },
    ];
  } else if (tourId === "prompt") {
    featureSteps = [
      {
        element: "#upload-zone-container",
        popover: {
          title: "3. Unggah Berkas Kustom",
          description: "Unggah dokumen tunggal yang ingin Anda ekstrak menggunakan instruksi atau prompt tertentu.",
          side: "bottom",
          align: "center",
          onPrevClick: (element, step, { driver }) => {
            setActivePage("dashboard");
            setTimeout(() => {
              driver.movePrevious();
            }, 150);
          },
          onNextClick: (element, step, { driver }) => {
            const dummyFile = new File([""], "dokumen_kustom.pdf", { type: "application/pdf" });
            setUploadedFiles([dummyFile]);
            setTimeout(() => {
              driver.moveNext();
            }, 300);
          },
        },
      },
      {
        element: "#extraction-config-container",
        popover: {
          title: "4. Konfigurasi Prompt AI",
          description: "Ketik instruksi bebas (prompt) di area teks, atau gunakan template cepat yang tersedia untuk mengisi perintah secara otomatis.",
          side: "right",
          align: "center",
          onPrevClick: (element, step, { driver }) => {
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
            setOcrResult({
              nama_perusahaan: "PT Maju Bersama",
              alamat: "Jl. Sudirman No. 12, Jakarta",
              nomor_kontrak: "KTR-2026-001",
              nilai_kontrak: "Rp 500.000.000"
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
          description: "Menampilkan output JSON hasil ekstraksi AI kustom yang dapat Anda sunting, unduh, atau ekspor ke Excel.",
          side: "left",
          align: "center",
          onPrevClick: (element, step, { driver }) => {
            setOcrResult(null);
            setTimeout(() => {
              driver.movePrevious();
            }, 150);
          },
        },
      },
    ];
  } else {
    // Default to "dokumen"
    featureSteps = [
      {
        element: "#upload-zone-container",
        popover: {
          title: "3. Unggah Berkas",
          description: "Tarik & lepas berkas PDF atau gambar di sini untuk memulai pemrosesan dokumen.",
          side: "bottom",
          align: "center",
          onPrevClick: (element, step, { driver }) => {
            setActivePage("dashboard");
            setTimeout(() => {
              driver.movePrevious();
            }, 150);
          },
          onNextClick: (element, step, { driver }) => {
            const dummyFile = new File([""], "dummy_faktur.pdf", { type: "application/pdf" });
            setUploadedFiles([dummyFile]);
            setTimeout(() => {
              driver.moveNext();
            }, 300);
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
            setOcrResult(null);
            setTimeout(() => {
              driver.movePrevious();
            }, 150);
          },
        },
      },
    ];
  }

  const steps = [...commonHeaderSteps, ...featureSteps];

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
