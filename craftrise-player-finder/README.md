# 🎮 CraftRise CANLI Oyuncu Tarayıcı

> **CraftRise** oyununun belleğini (RAM) gerçek zamanlı olarak tarayarak, oyun içindeki **oyuncu isimlerini** yakalayan ve konsola döken Python aracı.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📌 Nedir?

CraftRise, oyuncu verilerini bellek içinde belirli JSON-benzeri kalıplarla tutar. Bu araç:

- 🧠 `craftrise-x64.exe` sürecinin belleğini okur
- 🔍 `MC|Data{"3x7":[...]` biçimindeki kalıpları arar
- 🏷️ `3x8` ve `4x5` anahtarları altındaki **oyuncu isimlerini** çıkarır
- ♻️ Her ismi **yalnızca 1 kez** gösterir (tekrar yok)
- ⚡ Arka planda sürekli tarar — yeni oyuncu geldiği an ekrana basar

> ⚠️ Bu araç **hiçbir veriyi sunucuya göndermez**, yalnızca yerel bellek okur.

---

## ⚙️ Özellikler

| Özellik | Açıklama |
|---|---|
| 🔄 Sürekli tarama | 0.5 saniyede bir tüm belleği tarar |
| 🎯 Kalıp eşleştirme | İki farklı `MC|Data` şemasını destekler |
| 🚫 Tekrar filtresi | Aynı ismi bir kez yazar (`seen` seti) |
| 📍 Bellek adresi | Her ismin bulunduğu **mutlak adresi** gösterir |
| ⏱️ Zaman damgası | Her bulgu `[HH:MM:SS]` formatında |
| 🛡️ Yönetici kontrolü | `OpenProcess` başarısız olursa uyarı verir |
| 🧹 Temiz çıkış | `Ctrl+C` ile düzgün kapatma |

---

## 📋 Gereksinimler

- **Python 3.8+**
- **Windows** (Win32 API kullanır)
- **CraftRise** açık ve çalışıyor olmalı
- **Yönetici yetkisi** (bellek okumak için) 🔑

### 📦 Kurulum

```bash
pip install pymem
