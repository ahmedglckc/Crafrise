# 🔓 CraftRise Şifre Çözücü

> **CraftRise Launcher** tarafından `%APPDATA%\.craftrise` dizinine kaydedilen şifreli parolayı, launcher sunucusuyla aynı protokolü kullanarak çözen küçük bir Python aracı.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📌 Nedir?

CraftRise Launcher, "Beni hatırla" seçeneği işaretlendiğinde kullanıcının parolasını `config.json` içine **şifrelenmiş** olarak (`rememberPass`) kaydeder. Bu araç:

- 📂 `config.json` ve `launcher_java.json` dosyalarını okur
- 🔐 Şifreli parolayı ve oturum anahtarlarını **launcher gibi** sunucuya POST eder
- ✅ Sunucunun döndürdüğü HTML yanıtından **açık metin parolayı** ayıklar

> ⚠️ **Bu araç yalnızca kendi hesabınızın kayıp/unutulan parolasını kurtarmak için tasarlanmıştır.** Başkasına ait cihazlarda kullanmak **yasal ve etik değildir** anladınızmı! [sorumluluk almıyorum].

---

## ⚙️ Özellikler

| Özellik | Açıklama |
|---|---|
| 🔍 Otomatik config bulma | `%APPDATA%\.craftrise\` yolunu otomatik algılar |
| 📦 Eksiksiz payload | `config.json` + `launcher_java.json` birleştirilerek gönderilir |
| 🌐 Launcher taklidi | `User-Agent` ve `Content-Type` başlıkları launcher ile aynı |
| 🛡️ Hata yakalama | Tüm istisnalar yakalanır, pencere asla kapanmaz |
| ⏱️ Zaman aşımı | 15 saniye varsayılan (kolayca değiştirilebilir) |

---

## 📋 Gereksinimler

- **Python 3.8+**
- **Windows** (yol `%APPDATA%` üzerinden okunduğu için)
- CraftRise Launcher'da daha önce **giriş yapılmış** olması (yani `rememberPass` alanının dolu olması)

> Harici kütüphane gerekmez — yalnızca standart kütüphane (`json`, `os`, `re`, `urllib`).

---

## 🚀 Kullanım

```bash
python cözücü.py
