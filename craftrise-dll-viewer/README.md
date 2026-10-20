# 🔍 CraftRise DLL Görüntüleyici

> **CraftRise** oyununun yüklediği **tüm DLL'leri** gösteren, yeni yüklenenleri **kırmızı** ile işaretleyen ve herhangi bir DLL'e tıklayınca **içini gösteren** (export/import/section) basit bir masaüstü uygulaması.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![GUI](https://img.shields.io/badge/GUI-Tkinter-orange)

---

## 📌 Bu ne işe yarar?

Oyunlar çalışırken bir sürü DLL dosyası yükler. Bazıları Windows'un kendi dosyaları, bazıları oyunun kendi dosyaları, bazıları da **mod** olabilir.

Bu araç:
- 🔎 Çalışan **CraftRise** oyununu bulur
- 📄 Yüklediği **tüm DLL'leri** listeler
- 🆕 Yeni yüklenenleri **anında kırmızı** yapar
- 🖱️ Bir DLL'e tıklayınca içini gösterir:
  - Temel bilgiler (boyut, mimari, tarih)
  - Dışa aktarılan fonksiyonlar (Exports)
  - İçe aktarılan fonksiyonlar (Imports)
  - Section'lar (entropy ile — yüksek entropy = paketli/şifreli olabilir)
  - İlk 64 byte (ham hex)
- 💾 Tüm listeyi `.txt` dosyasına kaydeder

> ⚠️ **Bu araç sadece OKUR.** Oyunu değiştirmez, enjekte etmez, hiçbir şeye dokunmaz. Güvenle çalıştırabilirsin.

---

## ⚙️ Özellikler

| Özellik | Ne yapar |
|---|---|
| 🔄 Canlı izleme | Her **1.5 saniyede** bir yeni DLL var mı diye bakar |
| 🆕 Yeni vurgusu | Yeni DLL'ler **kırmızı** ve 🆕 işaretli gelir |
| 🖱️ Tıkla incele | Tam PE detaylarını sekmelerde gösterir |
| 📑 5 sekme | Özet · Exports · Imports · Sections · Ham |
| 🧹 İşaret temizle | Gördükten sonra "yeni" işaretlerini siler |
| 💾 Liste kaydet | Tüm DLL'leri `.txt` olarak dışa aktarır |
| 🧠 Otomatik bulma | İsim değişse bile çalışır (`craftrise` arar) |
| 📝 Log dosyası | Her şey `dll_gozlemci_log.txt` dosyasına yazılır |

---

## 📋 Gereksinimler

- **Python 3.8+**
- **Windows**
- **CraftRise** açık olmalı
- **Yönetici olarak çalıştır** 🔑 (süreci okumak için gerekli)

### 📦 Kurulum

```bash
pip install psutil pefile
