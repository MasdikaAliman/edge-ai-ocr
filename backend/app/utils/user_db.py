import os
import json
import logging
import bcrypt
from fastapi import HTTPException
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
USERS_FILE = os.path.join(BASE_DIR, "users.json")

def load_users() -> List[Dict]:
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Gagal membaca file {USERS_FILE}: {e}")
        return []

def save_users(users: List[Dict]):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Gagal menulis ke file {USERS_FILE}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_type": "database_error",
                "message": "Gagal menyimpan data pengguna.",
            }
        )

def get_user(employee: str) -> Optional[Dict]:
    users = load_users()
    for u in users:
        if u["employee"].lower() == employee.lower():
            return u
    return None

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def add_user(username: str, plain_password: str, employee: str, role: str = "user") -> Dict:
    users = load_users()
    
    # Check if employee (badge number) already exists
    for u in users:
        if u["employee"].lower() == employee.lower():
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error_type": "employee_exists",
                    "message": f"Nomor Badge '{employee}' sudah terdaftar.",
                }
            )
            
    new_user = {
        "username": username,
        "hashed_password": hash_password(plain_password),
        "employee": employee,
        "role": role
    }
    users.append(new_user)
    save_users(users)
    return new_user

def delete_user(username: str) -> bool:
    users = load_users()
    initial_len = len(users)
    users = [u for u in users if u["username"].lower() != username.lower()]
    if len(users) < initial_len:
        save_users(users)
        return True
    return False

def update_user(employee: str, username: Optional[str] = None, plain_password: Optional[str] = None, role: Optional[str] = None, new_employee: Optional[str] = None) -> Optional[Dict]:
    users = load_users()
    
    target_user = None
    for u in users:
        if u["employee"].lower() == employee.lower():
            target_user = u
            break
            
    if not target_user:
        return None
        
    # Check for badge number conflict if it's changing
    if new_employee and new_employee.lower() != employee.lower():
        for u in users:
            if u["employee"].lower() == new_employee.lower():
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error_type": "employee_exists",
                        "message": f"Nomor Badge '{new_employee}' sudah terdaftar.",
                    }
                )
        target_user["employee"] = new_employee

    if username is not None:
        target_user["username"] = username
    if plain_password:
        target_user["hashed_password"] = hash_password(plain_password)
    if role is not None:
        # Prevent demoting the last admin to user
        if target_user["role"] == "admin" and role == "user":
            admin_count = sum(1 for usr in users if usr["role"] == "admin")
            if admin_count <= 1:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error_type": "last_admin_demotion",
                        "message": "Tidak dapat mengubah peran admin terakhir menjadi user.",
                    }
                )
        target_user["role"] = role
        
    save_users(users)
    return target_user

def init_default_admin():
    users = load_users()
    if not users:
        admin_user =  "SYSTEM_ADMIN"
        admin_pass = "admin123"
        admin_emp = "000000"
        
        # Add default admin
        add_user(
            username=admin_user,
            plain_password=admin_pass,
            employee=admin_emp,
            role="admin"
        )
        logger.info(f"Database user diinisialisasi. Default admin '{admin_user}' dibuat.")
