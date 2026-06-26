import React, { useState, useEffect } from "react";
import toast from "react-hot-toast";

export default function Settings({ baseUrl, token, currentUser }) {
  const [usersList, setUsersList] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Delete modal state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [userToDelete, setUserToDelete] = useState(null);

  // Editing state
  const [editingUser, setEditingUser] = useState(null);

  // Form state
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newEmployee, setNewEmployee] = useState("");
  const [newRole, setNewRole] = useState("user");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchUsers = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${baseUrl}/api/users`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Gagal memuat daftar pengguna");
      }

      const data = await response.json();
      if (data.success && data.users) {
        setUsersList(data.users);
      }
    } catch (err) {
      console.error(err);
      toast.error(err.message || "Gagal memuat pengguna.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [token]);

  const startEditUser = (user) => {
    setEditingUser(user);
    setNewUsername(user.username);
    setNewEmployee(user.employee);
    setNewRole(user.role);
    setNewPassword("");
  };

  const cancelEditUser = () => {
    setEditingUser(null);
    setNewUsername("");
    setNewEmployee("");
    setNewRole("user");
    setNewPassword("");
  };

  const handleAddUser = async (e) => {
    e.preventDefault();
    if (!newUsername.trim() || !newEmployee.trim() || (!editingUser && !newPassword.trim())) {
      toast.error("Semua field wajib diisi");
      return;
    }

    setIsSubmitting(true);
    try {
      let response;
      if (editingUser) {
        // Edit User flow (PUT)
        const payload = {
          username: newUsername,
          role: newRole,
          employee: newEmployee,
        };
        if (newPassword.trim()) {
          payload.password = newPassword;
        }

        response = await fetch(`${baseUrl}/api/users/${editingUser.employee}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        });
      } else {
        // Create User flow (POST)
        response = await fetch(`${baseUrl}/api/users`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            username: newUsername,
            password: newPassword,
            employee: newEmployee,
            role: newRole,
          }),
        });
      }

      if (!response.ok) {
        const errData = await response.json();
        const msg = errData?.detail?.message || errData?.message || "Gagal menyimpan data pengguna.";
        throw new Error(msg);
      }

      if (editingUser) {
        toast.success(`Pengguna '${newUsername}' berhasil diperbarui!`);
      } else {
        toast.success(`Pengguna '${newUsername}' berhasil dibuat!`);
      }

      // Reset form
      cancelEditUser();
      // Refresh list
      fetchUsers();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const confirmDeleteUser = (username) => {
    setUserToDelete(username);
    setShowDeleteModal(true);
  };

  const handleDeleteUser = async () => {
    if (!userToDelete) return;
    
    try {
      const response = await fetch(`${baseUrl}/api/users/${userToDelete}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errData = await response.json();
        const msg = errData?.detail?.message || errData?.message || "Gagal menghapus pengguna.";
        throw new Error(msg);
      }

      toast.success(`Pengguna '${userToDelete}' berhasil dihapus.`);
      fetchUsers();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setShowDeleteModal(false);
      setUserToDelete(null);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Add / Edit User Panel */}
      <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-6">
        <div>
          <h2 className="text-md font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px] text-blue-600">
              {editingUser ? "edit" : "person_add"}
            </span>
            <span>{editingUser ? "Edit Pengguna" : "Tambah Pengguna"}</span>
          </h2>
          <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
            {editingUser ? "Perbarui informasi akun pegawai" : "Buat akun baru untuk akses sistem OCR"}
          </p>
        </div>

        <form onSubmit={handleAddUser} className="space-y-4">
          <div>
            <label className="block text-[10px] font-bold text-slate-500 dark:text-slate-400 mb-1.5 uppercase">
              Username
            </label>
            <input
              type="text"
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              placeholder={editingUser ? "Nama baru" : "Username baru"}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs font-semibold focus:outline-none focus:border-blue-500 transition-colors"
              disabled={isSubmitting}
            />
          </div>

          <div>
            <label className="block text-[10px] font-bold text-slate-500 dark:text-slate-400 mb-1.5 uppercase">
              Kata Sandi {editingUser && "(Baru)"}
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder={editingUser ? "Kosongkan jika tidak ingin diubah" : "Minimal 6 karakter"}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs font-semibold focus:outline-none focus:border-blue-500 transition-colors"
              disabled={isSubmitting}
            />
          </div>

          <div>
            <label className="block text-[10px] font-bold text-slate-500 dark:text-slate-400 mb-1.5 uppercase">
              Nomor Badge
            </label>
            <input
              type="text"
              value={newEmployee}
              onChange={(e) => setNewEmployee(e.target.value)}
              placeholder="Contoh: PKL449"
              className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs font-semibold focus:outline-none focus:border-blue-500 transition-colors"
              disabled={isSubmitting}
            />
          </div>

          <div>
            <label className="block text-[10px] font-bold text-slate-500 dark:text-slate-400 mb-1.5 uppercase">
              Peran (Role)
            </label>
            <select
              value={newRole}
              onChange={(e) => setNewRole(e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs font-semibold focus:outline-none focus:border-blue-500 transition-colors cursor-pointer"
              disabled={isSubmitting}
            >
              <option value="user">User (Hanya Ekstraksi)</option>
              <option value="admin">Admin (Ekstraksi & Manajemen User)</option>
            </select>
          </div>

          {editingUser ? (
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={cancelEditUser}
                className="flex-1 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900 text-slate-600 dark:text-slate-300 font-semibold text-xs transition-colors cursor-pointer text-center"
                disabled={isSubmitting}
              >
                Batal
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex-1 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition-colors flex items-center justify-center gap-1.5 cursor-pointer shadow-sm disabled:opacity-50"
              >
                <span className="material-symbols-outlined text-[16px]">save</span>
                <span>{isSubmitting ? "Menyimpan..." : "Simpan"}</span>
              </button>
            </div>
          ) : (
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition-colors flex items-center justify-center gap-1.5 cursor-pointer shadow-sm disabled:opacity-50"
            >
              <span className="material-symbols-outlined text-[16px]">save</span>
              <span>{isSubmitting ? "Menyimpan..." : "Simpan Akun"}</span>
            </button>
          )}
        </form>
      </div>

      {/* Users List Panel */}
      <div className="lg:col-span-2 bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm flex flex-col h-[520px]">
        <div className="mb-4">
          <h2 className="text-md font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px] text-blue-600">group</span>
            <span>Daftar Pengguna</span>
          </h2>
          <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
            Total {usersList.length} pengguna terdaftar di sistem
          </p>
        </div>

        {isLoading ? (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-2" />
            <span className="text-xs">Memuat daftar pengguna...</span>
          </div>
        ) : usersList.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-400 space-y-2">
            <span className="material-symbols-outlined text-[40px]">group_off</span>
            <span className="text-xs">Tidak ada data pengguna</span>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto custom-scrollbar border border-slate-100 dark:border-slate-800 rounded-2xl">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-900/60 text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase border-b border-slate-100 dark:border-slate-800">
                  <th className="px-4 py-3">Username</th>
                  <th className="px-4 py-3">Nomor Badge</th>
                  <th className="px-4 py-3">Role</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {usersList.map((user, index) => (
                  <tr key={index} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/20 text-slate-700 dark:text-slate-300 transition-colors">
                    <td className="px-4 py-3 font-semibold">{user.username}</td>
                    <td className="px-4 py-3 text-slate-500">{user.employee}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-block font-bold text-[9px] px-2 py-0.5 rounded capitalize ${user.role === "admin" ? "bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400" : "bg-slate-50 dark:bg-slate-900 text-slate-600 dark:text-slate-400"}`}>
                        {user.role}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => startEditUser(user)}
                          className="p-1 rounded-lg text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-950/30 transition-colors inline-flex items-center justify-center cursor-pointer"
                          title="Edit Pengguna"
                        >
                          <span className="material-symbols-outlined text-[16px]">edit</span>
                        </button>
                        {user.employee.toLowerCase() !== currentUser?.employee?.toLowerCase() ? (
                          <button
                            onClick={() => confirmDeleteUser(user.username)}
                            className="p-1 rounded-lg text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors inline-flex items-center justify-center cursor-pointer"
                            title="Hapus Pengguna"
                          >
                            <span className="material-symbols-outlined text-[16px]">delete</span>
                          </button>
                        ) : (
                          <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 select-none mr-2">
                            Akun Anda
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {/* Custom Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm px-4">
          <div className="w-full max-w-sm bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-2xl transition-all duration-300 relative z-50 animate-in fade-in zoom-in-95 duration-150">
            <div className="text-center space-y-4">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-red-50 dark:bg-red-950/40 border border-red-100 dark:border-red-900/30 text-red-600 dark:text-red-400">
                <span className="material-symbols-outlined text-[24px]">warning</span>
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">
                  Hapus Pengguna?
                </h3>
                <p className="text-xs text-slate-400 dark:text-slate-500">
                  Apakah Anda yakin ingin menghapus pengguna <span className="font-bold text-slate-700 dark:text-slate-300">"{userToDelete}"</span>? Tindakan ini tidak dapat dibatalkan.
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-3 mt-6">
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setUserToDelete(null);
                }}
                className="flex-1 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900 text-slate-600 dark:text-slate-300 font-semibold text-xs transition-colors cursor-pointer text-center"
              >
                Batal
              </button>
              <button
                onClick={handleDeleteUser}
                className="flex-1 py-2.5 rounded-xl bg-red-600 hover:bg-red-700 text-white font-semibold text-xs transition-colors cursor-pointer text-center shadow-sm"
              >
                Hapus Akun
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
