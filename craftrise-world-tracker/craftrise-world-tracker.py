# -*- coding: utf-8 -*-
"""
CraftRise Discord RPC Canlı Okuyucu
RAM'i sürekli tarar, SET_ACTIVITY JSON'unu bulur,
alanları ayrıştırır ve değişince anında yazdırır.

Mapping:
  state        -> Dünya
  details      -> Mod
  small_text   -> KULLANICI ADI  (oda kodu DEĞİL!)
  large_image  -> Mod ikonu
  small_image  -> CraftRise logosu
"""

import ctypes
import ctypes.wintypes as wt
import json
import re
import sys
import time
import datetime
from pymem import Pymem

# ---------- Win32 sabitleri ----------
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_NOACCESS = 0x01
PAGE_GUARD = 0x100
PAGE_READONLY = 0x02
PAGE_READWRITE = 0x04
PAGE_WRITECOPY = 0x08
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_WRITECOPY = 0x80

READABLE_PROTECTS = {
    PAGE_READONLY, PAGE_READWRITE, PAGE_WRITECOPY,
    PAGE_EXECUTE_READ, PAGE_EXECUTE_READWRITE, PAGE_EXECUTE_WRITECOPY
}

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wt.DWORD),
        ("Protect", wt.DWORD),
        ("Type", wt.DWORD),
    ]

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.VirtualQueryEx.argtypes = [
    wt.HANDLE, ctypes.c_void_p,
    ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t
]
kernel32.VirtualQueryEx.restype = ctypes.c_size_t
kernel32.ReadProcessMemory.argtypes = [
    wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
]
kernel32.ReadProcessMemory.restype = wt.BOOL


# ---------- Yardımcılar ----------
def is_text_char(b: int) -> bool:
    return (32 <= b <= 126) or (0x80 <= b <= 0xFF)

def extract_full_string(buf: bytes, match_index: int, max_len: int = 2048) -> str:
    start = match_index
    while start > 0 and is_text_char(buf[start - 1]):
        start -= 1
    end = match_index
    n = len(buf)
    while end < n and is_text_char(buf[end]):
        end += 1
    end = min(end, start + max_len)
    return buf[start:end].decode("utf-8", errors="replace").strip()

def find_all_occurrences(haystack: bytes, needle: bytes):
    idx = 0
    while True:
        idx = haystack.find(needle, idx)
        if idx == -1:
            return
        yield idx
        idx += 1


# ---------- JSON ayrıştırma / mapping ----------
def parse_rpc_json(raw: str) -> dict:
    result = {
        "state": None, "details": None,
        "large_image": None, "large_text": None,
        "small_image": None, "small_text": None,
        "pid": None, "start_timestamp": None,
        # anlamlı alanlar
        "world": None, "mode": None,
        "username": None,   # <-- small_text = kullanıcı adı
    }

    def grab(key):
        m = re.search(rf'"{key}"\s*:\s*"([^"]*)"', raw)
        return m.group(1) if m else None

    def grab_int(key):
        m = re.search(rf'"{key}"\s*:\s*(\d+)', raw)
        return int(m.group(1)) if m else None

    result["state"] = grab("state")
    result["details"] = grab("details")
    result["large_image"] = grab("large_image")
    result["large_text"] = grab("large_text")
    result["small_image"] = grab("small_image")
    result["small_text"] = grab("small_text")
    result["pid"] = grab_int("pid")
    result["start_timestamp"] = grab_int("start")

    if result["state"]:
        result["world"] = result["state"].strip().rstrip(".")

    if result["details"]:
        d = result["details"].strip()
        m = re.match(r"(.+?)\s+oynuyor\.?$", d, re.IGNORECASE)
        result["mode"] = m.group(1).strip() if m else d

    # DÜZELTME: small_text oda kodu değil, KULLANICI ADI
    if result["small_text"]:
        result["username"] = result["small_text"].strip()

    return result


def format_status(m: dict) -> str:
    ts = ""
    if m.get("start_timestamp"):
        try:
            ts = datetime.datetime.fromtimestamp(m["start_timestamp"]).strftime("%H:%M:%S")
        except Exception:
            ts = str(m["start_timestamp"])

    lines = []
    lines.append("=" * 60)
    lines.append(f"  Kullanıcı : {m.get('username') or '?'}")
    lines.append(f"  Dünya     : {m.get('world') or '?'}")
    lines.append(f"  Mod       : {m.get('mode') or '?'}")
    lines.append(f"  PID       : {m.get('pid')}")
    if ts:
        lines.append(f"  Başlangıç : {ts}")
    lines.append("=" * 60)
    return "\n".join(lines)


# ---------- Tek seferlik RAM taraması ----------
def scan_once(h_proc, chunk_size: int = 64 * 1024 * 1024) -> list:
    """Bir kez tarar, benzersiz RPC durumlarını döndürür."""
    needle = b"SET_ACTIVITY"
    addr = 0
    max_addr = 0x7FFFFFFFFFFF
    mbi = MEMORY_BASIC_INFORMATION()
    mbi_size = ctypes.sizeof(mbi)

    results = []
    seen = set()

    while addr < max_addr:
        ret = kernel32.VirtualQueryEx(
            h_proc, ctypes.c_void_p(addr),
            ctypes.byref(mbi), mbi_size
        )
        if ret == 0:
            break

        base = mbi.BaseAddress or 0
        size = mbi.RegionSize
        if size == 0:
            break

        readable = (
            mbi.State == MEM_COMMIT
            and (mbi.Protect & PAGE_GUARD) == 0
            and mbi.Protect != PAGE_NOACCESS
            and mbi.Protect in READABLE_PROTECTS
        )

        if readable and size > 0:
            offset = 0
            while offset < size:
                to_read = min(chunk_size, size - offset)
                read_addr = base + offset

                buf = ctypes.create_string_buffer(to_read)
                bytes_read = ctypes.c_size_t(0)

                ok = kernel32.ReadProcessMemory(
                    h_proc, ctypes.c_void_p(read_addr),
                    buf, to_read, ctypes.byref(bytes_read)
                )
                if ok and bytes_read.value > 0:
                    data = buf.raw[:bytes_read.value]
                    for idx in find_all_occurrences(data, needle):
                        full = extract_full_string(data, idx)
                        js_start = full.find("{")
                        if js_start == -1:
                            continue
                        raw_json = full[js_start:]
                        m = parse_rpc_json(raw_json)

                        key = (m.get("world"), m.get("mode"),
                               m.get("username"), m.get("pid"))
                        if key in seen:
                            continue
                        seen.add(key)
                        m["_addr"] = read_addr + idx
                        results.append(m)
                offset += to_read

        next_addr = base + size
        if next_addr <= addr:
            break
        addr = next_addr

    return results


# ---------- Canlı okuma ----------
def live_monitor(pid: int, interval: float = 2.0):
    """
    RAM'i sürekli tarar. Durum değişince anında yazdırır.
    interval: iki tarama arası saniye (varsayılan 2 sn)
    """
    h_proc = kernel32.OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid
    )
    if not h_proc:
        raise OSError(f"OpenProcess başarısız (err={ctypes.get_last_error()}). "
                      f"Yönetici olarak çalıştır!")

    print(f"[*] Canlı izleme başladı (PID {pid}, {interval}s aralık)")
    print("[*] Durum değişince yazdırılacak. Ctrl+C ile durdur.\n")

    last_status = None
    last_change = time.time()

    try:
        while True:
            try:
                results = scan_once(h_proc)
            except Exception as e:
                print(f"[!] Tarama hatası: {e}")
                time.sleep(interval)
                continue

            # En güncel (en büyük timestamp) kaydı seç
            if results:
                current = max(
                    results,
                    key=lambda x: x.get("start_timestamp") or 0
                )
                status_key = (
                    current.get("username"),
                    current.get("world"),
                    current.get("mode"),
                    current.get("pid"),
                )

                if status_key != last_status:
                    if last_status is not None:
                        elapsed = time.time() - last_change
                        print(f"\n[!] DEĞİŞİKLİK ({elapsed:.1f}s sonra)")
                    print(format_status(current))
                    last_status = status_key
                    last_change = time.time()

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[*] İzleme durduruldu.")
    finally:
        kernel32.CloseHandle(h_proc)


# ---------- Main ----------
def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("╔══════════════════════════════════════════╗")
    print("║  CraftRise Discord RPC Canlı Okuyucu     ║")
    print("╚══════════════════════════════════════════╝\n")

    try:
        pm = Pymem("craftrise-x64.exe")
        print(f"[+] Process bulundu: {pm.process_id}")
    except Exception as e:
        print(f"[!] craftrise-x64.exe bulunamadı: {e}")
        sys.exit(1)

    try:
        interval = float(input("[?] Tarama aralığı saniye (varsayılan 2): ").strip() or "2")
    except ValueError:
        interval = 2.0

    live_monitor(pm.process_id, interval=interval)


if __name__ == "__main__":
    main()
