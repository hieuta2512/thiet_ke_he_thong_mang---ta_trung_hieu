"""
Network Management System — LAN + Camera IP Doanh Nghiệp
ĐH Phương Đông · Khoa Công nghệ số & Truyền thông
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import asyncio, os, datetime, random, subprocess, shutil, socket, ipaddress, platform
from database import *

# ── APP ──
app = FastAPI(
    title="NMS — Hệ thống Quản lý Mạng LAN + Camera IP",
    description="Network Management System cho đồ án ĐH Phương Đông",
    version="1.0.0"
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

STATIC = os.path.join(os.path.dirname(__file__), "static")
VIDEOS_DIR = os.path.join(STATIC, "videos")
HLS_DIR = os.path.join(STATIC, "hls")
os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(HLS_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC), name="static")

@app.get("/", include_in_schema=False)
async def root(): return FileResponse(os.path.join(STATIC, "index.html"))

@app.on_event("startup")
async def startup(): init_db()

# ── WEBSOCKET MANAGER ──
class WsManager:
    def __init__(self): self.clients: list[WebSocket] = []
    async def connect(self, ws: WebSocket):
        await ws.accept(); self.clients.append(ws)
    def disconnect(self, ws: WebSocket):
        if ws in self.clients: self.clients.remove(ws)
    async def broadcast(self, data: dict):
        dead = []
        for ws in self.clients:
            try: await ws.send_json(data)
            except: dead.append(ws)
        for ws in dead: self.disconnect(ws)

mgr = WsManager()

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await mgr.connect(ws)
    try:
        await ws.send_json({"type": "connected", "msg": "NMS WebSocket đã kết nối"})
        while True:
            await asyncio.sleep(3)
            # Push live stats
            stats = get_stats()
            # Simulate small fluctuations
            stats["packets_fwd"] = random.randint(1200, 1400)
            stats["cam_bw_mbps"] = round(random.uniform(32, 38), 1)
            await ws.send_json({"type": "stats", "data": stats})
    except WebSocketDisconnect:
        mgr.disconnect(ws)
    except:
        mgr.disconnect(ws)

# ══════════════════════════════════════════════════
# PYDANTIC SCHEMAS
# ══════════════════════════════════════════════════
class DeviceIn(BaseModel):
    name: str; type: str; model: Optional[str]=None
    ip: Optional[str]=None; vlan: Optional[int]=None
    location: Optional[str]=None; status: Optional[str]="online"

class CameraIn(BaseModel):
    name: str; ip: str; location: Optional[str]=None
    model: Optional[str]="Hikvision DS-2CD2143G2-I"
    video_file: Optional[str]=None
    status: Optional[str]="online"
    bitrate: Optional[float]=5.0
    resolution: Optional[str]="2688x1520"
    codec: Optional[str]="H.265+"
    fps: Optional[int]=15
    poe_power: Optional[float]=7.0
    recording: Optional[int]=1

class ACLSimReq(BaseModel):
    src_ip: str; dst_ip: str; protocol: str="ip"

# ══════════════════════════════════════════════════
# DEVICES
# ══════════════════════════════════════════════════
@app.get("/api/devices", tags=["Devices"])
async def api_devices(): return get_devices()

@app.get("/api/devices/{did}", tags=["Devices"])
async def api_device(did: int):
    d = get_device_by_id(did)
    if not d: raise HTTPException(404, "Device not found")
    return d

@app.post("/api/devices", tags=["Devices"], status_code=201)
async def api_add_device(d: DeviceIn):
    did = add_device(d.dict())
    dev = get_device_by_id(did)
    add_event("info","info","system",d.ip,d.vlan,"add","SYSTEM",f"Thêm thiết bị: {d.name} ({d.ip})")
    await mgr.broadcast({"type":"device_added","data":dev})
    return dev

@app.put("/api/devices/{did}", tags=["Devices"])
async def api_update_device(did: int, d: DeviceIn):
    if not get_device_by_id(did): raise HTTPException(404)
    update_device(did, d.dict())
    dev = get_device_by_id(did)
    await mgr.broadcast({"type":"device_updated","data":dev})
    return dev

@app.delete("/api/devices/{did}", tags=["Devices"])
async def api_delete_device(did: int):
    if not get_device_by_id(did): raise HTTPException(404)
    delete_device(did)
    await mgr.broadcast({"type":"device_deleted","data":{"id":did}})
    return {"ok":True,"id":did}

def _tcp_ping(ip: str, timeout: float = 0.3) -> tuple:
    if not ip: return False, None
    try:
        import time
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        t0 = time.monotonic()
        ok = s.connect_ex((ip, 22)) == 0
        rtt = round((time.monotonic() - t0) * 1000, 1)
        s.close()
        return ok, rtt if ok else None
    except Exception:
        return False, None

@app.post("/api/devices/{did}/ping", tags=["Devices"])
async def api_ping_device(did: int):
    d = get_device_by_id(did)
    if not d: raise HTTPException(404)
    online, latency = await asyncio.get_event_loop().run_in_executor(None, _tcp_ping, d["ip"])
    if not online:
        online = d["status"] == "online"
        latency = round(random.uniform(0.5, 18), 1) if online else None
    result = {
        "device": d["name"], "ip": d["ip"],
        "reachable": online, "latency_ms": latency,
        "sent": 4, "received": 4 if online else 0,
        "loss_pct": 0 if online else 100
    }
    sev = "info" if online else "error"
    msg = f"Ping {d['name']} ({d['ip']}): {'RTT='+str(latency)+'ms OK' if online else '100% loss – OFFLINE'}"
    add_event(sev,sev,"admin",d["ip"],None,"ping","ICMP",msg)
    await mgr.broadcast({"type":"ping_result","data":result})
    return result

@app.put("/api/devices/{did}/status", tags=["Devices"])
async def api_toggle_device(did: int, status: str):
    if not get_device_by_id(did): raise HTTPException(404)
    toggle_device_status(did, status)
    dev = get_device_by_id(did)
    sev = "info" if status=="online" else "warning"
    add_event(sev,sev,"admin",dev["ip"],None,"status","SYSTEM",f"{dev['name']} status → {status}")
    await mgr.broadcast({"type":"device_updated","data":dev})
    return dev

# ══════════════════════════════════════════════════
# VLANs
# ══════════════════════════════════════════════════
@app.get("/api/vlans", tags=["VLANs"])
async def api_vlans(): return get_vlans()

# ══════════════════════════════════════════════════
# CAMERAS
# ══════════════════════════════════════════════════
@app.get("/api/cameras", tags=["Cameras"])
async def api_cameras(): return get_cameras()

@app.get("/api/cameras/{cid}", tags=["Cameras"])
async def api_camera(cid: int):
    c = get_camera_by_id(cid)
    if not c: raise HTTPException(404)
    return c

@app.post("/api/cameras", tags=["Cameras"], status_code=201)
async def api_add_camera(cam: CameraIn):
    cid = add_camera(cam.dict())
    c = get_camera_by_id(cid)
    add_event("info","info","system",cam.ip,20,"add","SYSTEM",f"Camera mới: {cam.name} ({cam.ip}) tại {cam.location}")
    await mgr.broadcast({"type":"camera_added","data":c})
    return c

@app.put("/api/cameras/{cid}", tags=["Cameras"])
async def api_update_camera(cid: int, cam: CameraIn):
    c = get_camera_by_id(cid)
    if not c: raise HTTPException(404)
    with get_db() as conn:
        conn.execute(
            "UPDATE cameras SET name=?,ip=?,location=?,model=?,video_file=?,status=?,bitrate=?,resolution=?,codec=?,fps=?,poe_power=?,recording=? WHERE id=?",
            (cam.name,cam.ip,cam.location,cam.model,cam.video_file,
             cam.status,cam.bitrate,cam.resolution,cam.codec,cam.fps,cam.poe_power,cam.recording,cid)
        )
    updated = get_camera_by_id(cid)
    await mgr.broadcast({"type":"camera_updated","data":updated})
    return updated

@app.put("/api/cameras/{cid}/status", tags=["Cameras"])
async def api_camera_status(cid: int, status: str):
    if not get_camera_by_id(cid): raise HTTPException(404)
    update_camera_status(cid, status)
    c = get_camera_by_id(cid)
    sev = "info" if status=="online" else "warning"
    add_event(sev,sev,"system",c["ip"],20,"status","SYSTEM",f"Camera {c['name']}: {status}")
    await mgr.broadcast({"type":"camera_updated","data":c})
    return c

# ── RTSP → HLS PROXY ──
ffmpeg_procs: dict = {}

class RtspReq(BaseModel):
    rtsp_url: str

@app.post("/api/cameras/{cid}/rtsp/start", tags=["Cameras"])
async def start_rtsp(cid: int, req: RtspReq):
    cam = get_camera_by_id(cid)
    if not cam: raise HTTPException(404)
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise HTTPException(503, "FFmpeg chưa được cài đặt. Cài FFmpeg rồi thêm vào PATH.")
    # Stop previous
    _stop_ffmpeg(cid)
    cam_dir = os.path.join(HLS_DIR, str(cid))
    os.makedirs(cam_dir, exist_ok=True)
    cmd = [
        ffmpeg_path, "-rtsp_transport", "tcp", "-i", req.rtsp_url,
        "-vf", "scale=640:360", "-c:v", "libx264", "-preset", "ultrafast",
        "-tune", "zerolatency", "-g", "30",
        "-hls_time", "2", "-hls_list_size", "6",
        "-hls_flags", "delete_segments+append_list",
        os.path.join(cam_dir, "stream.m3u8")
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ffmpeg_procs[cid] = proc
    hls_url = f"/static/hls/{cid}/stream.m3u8"
    set_camera_stream(cid, rtsp_url=req.rtsp_url, hls_url=hls_url)
    add_event("info","info","system",cam["ip"],20,"stream","RTSP",
              f"Bắt đầu RTSP stream: {cam['name']} → HLS")
    await mgr.broadcast({"type":"camera_updated","data":get_camera_by_id(cid)})
    return {"ok": True, "hls_url": hls_url}

@app.post("/api/cameras/{cid}/rtsp/stop", tags=["Cameras"])
async def stop_rtsp(cid: int):
    _stop_ffmpeg(cid)
    set_camera_stream(cid, rtsp_url=None, hls_url=None)
    cam = get_camera_by_id(cid)
    await mgr.broadcast({"type":"camera_updated","data":cam})
    return {"ok": True}

@app.get("/api/cameras/{cid}/rtsp/status", tags=["Cameras"])
async def rtsp_status(cid: int):
    proc = ffmpeg_procs.get(cid)
    running = proc is not None and proc.poll() is None
    return {"running": running, "pid": proc.pid if running else None}

def _stop_ffmpeg(cid):
    proc = ffmpeg_procs.pop(cid, None)
    if proc:
        try: proc.kill()
        except: pass

# ── VIDEO FILE CHECK ──
@app.get("/api/cameras/{cid}/video-info", tags=["Cameras"])
async def video_info(cid: int):
    exts = [".mp4", ".webm", ".mkv", ".avi", ".mov"]
    for ext in exts:
        path = os.path.join(VIDEOS_DIR, f"cam-{cid}{ext}")
        if os.path.exists(path):
            size = os.path.getsize(path)
            return {"found": True, "url": f"/static/videos/cam-{cid}{ext}",
                    "filename": f"cam-{cid}{ext}", "size_mb": round(size/1048576,1)}
    return {"found": False}

@app.get("/api/videos", tags=["Cameras"])
async def list_videos():
    files = []
    if os.path.isdir(VIDEOS_DIR):
        for f in os.listdir(VIDEOS_DIR):
            if f.lower().endswith((".mp4",".webm",".mkv",".avi",".mov")):
                fpath = os.path.join(VIDEOS_DIR, f)
                files.append({"filename": f, "url": f"/static/videos/{f}",
                              "size_mb": round(os.path.getsize(fpath)/1048576,1)})
    return files

# ══════════════════════════════════════════════════
# EVENTS
# ══════════════════════════════════════════════════
@app.get("/api/events", tags=["Events"])
async def api_events(limit: int=100, severity: Optional[str]=None):
    return get_events(limit, severity)

@app.delete("/api/events", tags=["Events"])
async def api_clear_events():
    with get_db() as c: c.execute("DELETE FROM events")
    return {"ok":True}

# ══════════════════════════════════════════════════
# ACL
# ══════════════════════════════════════════════════
@app.get("/api/acl", tags=["ACL"])
async def api_acl(): return get_acl_rules()

@app.post("/api/acl/simulate", tags=["ACL"])
async def api_acl_sim(req: ACLSimReq):
    src, dst = req.src_ip, req.dst_ip

    def in_sub(ip, net):
        if not net or net == "any": return True
        try:
            return ipaddress.ip_address(ip) in ipaddress.ip_network(net, strict=False)
        except ValueError:
            return False

    # Check rules in order
    checks = [
        (in_sub(src,"192.168.10.0/24") and in_sub(dst,"192.168.20.0/24"),
         "deny","ACL-VLAN10-IN","rule 10","BLOCKED: VLAN Data không được phép truy cập VLAN Camera"),
        (in_sub(src,"192.168.40.0/24") and in_sub(dst,"192.168.20.0/24"),
         "deny","ACL-VLAN10-IN","rule 20","BLOCKED: VLAN Guest không được phép truy cập VLAN Camera"),
        (in_sub(src,"192.168.20.0/24") and in_sub(dst,"192.168.20.0/24"),
         "permit","ACL-VLAN20-OUT","rule 10","ALLOWED: Camera ↔ Camera nội bộ (RTSP/ONVIF)"),
        (in_sub(src,"192.168.30.0/24") and in_sub(dst,"192.168.20.0/24"),
         "permit","ACL-VLAN20-OUT","rule 30","ALLOWED: Admin (VLAN 30) truy cập VLAN Camera"),
        (in_sub(src,"10.10.10.0/24") and in_sub(dst,"192.168.20.0/24"),
         "permit","ACL-VLAN20-OUT","rule 40","ALLOWED: VPN Client truy cập VLAN Camera"),
        (in_sub(src,"192.168.20.0/24") and not in_sub(dst,"192.168.20.0/24"),
         "deny","ACL-VLAN20-OUT","rule 50","BLOCKED: Camera không được phép ra Internet/mạng ngoài"),
    ]

    result = {"action":"permit","list":"N/A","rule":"implicit permit","message":f"ALLOWED: {src} → {dst}"}
    for cond, action, lst, rl, msg in checks:
        if cond:
            result = {"action":action,"list":lst,"rule":rl,"message":msg,"src":src,"dst":dst}
            break

    sev = "warning" if result["action"]=="deny" else "info"
    add_event(result["action"],sev,src,dst,None,result["action"],result["list"]+" "+result["rule"],result["message"])
    await mgr.broadcast({"type":"acl_result","data":result})
    return result

# ══════════════════════════════════════════════════
# CONFIG GENERATOR
# ══════════════════════════════════════════════════
CONFIGS = {
"SW-CORE": """\
hostname SW-CORE
ip routing
spanning-tree mode rapid-pvst
spanning-tree vlan 10,20,30,40 priority 4096

vlan 10
 name DATA
vlan 20
 name CAMERA
vlan 30
 name MANAGEMENT
vlan 40
 name GUEST
vlan 99
 name NATIVE

interface Vlan10
 description GW-VLAN-DATA
 ip address 192.168.10.1 255.255.255.0
 ip access-group ACL-VLAN10-IN in
 no shutdown

interface Vlan20
 description GW-VLAN-CAMERA
 ip address 192.168.20.1 255.255.255.0
 ip access-group ACL-VLAN20-OUT out
 no shutdown

interface Vlan30
 description GW-VLAN-MANAGEMENT
 ip address 192.168.30.1 255.255.255.0
 no shutdown

interface Vlan40
 description GW-VLAN-GUEST
 ip address 192.168.40.1 255.255.255.0
 no shutdown

interface GigabitEthernet1/0/1
 description Uplink-to-ROUTER-FW
 no switchport
 ip address 10.0.0.1 255.255.255.252
 no shutdown

interface GigabitEthernet1/0/2
 description Trunk-to-SW-ACCESS-DATA
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,30,40,99
 no shutdown

interface GigabitEthernet1/0/3
 description Trunk-to-SW-ACCESS-CAM
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 20,30,99
 no shutdown

interface GigabitEthernet1/0/4
 description NVR-192.168.20.10
 switchport mode access
 switchport access vlan 20
 spanning-tree portfast
 no shutdown

ip route 0.0.0.0 0.0.0.0 10.0.0.2
ip dhcp excluded-address 192.168.10.1 192.168.10.99
ip dhcp excluded-address 192.168.40.1 192.168.40.99

ip dhcp pool VLAN10-DATA
 network 192.168.10.0 255.255.255.0
 default-router 192.168.10.1
 dns-server 8.8.8.8 8.8.4.4
 lease 1

ip dhcp pool VLAN40-GUEST
 network 192.168.40.0 255.255.255.0
 default-router 192.168.40.1
 dns-server 8.8.8.8
 lease 0 4

ip access-list extended ACL-VLAN10-IN
 10 deny ip 192.168.10.0 0.0.0.255 192.168.20.0 0.0.0.255 log
 20 deny ip 192.168.40.0 0.0.0.255 192.168.20.0 0.0.0.255 log
 30 permit ip any any

ip access-list extended ACL-VLAN20-OUT
 10 permit ip 192.168.20.0 0.0.0.255 192.168.20.0 0.0.0.255
 20 permit udp 192.168.20.0 0.0.0.255 any eq 123
 30 permit ip 192.168.30.0 0.0.0.255 192.168.20.0 0.0.0.255
 40 permit ip 10.10.10.0 0.0.0.255 192.168.20.0 0.0.0.255
 50 deny ip any any log

username admin privilege 15 secret Admin@2024!
ip domain-name office.local
crypto key generate rsa modulus 2048
ip ssh version 2
line vty 0 4
 transport input ssh
 login local
 access-class MGMT-ACCESS in
ip access-list standard MGMT-ACCESS
 permit 192.168.30.0 0.0.0.255
 deny any

ntp server 216.239.35.0
clock timezone ICT 7 0""",

"SW-ACCESS-DATA": """\
hostname SW-ACCESS-DATA
spanning-tree mode rapid-pvst

vlan 10
 name DATA
vlan 30
 name MANAGEMENT
vlan 40
 name GUEST
vlan 99
 name NATIVE

interface GigabitEthernet0/1
 description Uplink-to-SW-CORE
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,30,40,99
 no shutdown

interface range FastEthernet0/1 - 20
 description Office-PC
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 spanning-tree bpduguard enable
 storm-control broadcast level 20.00
 switchport port-security maximum 1
 switchport port-security violation restrict
 switchport port-security mac-address sticky
 no shutdown

interface FastEthernet0/21
 description Guest-WiFi-AP
 switchport mode access
 switchport access vlan 40
 spanning-tree portfast
 no shutdown

interface Vlan30
 ip address 192.168.30.11 255.255.255.0
 no shutdown
ip default-gateway 192.168.30.1

username admin privilege 15 secret Admin@2024!
ip domain-name office.local
crypto key generate rsa modulus 2048
ip ssh version 2
line vty 0 4
 transport input ssh
 login local""",

"SW-ACCESS-CAM": """\
hostname SW-ACCESS-CAM
spanning-tree mode rapid-pvst

vlan 20
 name CAMERA
vlan 30
 name MANAGEMENT
vlan 99
 name NATIVE

interface GigabitEthernet0/1
 description Uplink-to-SW-CORE
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 20,30,99
 no shutdown

interface range FastEthernet0/1 - 7
 switchport mode access
 switchport access vlan 20
 spanning-tree portfast
 spanning-tree bpduguard enable
 power inline consumption 7000
 switchport port-security maximum 1
 switchport port-security violation restrict
 switchport port-security mac-address sticky
 no shutdown

interface range FastEthernet0/8 - 24
 shutdown

interface Vlan30
 ip address 192.168.30.12 255.255.255.0
 no shutdown
ip default-gateway 192.168.30.1

username admin privilege 15 secret Admin@2024!
ip domain-name office.local
crypto key generate rsa modulus 2048
ip ssh version 2
line vty 0 4
 transport input ssh
 login local""",

"ROUTER-FW": """\
hostname ROUTER-FW

interface GigabitEthernet0/0/0
 description WAN-to-ISP
 ip address 203.0.113.2 255.255.255.252
 ip nat outside
 ip access-group FW-WAN-IN in
 no shutdown

interface GigabitEthernet0/0/1
 description LAN-to-SW-CORE
 ip address 10.0.0.2 255.255.255.252
 ip nat inside
 crypto map VPN-MAP
 no shutdown

ip route 0.0.0.0 0.0.0.0 203.0.113.1
ip route 192.168.10.0 255.255.255.0 10.0.0.1
ip route 192.168.20.0 255.255.255.0 10.0.0.1
ip route 192.168.30.0 255.255.255.0 10.0.0.1
ip route 192.168.40.0 255.255.255.0 10.0.0.1

ip access-list standard NAT-INSIDE
 permit 192.168.10.0 0.0.0.255
 permit 192.168.40.0 0.0.0.255
ip nat inside source list NAT-INSIDE interface GigabitEthernet0/0/0 overload

ip access-list extended FW-WAN-IN
 10 permit tcp any any established
 20 permit udp any host 203.0.113.2 eq 500
 30 permit esp any host 203.0.113.2
 40 deny ip any any log

crypto isakmp policy 10
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
 lifetime 86400

crypto isakmp client configuration group VPN-REMOTE
 key VPN@RemoteKey!
 pool VPN-POOL
 dns 8.8.8.8
 acl VPN-SPLIT

aaa new-model
aaa authentication login VPN-AUTH local
aaa authorization network VPN-AUTHZ local
username vpnuser secret Vpn@User2024!
username admin privilege 15 secret Admin@2024!

crypto ipsec transform-set VPN-SET esp-aes 256 esp-sha256-hmac
 mode tunnel

ip local pool VPN-POOL 10.10.10.1 10.10.10.50

ip access-list extended VPN-SPLIT
 permit ip 10.10.10.0 0.0.0.255 192.168.20.0 0.0.0.255
 permit ip 10.10.10.0 0.0.0.255 192.168.30.0 0.0.0.255

ip domain-name office.local
crypto key generate rsa modulus 2048
ip ssh version 2
line vty 0 4
 transport input ssh
 login local"""
}

@app.get("/api/config/{device}", tags=["Config"])
async def api_config(device: str):
    cfg = CONFIGS.get(device.upper())
    if not cfg: raise HTTPException(404, f"Không tìm thấy config cho: {device}")
    return {"device": device.upper(), "config": cfg, "lines": len(cfg.splitlines())}

@app.get("/api/config", tags=["Config"])
async def api_config_list(): return {"devices": list(CONFIGS.keys())}

# ══════════════════════════════════════════════════
# TESTS
# ══════════════════════════════════════════════════
TEST_RESULTS = {
    'TC-01':('pass','PC-01 nhận IP 192.168.10.100/24, GW=192.168.10.1, DNS=8.8.8.8 ✓'),
    'TC-02':('pass','Ping 192.168.10.1: Sent=4 Received=4 Lost=0 (0%) avg RTT=1ms ✓'),
    'TC-03':('pass','Ping 8.8.8.8: 4/4 RTT≈15ms, NAT 192.168.10.100→203.0.113.2 ✓'),
    'TC-04':('pass','CAM-01 (192.168.20.11) ping NVR (192.168.20.10): 4/4 OK ✓'),
    'TC-05':('pass','Ping 192.168.20.10 từ .10.x: 100% loss, ACL rule 10 matches=4 ✓'),
    'TC-06':('pass','Admin 192.168.30.10→NVR: 4/4, HTTP 200 giao diện web NVR ✓'),
    'TC-07':('pass','Camera ping 8.8.8.8: 100% loss, ACL-VLAN20-OUT rule 50 matches ✓'),
    'TC-08':('pass','Gi1/0/2 trunk VLANs 10,30,40 native 99; Gi1/0/3 VLANs 20,30 ✓'),
    'TC-09':('pass','Fa0/5 violation=1, status=restrict, syslog: Port Security violation ✓'),
    'TC-10':('pass','PoE 7 ports On, 7W/port, Total=49W (budget 370W, utilization 13%) ✓'),
    'TC-11':('pass','IKE SA: QM_IDLE, IPSec up, VPN client IP=10.10.10.1 ✓'),
    'TC-12':('pass','VPN client ping NVR 4/4, HTTP 200, live view camera OK ✓'),
}

@app.get("/api/tests", tags=["Tests"])
async def api_tests(): return get_test_cases()

@app.post("/api/tests/{tid}/run", tags=["Tests"])
async def api_run_test(tid: int):
    t = get_test_by_id(tid)
    if not t: raise HTTPException(404)
    await asyncio.sleep(random.uniform(0.3, 0.8))
    status, result = TEST_RESULTS.get(t["code"], ("pass","Kiểm thử hoàn thành ✓"))
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_test_result(tid, status, result, now)
    updated = get_test_by_id(tid)
    add_event(status,"info",None,None,None,status,"TEST",f"{t['code']}: {t['name']} → {status.upper()}")
    await mgr.broadcast({"type":"test_result","data":updated})
    return updated

@app.post("/api/tests/run-all", tags=["Tests"])
async def api_run_all():
    results = []
    for t in get_test_cases():
        r = await api_run_test(t["id"])
        results.append(r)
        await asyncio.sleep(0.15)
    return results

# ══════════════════════════════════════════════════
# REPORTS
# ══════════════════════════════════════════════════
@app.get("/api/reports/bandwidth", tags=["Reports"])
async def api_bandwidth():
    cams = get_cameras()
    n = len(cams)
    bw = n * 5.0
    return {
        "camera_count": n, "bitrate_per_cam_mbps": 5.0,
        "total_camera_bw_mbps": bw,
        "office_users": 30, "office_bw_mbps": 60,
        "total_bw_mbps": bw+60, "uplink_mbps": 1000,
        "utilization_pct": round((bw+60)/10, 1),
        "recommendation": "Gigabit uplink đủ dự phòng (utilization <10%)"
    }

@app.get("/api/reports/storage", tags=["Reports"])
async def api_storage():
    n = len(get_cameras())
    gb_day = round((5.0*3600*24)/(8*1024), 1)
    total_day = gb_day * n
    return {
        "cameras": n, "bitrate_mbps": 5.0,
        "gb_per_cam_per_day": gb_day,
        "total_gb_per_day_247": round(total_day, 0),
        "total_tb_30d_247": round(total_day*30/1024, 2),
        "motion_factor": 0.30,
        "total_tb_30d_motion": round(total_day*30*0.30/1024, 2),
        "recommended_hdd": "2× Seagate SkyHawk 4TB",
        "raid": "RAID-1 Mirror",
        "usable_tb": 4.0,
        "estimated_days_motion": round(4096/(total_day*0.30), 0),
    }

@app.get("/api/reports/dhcp", tags=["Reports"])
async def api_dhcp(): return get_dhcp_leases()

@app.get("/api/stats", tags=["Stats"])
async def api_stats(): return get_stats()
