# -*- coding: utf-8 -*-
"""
Oyun DLL Gözlemcisi
- craftrise.64.exe'nin yüklediği TÜM DLL'leri gösterir
- Yeni yüklenenleri KIRMIZI yapar
- DLL'e çift tıklayınca içeriğini gösterir (export/import/sections)
- Sadece OKUR, enjekte etmez
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import os
import sys
import traceback
import datetime
import subprocess

try:
    import psutil
except ImportError:
    print("HATA: pip install psutil")
    sys.exit(1)

try:
    import pefile
except ImportError:
    print("HATA: pip install pefile")
    sys.exit(1)


# ============================================================
#                    AYARLAR
# ============================================================
HEDEF_ISIM = "craftrise.64.exe"       # izlenecek süreç
TARAMA_ARALIK = 1.5                    # saniye
LOG_DOSYA = "dll_gozlemci_log.txt"


def logla(msg):
    try:
        zaman = datetime.datetime.now().strftime("%H:%M:%S")
        s = f"[{zaman}] {msg}"
        print(s)
        try:
            with open(LOG_DOSYA, "a", encoding="utf-8") as f:
                f.write(s + "\n")
        except Exception:
            pass
    except Exception:
        pass


# ============================================================
#                    SÜREÇ BULMA
# ============================================================
def surec_bul():
    """Hedef süreci bulur, PID döner."""
    adaylar = []
    for p in psutil.process_iter(["pid", "name", "exe"]):
        try:
            ad = (p.info["name"] or "").lower()
            if HEDEF_ISIM.lower() in ad or "craftrise" in ad:
                adaylar.append(p)
        except Exception:
            continue

    if not adaylar:
        return None

    # En çok belleği kullananı seç (asıl oyun processi)
    adaylar.sort(key=lambda p: p.memory_info().rss, reverse=True)
    return adaylar[0]


# ============================================================
#                    DLL LİSTELEME
# ============================================================
def surec_dll_listesi(pid):
    """Verilen PID'nin yüklediği DLL listesini döner."""
    sonuc = []
    try:
        p = psutil.Process(pid)
        for m in p.memory_maps():
            try:
                yol = m.path
                if yol and yol.lower().endswith(".dll"):
                    sonuc.append(yol)
            except Exception:
                continue
    except Exception as e:
        logla(f"dll listesi hata: {e}")
    return sorted(set(sonuc), key=lambda x: x.lower())


# ============================================================
#                    PE ANALİZİ
# ============================================================
def pe_analiz(dosya_yolu):
    """DLL içeriğini analiz eder."""
    bilgi = {
        "yol": dosya_yolu,
        "var": os.path.exists(dosya_yolu),
        "boyut": 0,
        "mimari": "?",
        "timestamp": "?",
        "exports": [],
        "imports": {},       # {dll_adi: [fonk, fonk]}
        "sections": [],      # [(ad, vsize, rawsize, entropy)]
        "entrypoint": "?",
        "imagebase": "?",
        "hata": None,
    }

    try:
        if not os.path.exists(dosya_yolu):
            bilgi["hata"] = "Dosya bulunamadı (bellekten yüklü olabilir)"
            return bilgi

        bilgi["boyut"] = os.path.getsize(dosya_yolu)

        pe = pefile.PE(dosya_yolu, fast_load=True)
        pe.parse_data_directories()

        # Mimari
        try:
            if pe.FILE_HEADER.Machine == 0x8664:
                bilgi["mimari"] = "x64"
            elif pe.FILE_HEADER.Machine == 0x14c:
                bilgi["mimari"] = "x86 (32-bit)"
            elif pe.FILE_HEADER.Machine == 0xaa64:
                bilgi["mimari"] = "ARM64"
            else:
                bilgi["mimari"] = hex(pe.FILE_HEADER.Machine)
        except Exception:
            pass

        # Timestamp
        try:
            ts = pe.FILE_HEADER.TimeDateStamp
            bilgi["timestamp"] = datetime.datetime.fromtimestamp(ts).strftime(
                "%Y-%m-%d %H:%M"
            )
        except Exception:
            pass

        # ImageBase / EntryPoint
        try:
            bilgi["imagebase"] = hex(pe.OPTIONAL_HEADER.ImageBase)
        except Exception:
            pass
        try:
            bilgi["entrypoint"] = hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint)
        except Exception:
            pass

        # Exports
        try:
            if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
                for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                    try:
                        ad = exp.name.decode("utf-8", "ignore") if exp.name else f"ordinal_{exp.ordinal}"
                        bilgi["exports"].append(ad)
                    except Exception:
                        continue
        except Exception:
            pass

        # Imports
        try:
            if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
                for entry in pe.DIRECTORY_ENTRY_IMPORT:
                    try:
                        dll_adi = entry.dll.decode("utf-8", "ignore")
                        fonklar = []
                        for imp in entry.imports:
                            try:
                                ad = imp.name.decode("utf-8", "ignore") if imp.name else f"ord_{imp.ordinal}"
                                fonklar.append(ad)
                            except Exception:
                                continue
                        bilgi["imports"][dll_adi] = fonklar
                    except Exception:
                        continue
        except Exception:
            pass

        # Sections
        try:
            for s in pe.sections:
                try:
                    ad = s.Name.decode("utf-8", "ignore").rstrip("\x00")
                    bilgi["sections"].append((
                        ad,
                        s.Misc_VirtualSize,
                        s.SizeOfRawData,
                        round(s.get_entropy(), 2)
                    ))
                except Exception:
                    continue
        except Exception:
            pass

        pe.close()

    except Exception as e:
        bilgi["hata"] = str(e)

    return bilgi


# ============================================================
#                    ANA PENCERE
# ============================================================
class DllGozlemci:
    def __init__(self):
        self.pid = None
        self.son_dll_listesi = set()
        self.yeni_dll = set()
        self.calisiyor = True

        self._pencere_kur()
        self._pid_bul()
        self.root.after(500, self._dongu_baslat)
        self.root.protocol("WM_DELETE_WINDOW", self._kapat)
        self.root.mainloop()

    # ---------------- PENCERE ----------------
    def _pencere_kur(self):
        self.root = tk.Tk()
        self.root.title("Oyun DLL Gözlemcisi")
        self.root.geometry("1150x680")
        self.root.configure(bg="#1a1a1a")
        self.root.minsize(800, 500)

        # ÜST
        ust = tk.Frame(self.root, bg="#0d0d0d", height=52)
        ust.pack(fill="x")
        ust.pack_propagate(False)

        tk.Label(
            ust, text="🔍  DLL GÖZLEMCİ",
            font=("Segoe UI", 14, "bold"),
            fg="#00FF88", bg="#0d0d0d"
        ).pack(side="left", padx=15, pady=10)

        self.pid_lbl = tk.Label(
            ust, text="PID: ?",
            font=("Consolas", 10, "bold"),
            fg="#FFAA00", bg="#0d0d0d"
        )
        self.pid_lbl.pack(side="left", padx=10)

        self.durum = tk.Label(
            ust, text="● ARIYOR...",
            font=("Consolas", 10, "bold"),
            fg="#FFAA00", bg="#0d0d0d"
        )
        self.durum.pack(side="right", padx=15)

        # BUTONLAR
        btn_frame = tk.Frame(self.root, bg="#1a1a1a")
        btn_frame.pack(fill="x", padx=10, pady=6)

        tk.Button(
            btn_frame, text="🔄 Yeniden Bul",
            font=("Segoe UI", 9, "bold"),
            bg="#0088FF", fg="white", bd=0, padx=12, pady=4,
            cursor="hand2", command=self._pid_bul
        ).pack(side="left", padx=3)

        tk.Button(
            btn_frame, text="🧹 Yeni İşaretlerini Temizle",
            font=("Segoe UI", 9, "bold"),
            bg="#00AA55", fg="white", bd=0, padx=12, pady=4,
            cursor="hand2", command=self._yeni_temizle
        ).pack(side="left", padx=3)

        tk.Button(
            btn_frame, text="💾 Listeyi Kaydet",
            font=("Segoe UI", 9, "bold"),
            bg="#AA5500", fg="white", bd=0, padx=12, pady=4,
            cursor="hand2", command=self._liste_kaydet
        ).pack(side="left", padx=3)

        self.sayac_lbl = tk.Label(
            btn_frame, text="📄 Toplam: 0  |  🆕 Yeni: 0",
            font=("Consolas", 10, "bold"),
            fg="#CCCCCC", bg="#1a1a1a"
        )
        self.sayac_lbl.pack(side="right", padx=10)

        # ===== SPLIT (sol: DLL listesi, sağ: detay) =====
        ana = tk.PanedWindow(self.root, orient="horizontal",
                             bg="#1a1a1a", sashwidth=6,
                             sashrelief="raised", bd=0)
        ana.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        # --- SOL: LİSTE ---
        sol = tk.Frame(ana, bg="#0d0d0d")
        ana.add(sol, width=520)

        stil = ttk.Style()
        try:
            stil.theme_use("clam")
        except Exception:
            pass
        stil.configure("Treeview",
                       background="#0d0d0d",
                       foreground="#CCCCCC",
                       fieldbackground="#0d0d0d",
                       rowheight=22,
                       font=("Consolas", 9))
        stil.configure("Treeview.Heading",
                       background="#222222",
                       foreground="#00FF88",
                       font=("Segoe UI", 9, "bold"))
        stil.map("Treeview", background=[("selected", "#0088FF")])

        self.tree = ttk.Treeview(sol, columns=("dll",), show="headings")
        self.tree.heading("dll", text="📄 Yüklü DLL")
        self.tree.column("dll", width=500, anchor="w")

        self.tree.tag_configure("yeni", foreground="#FF3333",
                                font=("Consolas", 9, "bold"))
        self.tree.tag_configure("sistem", foreground="#777777")
        self.tree.tag_configure("normal", foreground="#CCCCCC")

        sb = ttk.Scrollbar(sol, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._dll_secildi)

        # --- SAĞ: DETAY ---
        sag = tk.Frame(ana, bg="#0d0d0d")
        ana.add(sag, width=600)

        detay_ust = tk.Frame(sag, bg="#0d0d0d")
        detay_ust.pack(fill="x")
        self.detay_baslik = tk.Label(
            detay_ust, text="Bir DLL seç...",
            font=("Segoe UI", 11, "bold"),
            fg="#00FF88", bg="#0d0d0d", anchor="w"
        )
        self.detay_baslik.pack(side="left", padx=8, pady=6)
        self.detay_yol = tk.Label(
            detay_ust, text="",
            font=("Consolas", 8),
            fg="#666666", bg="#0d0d0d", anchor="w"
        )
        self.detay_yol.pack(side="left", padx=8, pady=6)

        # Sekmeler
        notebook = ttk.Notebook(sag)
        notebook.pack(fill="both", expand=True, padx=4, pady=4)

        # Sekme 1: Özet
        self.txt_ozet = self._metin_sekmesi(notebook, "📋 Özet")
        # Sekme 2: Exports
        self.txt_exports = self._metin_sekmesi(notebook, "📤 Exports")
        # Sekme 3: Imports
        self.txt_imports = self._metin_sekmesi(notebook, "📥 Imports")
        # Sekme 4: Sections
        self.txt_sections = self._metin_sekmesi(notebook, "🧱 Sections")
        # Sekme 5: Ham
        self.txt_ham = self._metin_sekmesi(notebook, "🔤 Ham Çıktı")

        # ALT
        alt = tk.Frame(self.root, bg="#0d0d0d", height=26)
        alt.pack(fill="x", side="bottom")
        alt.pack_propagate(False)
        self.alt_lbl = tk.Label(
            alt, text="Hazır",
            font=("Consolas", 9),
            fg="#888888", bg="#0d0d0d", anchor="w"
        )
        self.alt_lbl.pack(side="left", padx=12, pady=4)

    def _metin_sekmesi(self, notebook, baslik):
        cerceve = tk.Frame(notebook, bg="#0d0d0d")
        notebook.add(cerceve, text=baslik)

        txt = tk.Text(
            cerceve, bg="#0d0d0d", fg="#CCCCCC",
            insertbackground="white",
            font=("Consolas", 9),
            wrap="none", bd=0, padx=8, pady=8
        )
        sb_y = ttk.Scrollbar(cerceve, orient="vertical", command=txt.yview)
        sb_x = ttk.Scrollbar(cerceve, orient="horizontal", command=txt.xview)
        txt.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        txt.grid(row=0, column=0, sticky="nsew")
        sb_y.grid(row=0, column=1, sticky="ns")
        sb_x.grid(row=1, column=0, sticky="ew")
        cerceve.rowconfigure(0, weight=1)
        cerceve.columnconfigure(0, weight=1)

        return txt

    # ---------------- PID BUL ----------------
    def _pid_bul(self):
        try:
            p = surec_bul()
            if not p:
                self.pid = None
                self.pid_lbl.config(text="PID: ?", fg="#FF5555")
                self.durum.config(text="● OYUN BULUNAMADI", fg="#FF5555")
                self.alt_lbl.config(
                    text=f"⚠ {HEDEF_ISIM} çalışmıyor — oyunu aç ve 'Yeniden Bul' bas"
                )
                return

            self.pid = p.pid
            exe = ""
            try:
                exe = p.exe()
            except Exception:
                pass
            self.pid_lbl.config(text=f"PID: {self.pid}", fg="#00FF88")
            self.durum.config(text="● İZLENİYOR", fg="#00FF88")
            self.alt_lbl.config(text=f"İzleniyor: {exe or HEDEF_ISIM}")
            logla(f"Oyun bulundu: PID={self.pid}")
        except Exception as e:
            logla(f"pid bul hata: {e}")

    # ---------------- DÖNGÜ ----------------
    def _dongu_baslat(self):
        threading.Thread(target=self._dongu, daemon=True).start()

    def _dongu(self):
        while self.calisiyor:
            try:
                if self.pid is None:
                    time.sleep(2)
                    self.root.after(0, self._pid_bul)
                    continue

                # Süreç hâlâ var mı?
                try:
                    if not psutil.pid_exists(self.pid):
                        logla("süreç kapandı")
                        self.pid = None
                        continue
                except Exception:
                    pass

                dll_listesi = surec_dll_listesi(self.pid)

                # Yeni eklenenler
                yeni_eklenen = []
                for d in dll_listesi:
                    if d not in self.son_dll_listesi and self.son_dll_listesi:
                        self.yeni_dll.add(d)
                        yeni_eklenen.append(os.path.basename(d))

                self.son_dll_listesi = set(dll_listesi)

                if yeni_eklenen:
                    for y in yeni_eklenen:
                        logla(f"🆕 YENİ YÜKLENDİ: {y}")

                self.root.after(0, lambda l=dll_listesi: self._listeyi_yenile(l))

            except Exception as e:
                logla(f"döngü hata: {e}")

            time.sleep(TARAMA_ARALIK)

    # ---------------- LİSTE YENİLE ----------------
    def _listeyi_yenile(self, dll_listesi):
        try:
            # Seçili olanı koru
            secili = self.tree.selection()
            secili_yol = None
            if secili:
                try:
                    secili_yol = self.tree.item(secili[0], "values")[0]
                except Exception:
                    pass

            for i in self.tree.get_children():
                self.tree.delete(i)

            # Yeni olanlar en üstte
            sirali = sorted(
                dll_listesi,
                key=lambda x: (x not in self.yeni_dll, x.lower())
            )

            tekrar_sec = None
            for yol in sirali:
                ad = os.path.basename(yol)
                if yol in self.yeni_dll:
                    etiket = "yeni"
                    goster = f"🆕 {ad}"
                elif "windows" in yol.lower() or "system32" in yol.lower():
                    etiket = "sistem"
                    goster = ad
                else:
                    etiket = "normal"
                    goster = ad

                iid = self.tree.insert(
                    "", "end",
                    values=(yol,),
                    tags=(etiket,)
                )
                # Görünen metin
                self.tree.item(iid, text=goster)
                self.tree.item(iid, values=(yol,))

                if secili_yol and yol == secili_yol:
                    tekrar_sec = iid

            if tekrar_sec:
                self.tree.selection_set(tekrar_sec)

            self.sayac_lbl.config(
                text=f"📄 Toplam: {len(dll_listesi)}  |  🆕 Yeni: {len(self.yeni_dll)}"
            )
        except Exception as e:
            logla(f"liste yenile hata: {e}")

    # ---------------- SEÇİM ----------------
    def _dll_secildi(self, event):
        try:
            secili = self.tree.selection()
            if not secili:
                return
            yol = self.tree.item(secili[0], "values")[0]

            self.detay_baslik.config(text=os.path.basename(yol))
            self.detay_yol.config(text=yol)

            # Analizi arka planda yap
            threading.Thread(
                target=self._analiz_yap, args=(yol,), daemon=True
            ).start()
        except Exception as e:
            logla(f"seçim hata: {e}")

    def _analiz_yap(self, yol):
        try:
            b = pe_analiz(yol)
            self.root.after(0, lambda: self._detay_goster(b))
        except Exception as e:
            logla(f"analiz hata: {e}")

    def _detay_goster(self, b):
        try:
            # --- ÖZET ---
            t = self.txt_ozet
            t.delete("1.0", "end")

            def yaz(s):
                t.insert("end", s + "\n")

            yaz(f"📄 Dosya:      {os.path.basename(b['yol'])}")
            yaz(f"📁 Yol:        {b['yol']}")
            yaz(f"📏 Boyut:      {self._boyut(b['boyut'])}")
            yaz(f"🏗️  Mimari:     {b['mimari']}")
            yaz(f"🕐 Tarih:      {b['timestamp']}")
            yaz(f"📍 ImageBase:  {b['imagebase']}")
            yaz(f"🚪 EntryPoint: {b['entrypoint']}")
            yaz(f"📤 Export:     {len(b['exports'])}")
            yaz(f"📥 Import DLL: {len(b['imports'])}")
            yaz(f"🧱 Section:    {len(b['sections'])}")
            if b["hata"]:
                yaz("")
                yaz(f"⚠️  HATA: {b['hata']}")

            # --- EXPORTS ---
            t = self.txt_exports
            t.delete("1.0", "end")
            if not b["exports"]:
                t.insert("end", "(Bu DLL'de dışa aktarılan fonksiyon yok)\n")
            else:
                t.insert("end", f"TOPLAM {len(b['exports'])} EXPORT\n")
                t.insert("end", "=" * 60 + "\n\n")
                for ad in sorted(b["exports"]):
                    t.insert("end", f"  • {ad}\n")

            # --- IMPORTS ---
            t = self.txt_imports
            t.delete("1.0", "end")
            if not b["imports"]:
                t.insert("end", "(Import yok)\n")
            else:
                toplam = sum(len(v) for v in b["imports"].values())
                t.insert("end", f"TOPLAM {len(b['imports'])} DLL, {toplam} FONKSİYON\n")
                t.insert("end", "=" * 60 + "\n\n")
                for dll_adi in sorted(b["imports"].keys()):
                    fonklar = b["imports"][dll_adi]
                    t.insert("end", f"\n📥 {dll_adi}  ({len(fonklar)} fonksiyon)\n")
                    t.insert("end", "-" * 60 + "\n")
                    for f in sorted(fonklar):
                        t.insert("end", f"  • {f}\n")

            # --- SECTIONS ---
            t = self.txt_sections
            t.delete("1.0", "end")
            if not b["sections"]:
                t.insert("end", "(Section yok)\n")
            else:
                t.insert("end",
                         f"{'Ad':<12}{'Sanal Boyut':>15}{'Ham Boyut':>15}{'Entropy':>12}\n")
                t.insert("end", "=" * 60 + "\n")
                for ad, vs, rs, ent in b["sections"]:
                    t.insert("end",
                             f"{ad:<12}{vs:>15,}{rs:>15,}{ent:>12}\n")

            # --- HAM ---
            t = self.txt_ham
            t.delete("1.0", "end")
            t.insert("end", f"YOL: {b['yol']}\n\n")
            t.insert("end", "İLK 64 BYTE (hex):\n")
            try:
                if os.path.exists(b["yol"]):
                    with open(b["yol"], "rb") as f:
                        veri = f.read(64)
                    hexs = " ".join(f"{x:02X}" for x in veri)
                    t.insert("end", hexs + "\n")
                    # MZ / PE kontrolü
                    if veri[:2] == b"MZ":
                        t.insert("end", "\n✅ MZ imzası var — geçerli PE dosyası\n")
                    else:
                        t.insert("end", "\n❌ MZ imzası yok — bozuk/şifreli olabilir\n")
                else:
                    t.insert("end", "(dosya diske yok)\n")
            except Exception as e:
                t.insert("end", f"HATA: {e}\n")

        except Exception as e:
            logla(f"detay goster hata: {e}")
            traceback.print_exc()

    @staticmethod
    def _boyut(b):
        try:
            for birim in ["B", "KB", "MB", "GB"]:
                if b < 1024:
                    return f"{b:.1f} {birim}"
                b /= 1024
            return f"{b:.1f} TB"
        except Exception:
            return "?"

    # ---------------- YENİ TEMİZLE ----------------
    def _yeni_temizle(self):
        self.yeni_dll.clear()
        if self.son_dll_listesi:
            self._listeyi_yenile(list(self.son_dll_listesi))
        logla("yeni işaretleri temizlendi")

    # ---------------- LİSTE KAYDET ----------------
    def _liste_kaydet(self):
        try:
            yol = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Metin", "*.txt")],
                initialfile=f"dll_listesi_{datetime.datetime.now():%Y%m%d_%H%M}.txt"
            )
            if not yol:
                return
            with open(yol, "w", encoding="utf-8") as f:
                f.write(f"Oyun: {HEDEF_ISIM}\n")
                f.write(f"PID: {self.pid}\n")
                f.write(f"Tarih: {datetime.datetime.now()}\n")
                f.write(f"Toplam: {len(self.son_dll_listesi)} DLL\n")
                f.write("=" * 70 + "\n\n")
                for d in sorted(self.son_dll_listesi, key=lambda x: x.lower()):
                    f.write(d + "\n")
            messagebox.showinfo("Kaydedildi", f"Kaydedildi:\n{yol}")
            logla(f"liste kaydedildi: {yol}")
        except Exception as e:
            logla(f"kaydet hata: {e}")
            messagebox.showerror("Hata", str(e))

    # ---------------- KAPAT ----------------
    def _kapat(self):
        self.calisiyor = False
        try:
            self.root.destroy()
        except Exception:
            pass
        try:
            os._exit(0)
        except Exception:
            sys.exit(0)


# ============================================================
if __name__ == "__main__":
    try:
        DllGozlemci()
    except Exception as e:
        logla(f"BAŞLATMA: {e}")
        traceback.print_exc()
        try:
            input("Enter...")
        except Exception:
            pass