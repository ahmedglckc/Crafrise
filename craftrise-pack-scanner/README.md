# CraftRise Pack Scanner

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

CraftRise ve Minecraft texture pack'leri (doku paketleri) içerisindeki zararlı yazılımları (RAT, Truva Atı vb.) ve şüpheli dosya yapılarını tespit etmek için geliştirilmiş statik analiz aracıdır.

## Özellikler

- **Toplu Tarama (CraftRise Modu):** `AppData\Roaming\.craftrise\resourcepacks` dizinini otomatik bulur ve içindeki tüm paketleri tek seferde analiz eder.
- **Tekli Tarama:** Belirtilen `.zip`, `.mcpack` veya klasör yolunu izole olarak tarar.
- **Çift Uzantı Tespiti:** `resim.png.exe` gibi aldatıcı çift uzantılı dosyaları tespit eder ve doğrudan "Virüslü" olarak işaretler.
- **Çalıştırılabilir Dosya Uyarısı:** Doku paketi içinde olmaması gereken `.exe`, `.dll`, `.bat`, `.ps1`, `.vbs`, `.jar`, `.scr` gibi dosyaları raporlar.
- **Yapı Kontrolü:** Geçerli bir Minecraft doku paketinde bulunması gereken `pack.mcmeta` ve `assets/` gibi temel bileşenlerin eksikliğini denetler.
- **Güvenli Analiz:** Dosyaları çalıştırmaz, yalnızca arşiv yapısını okur (Statik Analiz). Zip bomb saldırılarına karşı sıkıştırma oranı kontrolü yapar.

## Kurulum

Sisteminizde Python 3.8 veya üzeri bir sürümün kurulu olması gerekmektedir.

```bash
# Depoyu klonlayın
git clone https://github.com/ahmedglckc/craftrise-pack-scanner.git

# Dizine girin
cd craftrise-pack-scanner

# Aracı çalıştırın
python scan_texturepack.py
