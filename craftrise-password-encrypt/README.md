# 🔐 CraftRise Şifre Şifreleyici

> **CraftRise Launcher**'ın `%APPDATA%\.craftrise\config.json` dosyasına kullanıcı adı ve şifreyi launcher'ın beklediği formatta **şifreleyerek** yazan küçük bir Python aracı.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📌 Nedir?

CraftRise Launcher, "Beni hatırla" seçeneği işaretlendiğinde kullanıcının parolasını `config.json` içine **şifrelenmiş** olarak (`rememberPass`) kaydeder ve her açılışta bu değeri okuyup otomatik giriş yapar. Bu araç:

- 🔐 Kullanıcının girdiği açık parolayı launcher'ın beklediği formatta **şifreler**
- 📝 `%APPDATA%\.craftrise\config.json` dosyasını günceller (`rememberName`, `rememberPass`, `rememberMe`)
- 💾 Yazmadan önce mevcut config'in **otomatik yedeğini** alır (`.bak`)
- ✅ Yazdıktan sonra dosyayı geri okuyup **doğrular**

> ⚠️ **Bu araç yalnızca kendi hesabınızı otomatik girişe hazırlamak için tasarlanmıştır.** Başkasına ait cihazlarda kullanmak **yasal ve etik değildir**. Sorumluluk kullanıcıya aittir.

---

## ⚙️ Özellikler

| Özellik | Açıklama |
|---|---|
| 🔐 Launcher uyumlu şifreleme | CraftRise'ın kabul ettiği formatta `enc` üretir |
| 📂 Otomatik yol | `%APPDATA%\.craftrise\config.json` otomatik bulunur |
| 💾 Otomatik yedek | Yazma öncesi `config.json.bak` oluşturulur |
| ✅ Yazma doğrulama | Dosya geri okunur, alanlar karşılaştırılır |
| 🛡️ Hata yakalama | `PermissionError`, `OSError` ve tüm istisnalar yakalanır, pencere asla kapanmaz |
| 🎯 Mevcut alanlar korunur | Config'deki diğer alanlar silinmez, sadece gerekli 3 alan güncellenir |
| 🧪 CLI + etkileşimli | Komut satırından argümanla veya sorularla çalışır |

---

## 📋 Gereksinimler

- **Python 3.8+**
- **Windows** (yol `%APPDATA%` üzerinden okunduğu için)
- **pycryptodome** (AES şifreleme için)

```bash
pip install pycryptodome
