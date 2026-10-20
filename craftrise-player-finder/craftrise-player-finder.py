# -*- coding: utf-8 -*-
"""
CraftRise CANLI Oyuncu Tarayıcı - Arka Planda Sürekli Tarar
MC|Data{"3x7":[{"3x8":"...  pattern'ini otomatik arar.
Her oyuncu ismini SADECE 1 KEZ gösterir, tag/kozmetik göstermez.
Sürekli arka planda tarar, yeni oyuncu gelince anında basar.
"""

import ctypes
import ctypes.wintypes as wt
import sys
import re
import time
from datetime import datetime
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


# ---------- Regex ----------
PATTERN_3X8 = re.compile(
    rb'\{"3x7":\[\{"(?:4x5":\{[^}]*\},)?"3x8":"([^"]*)"'
)
PATTERN_4X5 = re.compile(
    rb'\{"3x7":\[\{"4x5":\{[^}]*\},"3x8":"([^"]*)"'
)


def scan_once(pid: int, seen: set, chunk_size: int = 64 * 1024 * 1024):
    """Tek bir tarama turu. Yeni isimleri basar, kaç yeni bulduğunu döner."""
    h_proc = kernel32.OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid
    )
    if not h_proc:
        raise OSError(f"OpenProcess başarısız (err={ctypes.get_last_error()}). "
                      f"Yönetici olarak çalıştır!")

    addr = 0
    max_addr = 0x7FFFFFFFFFFF
    mbi = MEMORY_BASIC_INFORMATION()
    mbi_size = ctypes.sizeof(mbi)
    yeni = 0

    try:
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

                        for m in PATTERN_3X8.finditer(data):
                            try:
                                isim = m.group(1).decode("utf-8", errors="replace")
                            except Exception:
                                continue
                            if not isim or len(isim) < 2:
                                continue
                            if isim in seen:
                                continue
                            seen.add(isim)
                            abs_addr = read_addr + m.start()
                            saat = datetime.now().strftime("%H:%M:%S")
                            print(f"[{saat}] 0x{abs_addr:016X}  ->  {isim}")
                            yeni += 1

                        for m in PATTERN_4X5.finditer(data):
                            try:
                                isim = m.group(1).decode("utf-8", errors="replace")
                            except Exception:
                                continue
                            if not isim or len(isim) < 2:
                                continue
                            if isim in seen:
                                continue
                            seen.add(isim)
                            abs_addr = read_addr + m.start()
                            saat = datetime.now().strftime("%H:%M:%S")
                            print(f"[{saat}] 0x{abs_addr:016X}  ->  {isim}")
                            yeni += 1

                    offset += to_read

            next_addr = base + size
            if next_addr <= addr:
                break
            addr = next_addr
    finally:
        kernel32.CloseHandle(h_proc)

    return yeni


def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("╔══════════════════════════════════════════╗")
    print("║   CraftRise CANLI Oyuncu Tarayıcı        ║")
    print("║   (Arka Planda Sürekli Tarar)            ║")
    print("╚══════════════════════════════════════════╝\n")

    try:
        pm = Pymem("craftrise-x64.exe")
        print(f"[+] Process bulundu: {pm.process_id}")
    except Exception as e:
        print(f"[!] craftrise-x64.exe bulunamadı: {e}")
        sys.exit(1)

    # Görülen isimler
    seen = set()
    tur = 0
    toplam = 0

    print("[*] CANLI tarama başladı. Yeni oyuncular anında basılacak.")
    print("[*] Çıkmak için Ctrl+C\n")

    try:
        while True:
            tur += 1
            baslangic = time.time()
            yeni = scan_once(pm.process_id, seen)
            sure = time.time() - baslangic

            toplam += yeni

            if yeni > 0:
                print(f"\n[Tur {tur}] {yeni} yeni oyuncu bulundu. "
                      f"(Toplam: {toplam}) ({sure:.2f}s)\n")
            else:
                # Ekranı doldurma, tek satırda bekle
                print(f"[Tur {tur}] Yeni yok. (Toplam: {toplam}) ({sure:.2f}s)", end="\r")

            time.sleep(0.5)  # 0.5 saniye bekle, sonra tekrar tara

    except KeyboardInterrupt:
        print(f"\n\n[!] Kullanıcı durdurdu. Toplam {toplam} oyuncu bulundu.")
    except Exception as e:
        print(f"\n[!] Hata: {e}")


if __name__ == "__main__":
    main()
