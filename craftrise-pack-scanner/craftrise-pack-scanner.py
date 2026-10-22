import os
import sys
import zipfile
import traceback
from pathlib import Path

AUTHOR = "ahmedglckc"
PROTECTION_KEY = "ahmedglckc-protection-v2"

SAFE_HIDDEN = {".DS_Store", "Thumbs.db", "desktop.ini", ".gitignore", ".gitkeep"}

SAFE_EXT = {
    "png","jpg","jpeg","gif","webp","bmp","tga","tif","tiff","ico",
    "mcmeta","json","ogg","wav","mp3","txt","md","cfg","properties",
    "lang","nbt","zip","mcpack","html","css","xml","yaml","yml","toml","csv"
}

EXEC_EXT = {
    "exe","dll","bat","cmd","ps1","vbs","vbe","js","jse","wsf","wsh",
    "scr","msi","msp","com","pif","lnk","url","hta","reg","cpl","msc",
    "jar","py","pyw","sh","bash","apk","app","deb","rpm","iso","img","bin"
}

RISK_LABELS = {
    0: "TEMİZ",
    1: "DÜŞÜK RİSK (muhtemelen zararsız)",
    2: "ORTA RİSK",
    3: "YÜKSEK RİSK",
    4: "VİRÜSLÜ",
}


def is_double_extension(name):
    base = Path(name).name
    parts = base.split(".")
    if len(parts) < 3:
        return False
    last = parts[-1].lower()
    prev = parts[-2].lower()
    return last in EXEC_EXT and prev in SAFE_EXT


def analyze_entry(name, is_dir=False):
    issues = []
    risk = 0
    base = Path(name).name

    if base in SAFE_HIDDEN:
        return issues, risk

    if is_double_extension(name):
        issues.append("ÇİFT UZANTI → KESİN VİRÜSLÜ")
        risk = 4
    else:
        ext = Path(name).suffix.lower()
        if not is_dir and ext in EXEC_EXT:
            issues.append(f"çalıştırılabilir dosya: {ext}")
            risk = max(risk, 3)

    if not is_dir:
        parts = Path(name).parts
        if any(p.startswith(".") and p not in (".", "..") for p in parts):
            issues.append("gizli dosya")
            risk = max(risk, 1)

    pstr = name.replace("\\", "/")
    if pstr.startswith("/") or ".." in pstr.split("/"):
        issues.append("şüpheli yol (path traversal)")
        risk = max(risk, 2)

    return issues, risk


def scan_zip(path):
    result = {"findings": [], "structure": [], "max_risk": 0, "total": 0, "error": None}
    try:
        with zipfile.ZipFile(path) as z:
            names = []
            for info in z.infolist():
                name = info.filename
                names.append(name)
                is_dir = name.endswith("/")
                if not is_dir:
                    result["total"] += 1
                issues, risk = analyze_entry(name, is_dir=is_dir)
                if not is_dir:
                    if info.file_size > 50 * 1024 * 1024:
                        issues.append("çok büyük dosya (>50 MB)")
                        risk = max(risk, 2)
                    if info.compress_size > 0 and info.file_size > 10 * 1024 * 1024:
                        ratio = info.file_size / max(info.compress_size, 1)
                        if ratio > 1000:
                            issues.append("yüksek sıkıştırma (zip bomb olabilir)")
                            risk = max(risk, 2)
                if issues:
                    result["findings"].append((name, issues, risk))
                    result["max_risk"] = max(result["max_risk"], risk)

            has_meta = any(n == "pack.mcmeta" or n.endswith("/pack.mcmeta") for n in names)
            has_assets = any(n.startswith("assets/") or "/assets/" in n for n in names)
            if not has_meta:
                result["structure"].append("pack.mcmeta yok")
                result["max_risk"] = max(result["max_risk"], 2)
            if not has_assets:
                result["structure"].append("assets/ klasörü yok")
                result["max_risk"] = max(result["max_risk"], 2)
    except zipfile.BadZipFile:
        result["error"] = "GEÇERSİZ ZIP/MCPACK"
    except PermissionError as e:
        result["error"] = f"Erişim reddedildi: {e}"
    except Exception as e:
        result["error"] = f"HATA: {e}"
    return result


def scan_folder(path):
    result = {"findings": [], "structure": [], "max_risk": 0, "total": 0, "error": None}
    has_meta = False
    has_assets = False
    try:
        for root, dirs, files in os.walk(path):
            for f in files:
                full = Path(root) / f
                try:
                    rel = full.relative_to(path).as_posix()
                except ValueError:
                    rel = str(full)
                result["total"] += 1
                if f == "pack.mcmeta":
                    has_meta = True
                if "assets" in Path(rel).parts:
                    has_assets = True
                issues, risk = analyze_entry(rel, is_dir=False)
                try:
                    if full.stat().st_size > 50 * 1024 * 1024:
                        issues.append("çok büyük dosya (>50 MB)")
                        risk = max(risk, 2)
                except OSError:
                    pass
                if issues:
                    result["findings"].append((rel, issues, risk))
                    result["max_risk"] = max(result["max_risk"], risk)
        if not has_meta:
            result["structure"].append("pack.mcmeta yok")
            result["max_risk"] = max(result["max_risk"], 2)
        if not has_assets:
            result["structure"].append("assets/ klasörü yok")
            result["max_risk"] = max(result["max_risk"], 2)
    except Exception as e:
        result["error"] = f"HATA: {e}"
    return result


def print_pack_report(name, result, path_str=None):
    print("\n" + "=" * 60)
    print(f" PACK: {name}")
    if path_str:
        print(f" Yol : {path_str}")

    if result["error"]:
        print(f" Durum: HATA - {result['error']}")
        print("=" * 60)
        return

    risk = result["max_risk"]
    label = RISK_LABELS.get(risk, "BİLİNMİYOR")
    print(f" Durum: {label}")
    print(f" Dosya sayısı: {result['total']}, Şüpheli: {len(result['findings'])}")

    if result["structure"]:
        print(" Yapı uyarıları:")
        for s in result["structure"]:
            print(f"   - {s}")

    if result["findings"]:
        print(" Bulgular (en riskli önce):")
        findings_sorted = sorted(result["findings"], key=lambda x: -x[2])
        for fname, issues, fr in findings_sorted[:20]:
            print(f"   [!] {fname}")
            for i in issues:
                print(f"        - {i}")
        if len(result["findings"]) > 20:
            print(f"   ... ve {len(result['findings']) - 20} bulgu daha")
    else:
        print(" Sorun bulunmadı.")
    print("=" * 60)


def scan_single(raw_path):
    raw_path = raw_path.strip().strip('"').strip("'")
    if not raw_path:
        print("[HATA] Boş yol.")
        return
    path = Path(raw_path).expanduser()
    if not path.exists():
        print(f"[HATA] Yol bulunamadı: {path}")
        return
    if path.is_dir():
        result = scan_folder(path)
        print_pack_report(path.name, result, str(path))
    elif path.is_file():
        result = scan_zip(path)
        print_pack_report(path.name, result, str(path))
    else:
        print(f"[HATA] Ne dosya ne klasör: {path}")


def get_craftrise_path():
    candidates = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / ".craftrise" / "resourcepacks")
    candidates.append(Path.home() / "AppData" / "Roaming" / ".craftrise" / "resourcepacks")
    for c in candidates:
        if c.is_dir():
            return c
    return None


def scan_craftrise(root):
    print(f"\nCraftRise klasörü taranıyor: {root}")
    packs = []

    try:
        entries = sorted(root.iterdir(), key=lambda p: p.name.lower())
    except PermissionError as e:
        print(f"[HATA] Klasör okunamadı: {e}")
        return

    for entry in entries:
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            packs.append((entry.name, scan_folder(entry), str(entry)))
        elif entry.suffix.lower() in (".zip", ".mcpack", ".jar"):
            packs.append((entry.name, scan_zip(entry), str(entry)))

    if not packs:
        print("Hiç pack bulunamadı.")
        return

    temiz = riskli = virüslü = 0

    for name, result, path_str in packs:
        print_pack_report(name, result, path_str)
        if result["error"]:
            riskli += 1
        elif result["max_risk"] == 4:
            virüslü += 1
        elif result["max_risk"] >= 2:
            riskli += 1
        else:
            temiz += 1

    print("\n" + "#" * 60)
    print(f"# ÖZET: {len(packs)} pack tarandı")
    print(f"#   Temiz  : {temiz}")
    print(f"#   Riskli : {riskli}")
    print(f"#   VİRÜSLÜ: {virüslü}")
    print("#" * 60)


def ahmedglckc_protection():
    print("=" * 60)
    print(f" {AUTHOR.upper()} KORUMASI AKTİF  [{PROTECTION_KEY}]")
    try:
        user = os.getlogin()
    except Exception:
        user = os.environ.get("USERNAME") or os.environ.get("USER") or "bilinmiyor"
    if user.lower() != AUTHOR.lower():
        print(f" Uyarı: Bu araç {AUTHOR} tarafından yazıldı.")
        print(f" Aktif kullanıcı: {user} (devam ediliyor)")
    else:
        print(f" Hoş geldin {AUTHOR}.")
    print("=" * 60)


def main():
    ahmedglckc_protection()

    print("\nNe taramak istiyorsun?")
    print("  [1] CraftRise resourcepacks klasörünü komple tara")
    print("  [2] Belirli bir texture pack (.zip / .mcpack / klasör)")

    while True:
        try:
            c = input("Seçim (1/2): ").strip()
        except EOFError:
            print("\n[EOF] Varsayılan (1) seçildi.")
            c = "1"
        if c in ("1", "2"):
            break
        print("Geçersiz, 1 veya 2 gir.")

    if c == "1":
        root = get_craftrise_path()
        if root is None:
            print("[!] CraftRise klasörü otomatik bulunamadı.")
            try:
                manual = input("resourcepacks klasör yolunu gir: ")
            except (EOFError, KeyboardInterrupt):
                print("İptal.")
                return
            manual = manual.strip().strip('"').strip("'")
            p = Path(manual).expanduser()
            if not p.is_dir():
                print(f"[HATA] Klasör değil / yok: {p}")
                return
            root = p
        scan_craftrise(root)
    else:
        try:
            raw = input("Pack yolu (.zip / .mcpack / klasör): ")
        except (EOFError, KeyboardInterrupt):
            print("İptal.")
            return
        scan_single(raw)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[İPTAL] Kullanıcı iptal etti.")
    except Exception as e:
        print(f"\n[KRİTİK HATA] {e}")
        traceback.print_exc()
    finally:
        try:
            input("\nKapatmak için Enter'a bas...")
        except (EOFError, KeyboardInterrupt):
            pass
