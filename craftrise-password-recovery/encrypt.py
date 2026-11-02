"""
bak.py — CraftRise launcher config yazici
tersi.py'deki DOGRU enc formatini kullanir:
    enc = b64(AES(b64(b64(pre + b64(sifre) + suf))))

Kullanim:
    python bak.py
    python bak.py kullaniciadi sifre

NOT: Launcher ACIKSA once kapatin.
"""

import base64
import json
import os
import shutil
import sys
import traceback

ENDPOINT = "https://craftrise.net.tr/client/launcher/user/api"
_AES_KEY = b"2640023187059250"


# ----------------------------------------------------------------
# enc uret — tersi.py ile AYNI format
# ----------------------------------------------------------------
def enc_uret(sifre):
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad
        pre, suf = "3ebi2mclmAM7Ao2", "KweGTngiZOOj9d6"

        b64_sifre = base64.b64encode(sifre.encode()).decode()
        wrapped   = pre + b64_sifre + suf
        s1        = base64.b64encode(wrapped.encode()).decode()
        s2        = base64.b64encode(s1.encode()).decode()

        c   = AES.new(_AES_KEY, AES.MODE_ECB)
        aes = c.encrypt(pad(s2.encode(), AES.block_size))
        return base64.b64encode(aes).decode()
    except ImportError:
        print("[!] pycryptodome kurulu degil: pip install pycryptodome")
        return ""
    except Exception as e:
        print("[!] enc_uret hatasi:", e)
        return ""


# ----------------------------------------------------------------
# Launcher config'e yaz + dogrula
# ----------------------------------------------------------------
def kaydet(username, enc_yerel):
    appdata = os.environ.get("APPDATA")
    if not appdata:
        print("[!] APPDATA bulunamadi.")
        return False

    launcher_cfg = os.path.join(appdata, ".craftrise", "config.json")
    cfg_dir = os.path.dirname(launcher_cfg)

    print("[*] Hedef     :", launcher_cfg)

    try:
        os.makedirs(cfg_dir, exist_ok=True)
    except Exception as e:
        print("[!] Klasor olusturulamadi:", e)
        return False

    cfg = {}
    if os.path.exists(launcher_cfg):
        try:
            with open(launcher_cfg, "r", encoding="utf-8") as f:
                ham = f.read()
            cfg = json.loads(ham) if ham.strip() else {}
        except (OSError, json.JSONDecodeError) as e:
            print("[!] Mevcut config okunamadi (uzerine yazilacak):", e)
            cfg = {}

        try:
            shutil.copy2(launcher_cfg, launcher_cfg + ".bak")
            print("[+] Yedek     :", launcher_cfg + ".bak")
        except Exception as e:
            print("[!] Yedekleme hatasi:", e)

    cfg["rememberName"] = username
    cfg["rememberPass"] = enc_yerel
    cfg["rememberMe"]   = True

    try:
        with open(launcher_cfg, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except PermissionError as e:
        print()
        print("[!] YAZILAMADI - Erisim reddedildi.")
        print("    Launcher ACIK olabilir. Once KAPATIN, tekrar deneyin.")
        print("    Detay:", e)
        return False
    except OSError as e:
        print("[!] Yazma hatasi:", e)
        return False

    # Dogrula
    try:
        with open(launcher_cfg, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        print("[!] Yazma dogrulanamadi:", e)
        return False

    if (d.get("rememberName") == username
            and d.get("rememberPass") == enc_yerel
            and d.get("rememberMe") is True):
        print()
        print("[OK] Config yazildi + dogrulandi.")
        print("     rememberName =", username)
        print("     rememberPass =", enc_yerel)
        return True
    else:
        print("[!] Icerik beklenen gibi degil!")
        print("    Dosyadaki:", d)
        return False


# ----------------------------------------------------------------
def main():
    print("=" * 60)
    print("  bak.py — craftrise config yazici (tersi formati)")
    print("=" * 60)

    if len(sys.argv) == 3:
        username, sifre = sys.argv[1], sys.argv[2]
    else:
        username = input("Kullanici adi : ").strip()
        sifre    = input("Sifre         : ").strip()

    if not username or not sifre:
        print("[!] Bos birakildi.")
        input("\nEnter...")
        sys.exit(1)

    print("\n[*] enc uretiliyor...")
    enc_yerel = enc_uret(sifre)
    if not enc_yerel:
        input("\nEnter...")
        sys.exit(1)
    print("[*] enc (%d karakter): %s" % (len(enc_yerel), enc_yerel))

    print("\n[*] Config yaziliyor...")
    ok = kaydet(username, enc_yerel)

    print()
    print("=" * 60)
    if ok:
        print("  BASARILI")
        print("=" * 60)
        print("\nLauncher KAPALIYSA acin — bilgiler dolu gelecek.")
        print("Dogrulamak icin tersi.py'yi calistirabilirsin (RAM kontrolu).")
    else:
        print("  BASARISIZ")
        print("=" * 60)

    input("\nCikmak icin Enter...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[*] Iptal.")
    except Exception:
        print("\n[!!] HATA:")
        traceback.print_exc()
        input("\nEnter...")