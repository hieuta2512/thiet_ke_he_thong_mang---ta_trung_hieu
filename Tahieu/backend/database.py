import sqlite3, os, datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "nms.db")
_UNSET = object()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def rows(cur): return [dict(r) for r in cur.fetchall()]
def row(cur):  r = cur.fetchone(); return dict(r) if r else None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, type TEXT NOT NULL, model TEXT,
    ip TEXT, vlan INTEGER, location TEXT,
    status TEXT DEFAULT 'online', uptime_hours INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS vlans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vlan_id INTEGER UNIQUE NOT NULL, name TEXT NOT NULL,
    network TEXT, gateway TEXT, dhcp_start TEXT, dhcp_end TEXT, description TEXT
);
CREATE TABLE IF NOT EXISTS cameras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, ip TEXT UNIQUE NOT NULL,
    location TEXT, model TEXT DEFAULT 'Hikvision DS-2CD2143G2-I',
    status TEXT DEFAULT 'online', bitrate REAL DEFAULT 5.0,
    resolution TEXT DEFAULT '2688x1520', codec TEXT DEFAULT 'H.265+',
    fps INTEGER DEFAULT 15, poe_power REAL DEFAULT 7.0, recording INTEGER DEFAULT 1,
    rtsp_url TEXT, hls_url TEXT, video_file TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    type TEXT NOT NULL, severity TEXT DEFAULT 'info',
    source_ip TEXT, dest_ip TEXT, vlan INTEGER,
    action TEXT, rule TEXT, message TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS acl_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_num INTEGER, list_name TEXT NOT NULL,
    action TEXT NOT NULL, protocol TEXT DEFAULT 'ip',
    src_net TEXT, dst_net TEXT, description TEXT
);
CREATE TABLE IF NOT EXISTS test_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
    category TEXT, status TEXT DEFAULT 'pending',
    last_result TEXT, last_run TEXT, expected TEXT, steps TEXT
);
CREATE TABLE IF NOT EXISTS dhcp_leases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip TEXT UNIQUE NOT NULL, mac TEXT, hostname TEXT,
    vlan INTEGER, lease_start TEXT, lease_end TEXT
);
"""

def init_db():
    with get_db() as conn:
        conn.executescript(_SCHEMA)
        _seed(conn)
        for col in ("rtsp_url TEXT", "hls_url TEXT", "video_file TEXT"):
            try: conn.execute(f"ALTER TABLE cameras ADD COLUMN {col}")
            except: pass

def _seed(c):
    if c.execute("SELECT COUNT(*) FROM acl_rules").fetchone()[0] > 0:
        return  # already seeded, skip to avoid duplicates
    devs = [
        ('ROUTER-FW','router','Cisco ISR 4221','10.0.0.2',None,'Phòng máy chủ','online',720),
        ('SW-CORE','switch-l3','Cisco Catalyst 3650-24PS','10.0.0.1',30,'Phòng máy chủ','online',720),
        ('SW-ACCESS-DATA','switch-l2','Cisco 2960X-24PD','192.168.30.11',30,'Tầng 1','online',720),
        ('SW-ACCESS-CAM','switch-l2','Cisco 2960X-24PD','192.168.30.12',30,'Phòng máy chủ','online',720),
        ('NVR','nvr','Hikvision DS-7608NI-K2','192.168.20.10',20,'Phòng máy chủ','online',720),
    ]
    for d in devs:
        c.execute("INSERT OR IGNORE INTO devices (name,type,model,ip,vlan,location,status,uptime_hours) VALUES (?,?,?,?,?,?,?,?)", d)

    vlans = [
        (10,'DATA','192.168.10.0/24','192.168.10.1','192.168.10.100','192.168.10.200','Máy tính văn phòng 30–50 PC'),
        (20,'CAMERA','192.168.20.0/24','192.168.20.1',None,None,'Camera IP & NVR — cô lập hoàn toàn'),
        (30,'MANAGEMENT','192.168.30.0/24','192.168.30.1',None,None,'Quản trị thiết bị mạng'),
        (40,'GUEST','192.168.40.0/24','192.168.40.1','192.168.40.100','192.168.40.200','Mạng khách WiFi'),
        (99,'NATIVE',None,None,None,None,'Native VLAN Trunk'),
    ]
    for v in vlans:
        c.execute("INSERT OR IGNORE INTO vlans (vlan_id,name,network,gateway,dhcp_start,dhcp_end,description) VALUES (?,?,?,?,?,?,?)", v)

    cams = [
        ('CAM-01','192.168.20.11','Cổng Chính'),('CAM-02','192.168.20.12','Sảnh Lễ Tân'),
        ('CAM-03','192.168.20.13','Khu Làm Việc A'),('CAM-04','192.168.20.14','Khu Làm Việc B'),
        ('CAM-05','192.168.20.15','Kho'),('CAM-06','192.168.20.16','Bãi Đỗ Xe'),
        ('CAM-07','192.168.20.17','Phòng Máy Chủ'),
    ]
    for cam in cams:
        c.execute("INSERT OR IGNORE INTO cameras (name,ip,location) VALUES (?,?,?)", cam)

    acls = [
        (10,'ACL-VLAN10-IN','deny','ip','192.168.10.0/24','192.168.20.0/24','Chặn Data → Camera'),
        (20,'ACL-VLAN10-IN','deny','ip','192.168.40.0/24','192.168.20.0/24','Chặn Guest → Camera'),
        (30,'ACL-VLAN10-IN','permit','ip','any','any','Cho phép traffic khác'),
        (10,'ACL-VLAN20-OUT','permit','ip','192.168.20.0/24','192.168.20.0/24','Camera nội bộ RTSP/ONVIF'),
        (20,'ACL-VLAN20-OUT','permit','udp','192.168.20.0/24','any/123','NTP đồng bộ thời gian'),
        (30,'ACL-VLAN20-OUT','permit','ip','192.168.30.0/24','192.168.20.0/24','Admin → Camera'),
        (40,'ACL-VLAN20-OUT','permit','ip','10.10.10.0/24','192.168.20.0/24','VPN Remote → Camera'),
        (50,'ACL-VLAN20-OUT','deny','ip','any','any','Chặn Camera → Internet'),
        (10,'FW-WAN-IN','permit','tcp','any','established','Return traffic'),
        (20,'FW-WAN-IN','permit','udp','any','203.0.113.2/500','IKE VPN'),
        (30,'FW-WAN-IN','permit','esp','any','203.0.113.2','IPSec ESP'),
        (40,'FW-WAN-IN','deny','ip','any','any','Block all inbound'),
    ]
    for a in acls:
        c.execute("INSERT OR IGNORE INTO acl_rules (rule_num,list_name,action,protocol,src_net,dst_net,description) VALUES (?,?,?,?,?,?,?)", a)

    tests = [
        ('TC-01','PC VLAN Data nhận IP DHCP đúng dải','Kết nối cơ bản','192.168.10.100–200, GW=192.168.10.1','Kết nối PC VLAN 10, chạy ip dhcp trên thiết bị'),
        ('TC-02','PC VLAN Data ping gateway thành công','Kết nối cơ bản','Ping 192.168.10.1: 4/4 Reply','ping 192.168.10.1 từ PC VLAN 10'),
        ('TC-03','PC VLAN Data truy cập Internet qua NAT','Kết nối cơ bản','Ping 8.8.8.8: 4/4, NAT translation active','ping 8.8.8.8, show ip nat translations'),
        ('TC-04','Camera nhận IP tĩnh, ping được NVR','VLAN Camera','Ping 192.168.20.10: 4/4','Cấu hình IP static camera, ping NVR'),
        ('TC-05','ACL Block: Data KHÔNG ping được Camera','Bảo mật ACL','100% loss, ACL log 4 matches','ping 192.168.20.10 từ PC VLAN Data'),
        ('TC-06','ACL Allow: Admin VLAN 30 truy cập NVR','Bảo mật ACL','Ping thành công, web NVR tải được','ping 192.168.20.10 từ Admin PC .30.10'),
        ('TC-07','Camera VLAN 20 không ra được Internet','Bảo mật ACL','100% loss khi ping 8.8.8.8','ping 8.8.8.8 từ thiết bị trong VLAN 20'),
        ('TC-08','Trunk 802.1Q hoạt động đúng VLAN list','Hạ tầng','Trunk active, VLANs đúng allowed list','show interfaces trunk trên SW-CORE'),
        ('TC-09','Port Security ngăn thiết bị MAC lạ','Bảo mật','Violation count tăng, port restrict mode','Cắm thiết bị MAC khác vào cổng secured'),
        ('TC-10','PoE cấp nguồn đúng công suất cho camera','PoE','7W/port, tổng 49W < 370W budget','show power inline SW-ACCESS-CAM'),
        ('TC-11','Kết nối VPN IPSec AES-256 thành công','VPN','IKE SA: QM_IDLE, IP pool=10.10.10.x','VPN client kết nối tới 203.0.113.2'),
        ('TC-12','Sau VPN truy cập được NVR từ xa','VPN','Ping 4/4, HTTP 200 NVR web','ping 192.168.20.10 từ VPN client'),
    ]
    for t in tests:
        c.execute("INSERT OR IGNORE INTO test_cases (code,name,category,expected,steps) VALUES (?,?,?,?,?)", t)

    evts = [
        ('info','info','192.168.10.100','8.8.8.8',10,'permit','ACL-VLAN10-IN','PC-01 VLAN Data ping Internet thành công'),
        ('warning','warning','192.168.10.105','192.168.20.10',10,'deny','ACL-VLAN10-IN rule 10','ACL BLOCKED: PC Data cố truy cập NVR'),
        ('info','info',None,None,None,'assign','DHCP','DHCP cấp IP 192.168.10.100 → PC-01'),
        ('info','info','10.10.10.1','192.168.20.10',None,'permit','VPN-SPLIT','VPN client kết nối, xem camera thành công'),
        ('warning','warning','192.168.20.11','8.8.8.8',20,'deny','ACL-VLAN20-OUT rule 50','Camera CAM-01 cố kết nối Internet — bị chặn'),
    ]
    for e in evts:
        c.execute("INSERT OR IGNORE INTO events (type,severity,source_ip,dest_ip,vlan,action,rule,message) VALUES (?,?,?,?,?,?,?,?)", e)

    leases = [
        ('192.168.10.100','00:50:79:66:68:00','PC-01',10),
        ('192.168.10.101','00:50:79:66:68:01','PC-02',10),
        ('192.168.10.102','00:50:79:66:68:02','PC-03',10),
        ('192.168.40.100','AA:BB:CC:DD:EE:01','GUEST-01',40),
    ]
    for l in leases:
        c.execute("INSERT OR IGNORE INTO dhcp_leases (ip,mac,hostname,vlan) VALUES (?,?,?,?)", l)

# ── DEVICES ──
def get_devices():
    with get_db() as c: return rows(c.execute("SELECT * FROM devices ORDER BY type,name"))
def get_device_by_id(did):
    with get_db() as c: return row(c.execute("SELECT * FROM devices WHERE id=?", (did,)))
def add_device(d):
    with get_db() as c:
        cur = c.execute("INSERT INTO devices (name,type,model,ip,vlan,location) VALUES (?,?,?,?,?,?)",
            (d['name'],d['type'],d.get('model'),d.get('ip'),d.get('vlan'),d.get('location')))
        return cur.lastrowid
def update_device(did, d):
    with get_db() as c:
        c.execute("UPDATE devices SET name=?,type=?,model=?,ip=?,vlan=?,location=?,status=? WHERE id=?",
            (d['name'],d['type'],d.get('model'),d.get('ip'),d.get('vlan'),d.get('location'),d.get('status','online'),did))
def delete_device(did):
    with get_db() as c: c.execute("DELETE FROM devices WHERE id=?", (did,))
def toggle_device_status(did, status):
    with get_db() as c: c.execute("UPDATE devices SET status=? WHERE id=?", (status, did))

# ── VLANS ──
def get_vlans():
    with get_db() as c: return rows(c.execute("SELECT * FROM vlans ORDER BY vlan_id"))

# ── CAMERAS ──
def get_cameras():
    with get_db() as c: return rows(c.execute("SELECT * FROM cameras ORDER BY name"))
def get_camera_by_id(cid):
    with get_db() as c: return row(c.execute("SELECT * FROM cameras WHERE id=?", (cid,)))
def update_camera_status(cid, status):
    with get_db() as c: c.execute("UPDATE cameras SET status=? WHERE id=?", (status, cid))

def set_camera_stream(cid, rtsp_url=_UNSET, hls_url=_UNSET, video_file=_UNSET):
    fields, vals = [], []
    if rtsp_url is not _UNSET: fields.append("rtsp_url=?"); vals.append(rtsp_url)
    if hls_url  is not _UNSET: fields.append("hls_url=?");  vals.append(hls_url)
    if video_file is not _UNSET: fields.append("video_file=?"); vals.append(video_file)
    if not fields: return
    with get_db() as c:
        c.execute(f"UPDATE cameras SET {','.join(fields)} WHERE id=?", vals + [cid])
def add_camera(d):
    with get_db() as c:
        cur = c.execute(
            "INSERT INTO cameras (name,ip,location,model,status,bitrate,resolution,codec,fps,poe_power,recording) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (d['name'],d['ip'],d.get('location'),d.get('model','Hikvision DS-2CD2143G2-I'),
             d.get('status','online'),d.get('bitrate',5.0),d.get('resolution','2688x1520'),
             d.get('codec','H.265+'),d.get('fps',15),d.get('poe_power',7.0),d.get('recording',1)))
        return cur.lastrowid

# ── EVENTS ──
def get_events(limit=50, severity=None):
    with get_db() as c:
        if severity:
            return rows(c.execute("SELECT * FROM events WHERE severity=? ORDER BY id DESC LIMIT ?", (severity, limit)))
        return rows(c.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)))
def add_event(etype, severity, src, dst, vlan, action, rule, message):
    with get_db() as c:
        c.execute("INSERT INTO events (type,severity,source_ip,dest_ip,vlan,action,rule,message) VALUES (?,?,?,?,?,?,?,?)",
            (etype, severity, src, dst, vlan, action, rule, message))

# ── ACL ──
def get_acl_rules():
    with get_db() as c: return rows(c.execute("SELECT * FROM acl_rules ORDER BY list_name, rule_num"))

# ── TESTS ──
def get_test_cases():
    with get_db() as c: return rows(c.execute("SELECT * FROM test_cases ORDER BY code"))
def get_test_by_id(tid):
    with get_db() as c: return row(c.execute("SELECT * FROM test_cases WHERE id=?", (tid,)))
def update_test_result(tid, status, result, ts):
    with get_db() as c:
        c.execute("UPDATE test_cases SET status=?,last_result=?,last_run=? WHERE id=?", (status,result,ts,tid))

# ── DHCP ──
def get_dhcp_leases():
    with get_db() as c: return rows(c.execute("SELECT * FROM dhcp_leases ORDER BY vlan,ip"))

# ── STATS ──
def get_stats():
    with get_db() as c:
        devices = c.execute("SELECT COUNT(*) as t, SUM(CASE WHEN status='online' THEN 1 ELSE 0 END) as on_ FROM devices").fetchone()
        cameras = c.execute("SELECT COUNT(*) as t, SUM(CASE WHEN status='online' THEN 1 ELSE 0 END) as on_ FROM cameras").fetchone()
        events  = c.execute("SELECT COUNT(*) as t, SUM(CASE WHEN severity='warning' OR severity='error' THEN 1 ELSE 0 END) as alerts FROM events").fetchone()
        tests   = c.execute("SELECT COUNT(*) as t, SUM(CASE WHEN status='pass' THEN 1 ELSE 0 END) as p FROM test_cases").fetchone()
        blocked = c.execute("SELECT COUNT(*) FROM events WHERE action='deny'").fetchone()[0]
        cam_online = cameras[1] or 0
        return {
            "devices_total": devices[0], "devices_online": devices[1] or 0,
            "cameras_total": cameras[0], "cameras_online": cam_online,
            "events_total": events[0], "alerts": events[1] or 0,
            "tests_total": tests[0], "tests_passed": tests[1] or 0,
            "packets_blocked": blocked,
            "cam_bw_mbps": round(cam_online * 5.0, 1),
            "packets_fwd": events[0] * 12 + 1200,
        }
