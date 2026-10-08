# -*- coding: utf-8 -*-
"""Lớp thao tác cơ sở dữ liệu SQLite cho hệ thống chấm công HSTech."""
import sqlite3
import os
import hashlib
from datetime import datetime, date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "hstech.db")
FACES_DIR = os.path.join(BASE_DIR, "faces")
ATT_PHOTOS_DIR = os.path.join(BASE_DIR, "attendance_photos")

os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
os.makedirs(FACES_DIR, exist_ok=True)
os.makedirs(ATT_PHOTOS_DIR, exist_ok=True)


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


# Ngưỡng nhận diện mặc định: LBPH confidence càng THẤP nghĩa là càng giống —
# 45 là mức chặt (ưu tiên an toàn, tránh nhận nhầm người khác hơn là nhận đúng
# mọi lúc). Có thể tăng lên nếu thấy khó nhận ra đúng người (Cài đặt > Nhận diện).
# min_votes = số khung hình liên tiếp phải khớp mới chấp nhận kết quả.
DEFAULT_SETTINGS = {
    "face_confidence_threshold": "45",
    "min_votes_to_accept": "6",
}


def get_setting(key, default=None):
    conn = _conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    if row is not None:
        return row["value"]
    return DEFAULT_SETTINGS.get(key, default)


def set_setting(key, value):
    conn = _conn()
    conn.execute("INSERT INTO settings (key, value) VALUES (?,?) "
                 "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
    conn.commit()
    conn.close()


def init_db(seed_demo=True):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT,
        role TEXT DEFAULT 'admin',
        ma_nv TEXT
    )""")
    # Cho phép nâng cấp database cũ (tạo trước khi có cột ma_nv) không bị lỗi
    try:
        cur.execute("ALTER TABLE users ADD COLUMN ma_nv TEXT")
    except sqlite3.OperationalError:
        pass
    cur.execute("""CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ma_nv TEXT UNIQUE NOT NULL,
        ho_ten TEXT NOT NULL,
        ngay_sinh TEXT,
        sdt TEXT,
        email TEXT,
        phong_ban TEXT,
        chuc_vu TEXT,
        ngay_vao_lam TEXT,
        trang_thai TEXT DEFAULT 'Đang làm',
        anh_path TEXT,
        label_id INTEGER
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ma_nv TEXT NOT NULL,
        ngay TEXT NOT NULL,
        gio_vao TEXT,
        gio_ra TEXT,
        trang_thai TEXT,
        anh_vao TEXT,
        anh_ra TEXT,
        FOREIGN KEY(ma_nv) REFERENCES employees(ma_nv)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    conn.commit()

    cur.execute("SELECT COUNT(*) c FROM users")
    if cur.fetchone()["c"] == 0:
        cur.execute("INSERT INTO users (username, password, full_name, role, ma_nv) VALUES (?,?,?,?,?)",
                    ("admin", hash_pw("123456"), "Admin", "admin", None))
        conn.commit()

    if seed_demo:
        cur.execute("SELECT COUNT(*) c FROM employees")
        if cur.fetchone()["c"] == 0:
            demo = [
                ("NV001", "Nguyễn Thị Ngọc", "Kế toán", "Nhân viên"),
                ("NV002", "Trần Văn Minh", "IT", "Developer"),
                ("NV003", "Lê Thị Mai", "Nhân sự", "Nhân viên"),
                ("NV004", "Phạm Văn Nam", "Kinh doanh", "Nhân viên"),
                ("NV005", "Hoàng Thị Lan", "Marketing", "Nhân viên"),
            ]
            for i, (ma, ten, pb, cv) in enumerate(demo):
                cur.execute("""INSERT INTO employees
                    (ma_nv, ho_ten, phong_ban, chuc_vu, ngay_vao_lam, trang_thai, label_id)
                    VALUES (?,?,?,?,?,?,?)""",
                    (ma, ten, pb, cv, "01/01/2024", "Đang làm", i + 1))
                # Tạo luôn tài khoản đăng nhập cho nhân viên demo: mật khẩu mặc định = mã NV
                cur.execute("""INSERT OR IGNORE INTO users (username, password, full_name, role, ma_nv)
                    VALUES (?,?,?,?,?)""",
                    (ma, hash_pw(ma), ten, "employee", ma))
            conn.commit()
    conn.close()


def check_login(username, password):
    conn = _conn()
    row = conn.execute("SELECT * FROM users WHERE username=? AND password=?",
                        (username, hash_pw(password))).fetchone()
    conn.close()
    return dict(row) if row else None


def create_employee_account(ma_nv, ho_ten, password=None):
    """Tạo (hoặc cập nhật) tài khoản đăng nhập role='employee' gắn với 1 nhân
    viên. Mặc định mật khẩu = mã NV nếu không truyền vào. Trả về (username, mật khẩu dạng chữ)."""
    password = password or ma_nv
    conn = _conn()
    existing = conn.execute("SELECT id FROM users WHERE username=?", (ma_nv,)).fetchone()
    if existing:
        conn.execute("UPDATE users SET full_name=?, ma_nv=?, role='employee' WHERE username=?",
                     (ho_ten, ma_nv, ma_nv))
    else:
        conn.execute("""INSERT INTO users (username, password, full_name, role, ma_nv)
            VALUES (?,?,?,?,?)""", (ma_nv, hash_pw(password), ho_ten, "employee", ma_nv))
    conn.commit()
    conn.close()
    return ma_nv, password


def reset_employee_password(ma_nv, new_password):
    conn = _conn()
    conn.execute("UPDATE users SET password=? WHERE username=?", (hash_pw(new_password), ma_nv))
    conn.commit()
    conn.close()


def change_password(username, old_password, new_password):
    user = check_login(username, old_password)
    if not user:
        return False
    conn = _conn()
    conn.execute("UPDATE users SET password=? WHERE username=?", (hash_pw(new_password), username))
    conn.commit()
    conn.close()
    return True


def has_account(ma_nv):
    conn = _conn()
    row = conn.execute("SELECT id FROM users WHERE username=?", (ma_nv,)).fetchone()
    conn.close()
    return row is not None


def employees_without_account():
    """Danh sách nhân viên chưa có tài khoản đăng nhập (thường là nhân viên
    được thêm trước khi có tính năng tự tạo tài khoản)."""
    conn = _conn()
    rows = conn.execute("""SELECT e.ma_nv, e.ho_ten FROM employees e
        LEFT JOIN users u ON u.username = e.ma_nv
        WHERE u.id IS NULL ORDER BY e.id""").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def bulk_create_accounts():
    """Tạo tài khoản (mật khẩu mặc định = mã NV) cho MỌI nhân viên hiện chưa
    có tài khoản. Trả về list (ma_nv, ho_ten, password)."""
    created = []
    for e in employees_without_account():
        ma_nv, pw = create_employee_account(e["ma_nv"], e["ho_ten"])
        created.append((ma_nv, e["ho_ten"], pw))
    return created


# ---------------- Employees ----------------
def next_label_id():
    conn = _conn()
    row = conn.execute("SELECT MAX(label_id) m FROM employees").fetchone()
    conn.close()
    return (row["m"] or 0) + 1


def next_ma_nv():
    """Sinh mã NV kế tiếp dạng NVxxx. Quét toàn bộ mã NV hiện có (bỏ qua an
    toàn những mã không đúng định dạng NV+số, ví dụ mã đặt tay kiểu khác)
    thay vì chỉ nhìn dòng cuối cùng — tránh crash nếu có mã không chuẩn."""
    conn = _conn()
    rows = conn.execute("SELECT ma_nv FROM employees").fetchall()
    conn.close()
    max_n = 0
    for r in rows:
        ma = (r["ma_nv"] or "").strip()
        suffix = ma[2:] if ma.upper().startswith("NV") else ""
        if suffix.isdigit():
            max_n = max(max_n, int(suffix))
    return f"NV{max_n + 1:03d}"


def add_employee(data: dict):
    conn = _conn()
    conn.execute("""INSERT INTO employees
        (ma_nv, ho_ten, ngay_sinh, sdt, email, phong_ban, chuc_vu, ngay_vao_lam, trang_thai, anh_path, label_id)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (data["ma_nv"], data["ho_ten"], data.get("ngay_sinh"), data.get("sdt"), data.get("email"),
         data.get("phong_ban"), data.get("chuc_vu"), data.get("ngay_vao_lam"),
         data.get("trang_thai", "Đang làm"), data.get("anh_path"), data["label_id"]))
    conn.commit()
    conn.close()


def update_employee(ma_nv, data: dict):
    conn = _conn()
    conn.execute("""UPDATE employees SET ho_ten=?, ngay_sinh=?, sdt=?, email=?, phong_ban=?,
        chuc_vu=?, ngay_vao_lam=?, trang_thai=? WHERE ma_nv=?""",
        (data["ho_ten"], data.get("ngay_sinh"), data.get("sdt"), data.get("email"),
         data.get("phong_ban"), data.get("chuc_vu"), data.get("ngay_vao_lam"),
         data.get("trang_thai"), ma_nv))
    conn.commit()
    conn.close()


def delete_employee(ma_nv):
    conn = _conn()
    conn.execute("DELETE FROM employees WHERE ma_nv=?", (ma_nv,))
    conn.execute("DELETE FROM users WHERE username=? AND role='employee'", (ma_nv,))
    conn.commit()
    conn.close()


def get_employees(search="", phong_ban="Tất cả phòng ban", trang_thai="Tất cả trạng thái"):
    conn = _conn()
    q = "SELECT * FROM employees WHERE 1=1"
    params = []
    if search:
        q += " AND (ho_ten LIKE ? OR ma_nv LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if phong_ban and phong_ban != "Tất cả phòng ban":
        q += " AND phong_ban=?"
        params.append(phong_ban)
    if trang_thai and trang_thai != "Tất cả trạng thái":
        q += " AND trang_thai=?"
        params.append(trang_thai)
    q += " ORDER BY id"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_employee(ma_nv):
    conn = _conn()
    row = conn.execute("SELECT * FROM employees WHERE ma_nv=?", (ma_nv,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_departments():
    conn = _conn()
    rows = conn.execute("SELECT DISTINCT phong_ban FROM employees WHERE phong_ban IS NOT NULL").fetchall()
    conn.close()
    return [r["phong_ban"] for r in rows]


# ---------------- Attendance ----------------
def today_str():
    return date.today().strftime("%d/%m/%Y")


# Giờ hành chính chuẩn: vào lúc 08:00, về lúc 17:00 (so sánh dạng chuỗi "HH:MM:SS"
# nên có thể so sánh trực tiếp bằng >/< mà không cần parse datetime).
WORK_START_TIME = "08:00:00"
WORK_END_TIME = "17:00:00"


def compute_trang_thai(gio_vao, gio_ra=None):
    """Tính trạng thái chấm công dựa trên giờ vào/giờ ra:
    - Vào sau 08:00 => Đi muộn
    - Ra trước 17:00 (khi đã có giờ ra) => Về sớm
    - Nếu cả hai xảy ra cùng lúc => hiển thị gộp cả hai."""
    late = bool(gio_vao) and gio_vao > WORK_START_TIME
    early = bool(gio_ra) and gio_ra < WORK_END_TIME
    if late and early:
        return "Đi muộn & Về sớm"
    if late:
        return "Đi muộn"
    if early:
        return "Về sớm"
    return "Đúng giờ"


def get_today_attendance(ma_nv):
    conn = _conn()
    row = conn.execute("SELECT * FROM attendance WHERE ma_nv=? AND ngay=?",
                        (ma_nv, today_str())).fetchone()
    conn.close()
    return dict(row) if row else None


def check_in(ma_nv, photo_path):
    now = datetime.now()
    existing = get_today_attendance(ma_nv)
    if existing:
        return False, "Nhân viên đã chấm công vào hôm nay."
    gio_vao = now.strftime("%H:%M:%S")
    trang_thai = compute_trang_thai(gio_vao, None)
    conn = _conn()
    conn.execute("""INSERT INTO attendance (ma_nv, ngay, gio_vao, trang_thai, anh_vao)
                    VALUES (?,?,?,?,?)""",
                 (ma_nv, today_str(), gio_vao, trang_thai, photo_path))
    conn.commit()
    conn.close()
    return True, gio_vao


def check_out(ma_nv, photo_path):
    existing = get_today_attendance(ma_nv)
    if not existing:
        return False, "Nhân viên chưa chấm công vào hôm nay."
    now = datetime.now()
    gio_ra = now.strftime("%H:%M:%S")
    # Tính lại trạng thái dựa trên CẢ giờ vào (đã lưu) lẫn giờ ra vừa chấm,
    # để nếu vừa đi muộn vừa về sớm thì trạng thái hiển thị gộp cả hai.
    trang_thai = compute_trang_thai(existing["gio_vao"], gio_ra)
    conn = _conn()
    conn.execute("UPDATE attendance SET gio_ra=?, anh_ra=?, trang_thai=? WHERE id=?",
                 (gio_ra, photo_path, trang_thai, existing["id"]))
    conn.commit()
    conn.close()
    return True, gio_ra


def get_recent_activity(limit=6):
    conn = _conn()
    rows = conn.execute("""SELECT a.*, e.ho_ten FROM attendance a
        JOIN employees e ON a.ma_nv=e.ma_nv
        WHERE a.ngay=? ORDER BY a.id DESC LIMIT ?""", (today_str(), limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_today_stats():
    conn = _conn()
    total = conn.execute("SELECT COUNT(*) c FROM employees WHERE trang_thai='Đang làm'").fetchone()["c"]
    present = conn.execute("SELECT COUNT(*) c FROM attendance WHERE ngay=?", (today_str(),)).fetchone()["c"]
    late = conn.execute(
        "SELECT COUNT(*) c FROM attendance WHERE ngay=? AND trang_thai LIKE '%Đi muộn%'",
        (today_str(),)).fetchone()["c"]
    conn.close()
    absent = max(total - present, 0)
    return {"total": total, "present": present, "late": late, "absent": absent}


def get_history(tu_ngay=None, den_ngay=None, ma_nv=None, trang_thai=None):
    conn = _conn()
    q = """SELECT a.*, e.ho_ten FROM attendance a JOIN employees e ON a.ma_nv=e.ma_nv WHERE 1=1"""
    params = []
    if ma_nv and ma_nv != "Tất cả":
        q += " AND a.ma_nv=?"
        params.append(ma_nv)
    if trang_thai and trang_thai != "Tất cả":
        # Dùng LIKE để khớp cả trạng thái gộp, ví dụ lọc "Đi muộn" vẫn ra
        # được cả những dòng "Đi muộn & Về sớm".
        q += " AND a.trang_thai LIKE ?"
        params.append(f"%{trang_thai}%")
    q += " ORDER BY a.id DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    result = [dict(r) for r in rows]
    # simple date-range filter (dd/mm/yyyy stored as text)
    def parse(d):
        try:
            return datetime.strptime(d, "%d/%m/%Y")
        except Exception:
            return None
    if tu_ngay:
        result = [r for r in result if parse(r["ngay"]) and parse(r["ngay"]) >= tu_ngay]
    if den_ngay:
        result = [r for r in result if parse(r["ngay"]) and parse(r["ngay"]) <= den_ngay]
    return result


def get_monthly_report(month, year, phong_ban="Tất cả", ma_nv=None):
    conn = _conn()
    emp_q = "SELECT * FROM employees WHERE 1=1"
    params = []
    if ma_nv:
        emp_q += " AND ma_nv=?"
        params.append(ma_nv)
    elif phong_ban and phong_ban != "Tất cả":
        emp_q += " AND phong_ban=?"
        params.append(phong_ban)
    employees = [dict(r) for r in conn.execute(emp_q, params).fetchall()]
    report = []
    for e in employees:
        rows = conn.execute("SELECT * FROM attendance WHERE ma_nv=?", (e["ma_nv"],)).fetchall()
        so_ngay_cong, di_muon, ve_som, vang = 0, 0, 0, 0
        for r in rows:
            try:
                d = datetime.strptime(r["ngay"], "%d/%m/%Y")
            except Exception:
                continue
            if d.month != month or d.year != year:
                continue
            so_ngay_cong += 1
            trang = r["trang_thai"] or ""
            if "Đi muộn" in trang:
                di_muon += 1
            if "Về sớm" in trang:
                ve_som += 1
        report.append({"ho_ten": e["ho_ten"], "ma_nv": e["ma_nv"], "so_ngay_cong": so_ngay_cong,
                        "di_muon": di_muon, "ve_som": ve_som, "vang": vang})
    conn.close()
    return report
