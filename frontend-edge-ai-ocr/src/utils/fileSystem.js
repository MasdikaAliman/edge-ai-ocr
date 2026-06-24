// Simple IndexedDB utility to save and load FileSystemDirectoryHandle across page reloads
const dbName = "EdgeAIOCR";
const storeName = "config";

export function saveDirectoryHandle(handle) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(dbName, 1);
    request.onupgradeneeded = (e) => {
      e.target.result.createObjectStore(storeName);
    };
    request.onsuccess = (e) => {
      const db = e.target.result;
      const tx = db.transaction(storeName, "readwrite");
      tx.objectStore(storeName).put(handle, "directoryHandle");
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    };
    request.onerror = () => reject(request.error);
  });
}

export function loadDirectoryHandle() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(dbName, 1);
    request.onupgradeneeded = (e) => {
      e.target.result.createObjectStore(storeName);
    };
    request.onsuccess = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(storeName)) {
        resolve(null);
        return;
      }
      const tx = db.transaction(storeName, "readonly");
      const req = tx.objectStore(storeName).get("directoryHandle");
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => reject(req.error);
    };
    request.onerror = () => reject(request.error);
  });
}

export async function verifyDirectoryPermission(directoryHandle, readWrite = true) {
  if (!directoryHandle) return false;
  const options = { mode: readWrite ? "readwrite" : "read" };
  
  try {
    if ((await directoryHandle.queryPermission(options)) === "granted") {
      return true;
    }
  } catch (err) {
    console.error("Gagal memeriksa izin direktori:", err);
  }
  return false;
}

export async function requestDirectoryPermission(directoryHandle, readWrite = true) {
  if (!directoryHandle) return false;
  const options = { mode: readWrite ? "readwrite" : "read" };
  
  try {
    const status = await directoryHandle.requestPermission(options);
    return status === "granted";
  } catch (err) {
    console.error("Gagal meminta izin direktori:", err);
    return false;
  }
}

export async function saveBlobToDirectory(directoryHandle, filename, blob) {
  const options = { mode: "readwrite" };
  
  // Verify or request permission
  if ((await directoryHandle.queryPermission(options)) !== "granted") {
    if ((await directoryHandle.requestPermission(options)) !== "granted") {
      throw new Error("Izin menulis ke folder ditolak oleh pengguna.");
    }
  }
  
  const fileHandle = await directoryHandle.getFileHandle(filename, { create: true });
  const writable = await fileHandle.createWritable();
  await writable.write(blob);
  await writable.close();
}
