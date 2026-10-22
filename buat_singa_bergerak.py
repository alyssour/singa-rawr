"""
TUGAS MULTIMEDIA - GAMBAR MENJADI BERGERAK DAN BERSUARA
========================================================
Hewan  : Singa (Panthera leo) - "RAWR si Singa"
Tema   : Singa berjalan di hutan saat PETANG (matahari terbenam),
         lalu berhenti dan MENGAUM: "AUUUMMM... RAWR!"
Input  : singa_jalan.png       -> gambar singa pose berjalan
         singa.png             -> gambar singa pose mengaum
         auman.mp3             -> suara auman singa asli (untuk web)
         auman_singa.mp3       -> audio video (hutan petang + auman)
Output : singa_bergerak.mp4    -> video gambar bergerak + bersuara
         badan.png, kaki1-4.png, singa_rawr.png, rig.js, poster.jpg
                               -> aset untuk halaman web (GitHub Pages)

Catatan sumber gambar:
  Gambar singa TIDAK diunduh dari internet. Program ini MENGGAMBAR
  sendiri kedua pose singa di atas latar putih memakai Pillow
  (d digambar 3x lebih besar lalu diperkecil supaya halus), lalu
  latar putihnya dihapus dengan metode yang sama seperti proyek
  referensi: flood-fill dari tepi gambar. Jadi alurnya tetap:
  gambar latar putih -> transparan -> dipotong jadi badan + 4 kaki.

Alur cerita video (14 detik):
  1. Detik 0,0-5,2 : singa BERJALAN masuk dari kiri layar melintasi
     hutan petang. Kakinya bergerak sungguhan dengan teknik walk
     cycle: gambar dipotong menjadi badan dan 4 kaki, lalu setiap
     kaki diputar bergantian pada poros pangkalnya (animasi 2D).
     Badan ikut naik-turun halus, pohon ikut bergeser (parallax),
     matahari terbenam membesar kecil mengikuti langkah.
  2. Detik 5,2-5,55: singa berhenti, berganti pose menjadi pose
     mengaum (crossfade cepat), lalu bersiap.
  3. Detik 5,9-13,0: singa MENGAUM. Gelombang suara keluar dari
     mulutnya tepat bersamaan dengan suara auman pada audio,
     badan dan cahaya matahari berdenyut, layar sedikit bergetar.
  4. Detik 13,0-14 : fade-out, video selesai.

Teknik menghapus background putih:
  Flood-fill dari tepi gambar: piksel yang nyaris putih DAN terhubung
  ke tepi gambar dianggap background. Bagian putih di dalam tubuh
  (mis. gigi di mulut yang terbuka) tidak ikut terhapus karena
  terhalang outline gambar.

Audio:
  auman.mp3 dibuat dari rekaman auman singa asli "Lion roaring"
  (Wikimedia Commons, singa di Tamil Nadu) yang dipotong dan
  dinaikkan volumenya memakai FFmpeg.
  auman_singa.mp3 (audio video) dibuat program ini bila belum ada:
  suara semilir hutan (brown noise pelan) selama fase berjalan,
  lalu auman mulai tepat detik 5,9.

Kebutuhan:
  pip install pillow numpy scipy
  Program FFmpeg harus sudah terinstall (perintah: ffmpeg)

Jalankan:
  python buat_singa_bergerak.py
"""

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------
FOLDER = Path(__file__).parent
FILE_JALAN = FOLDER / "singa_jalan.png"     # sumber pose berjalan (latar putih)
FILE_AUNG = FOLDER / "singa.png"            # sumber pose mengaum (latar putih)
FILE_SUARA_WEB = FOLDER / "auman.mp3"       # auman saja (halaman web)
FILE_SUARA = FOLDER / "auman_singa.mp3"     # audio video (ambien + auman)
FILE_VIDEO = FOLDER / "singa_bergerak.mp4"

LEBAR, TINGGI = 1280, 720     # resolusi video (HD 720p)
FPS = 30                      # frame per detik
DURASI = 14                   # durasi video (detik)
TOTAL_FRAME = FPS * DURASI

# Pembagian fase animasi (detik)
AKHIR_JALAN = 5.2             # singa berjalan sampai detik ini
AKHIR_GANTI_POSE = 5.55       # crossfade pose jalan -> pose mengaum
MULAI_AUNG = 5.9              # suara auman mulai (sinkron dgn audio)
AKHIR_AUNG = 13.0             # auman selesai, mulai fade-out

# Posisi mulut pada gambar pose mengaum (persen lebar/tinggi gambar)
MULUT_X, MULUT_Y = 0.90, 0.44

# Posisi akhir singa setelah berjalan (kiri atas area tampil)
TARGET_X = 150
TANAH_Y = TINGGI - 26         # garis telapak kaki singa
LEBAR_TAMPIL = 800            # lebar tampil singa di video (piksel)

# Warna singa
EMAS = (227, 154, 46)
EMAS_GELAP = (201, 127, 34)   # kaki jauh (lebih gelap = efek kedalaman)
EMAS_MUDA = (244, 188, 88)
PERUT = (249, 213, 141)
SURAI = (154, 85, 24)
SURAI_GELAP = (122, 64, 18)
MUZZLE = (251, 227, 176)
HIDUNG = (74, 42, 30)
MULUT_DALAM = (122, 31, 31)
LIDAH = (214, 102, 102)
PUTIH = (255, 255, 255)


# ---------------------------------------------------------------------------
# Langkah 0 - Menggambar sumber singa (latar putih) memakai Pillow
# ---------------------------------------------------------------------------
SS = 3  # supersample: gambar 3x lebih besar lalu diperkecil (anti-alias)


def _skala(img_besar, ukuran):
    return img_besar.resize(ukuran, Image.LANCZOS)


def gambar_sumber_jalan():
    """Singa tampak samping menghadap kanan, pose berjalan, latar putih."""
    W, H = 1000, 560
    img = Image.new("RGB", (W * SS, H * SS), PUTIH)
    d = ImageDraw.Draw(img)

    def k(v):
        return v * SS

    def kotak(x0, y0, x1, y1, **kw):
        d.rounded_rectangle([k(x0), k(y0), k(x1), k(y1)],
                            radius=k(26), **kw)

    def elips(cx, cy, rx, ry, **kw):
        d.ellipse([k(cx - rx), k(cy - ry), k(cx + rx), k(cy + ry)], **kw)

    # --- Ekor: garis melengkung ke atas + jambul gelap di ujung ---
    ekor = [(168, 238), (128, 205), (102, 168), (94, 132)]
    d.line([(k(x), k(y)) for x, y in ekor], fill=EMAS, width=k(21))
    for (jx, jy) in ekor:  # lingkaran di sambungan agar tidak patah
        elips(jx, jy, 10, 10, fill=EMAS)
    elips(92, 118, 24, 32, fill=SURAI_GELAP)

    # --- Kaki (digambar sebelum badan; pangkalnya tertutup badan) ---
    # Urutan kiri->kanan: belakang-jauh, belakang-dekat, depan-jauh, depan-dekat
    kaki_def = [(215, EMAS_GELAP), (305, EMAS), (575, EMAS_GELAP), (665, EMAS)]
    for cx, warna in kaki_def:
        kotak(cx - 29, 315, cx + 29, 520, fill=warna)
        elips(cx + 4, 522, 36, 14, fill=warna)  # telapak kaki

    # --- Badan ---
    d.rounded_rectangle([k(155), k(195), k(730), k(372)], radius=k(88),
                        fill=EMAS)
    elips(440, 334, 180, 32, fill=PERUT)  # perut muda

    # --- Surai (rambut lebat di sekeliling kepala) ---
    cx_s, cy_s, r_s = 772, 232, 132
    for sudut in range(0, 360, 30):  # gumpalan luar surai
        a = math.radians(sudut)
        elips(cx_s + r_s * 0.82 * math.cos(a), cy_s + r_s * 0.82 * math.sin(a),
              40, 40, fill=SURAI)
    elips(cx_s, cy_s, r_s, r_s, fill=SURAI)
    elips(cx_s, cy_s, r_s - 22, r_s - 22, fill=SURAI_GELAP)

    # --- Telinga ---
    elips(720, 140, 27, 27, fill=SURAI)
    elips(720, 140, 14, 14, fill=EMAS_MUDA)

    # --- Wajah ---
    elips(788, 242, 88, 88, fill=EMAS_MUDA)
    # Mata (tenang, menatap ke depan)
    elips(818, 222, 10, 14, fill=(40, 26, 18))
    elips(822, 217, 3.5, 4.5, fill=PUTIH)
    # Alis halus
    d.arc([k(798), k(196), k(840), k(224)], start=200, end=330,
          fill=SURAI_GELAP, width=k(5))
    # Moncong + hidung + mulut
    elips(842, 288, 48, 30, fill=MUZZLE)
    d.rounded_rectangle([k(858), k(258), k(892), k(282)], radius=k(11),
                        fill=HIDUNG)
    d.line([(k(875), k(282)), (k(875), k(296))], fill=HIDUNG, width=k(5))
    d.arc([k(848), k(286), k(878), k(308)], start=20, end=160,
          fill=HIDUNG, width=k(5))
    d.arc([k(872), k(286), k(902), k(308)], start=20, end=160,
          fill=HIDUNG, width=k(5))

    return _skala(img, (W, H))


def gambar_sumber_aung():
    """Singa pose mengaum: kepala mendongak, mulut terbuka lebar."""
    W, H = 1000, 560
    img = Image.new("RGB", (W * SS, H * SS), PUTIH)
    d = ImageDraw.Draw(img)

    def k(v):
        return v * SS

    def kotak(x0, y0, x1, y1, **kw):
        d.rounded_rectangle([k(x0), k(y0), k(x1), k(y1)],
                            radius=k(26), **kw)

    def elips(cx, cy, rx, ry, **kw):
        d.ellipse([k(cx - rx), k(cy - ry), k(cx + rx), k(cy + ry)], **kw)

    # --- Ekor (sama seperti pose jalan) ---
    ekor = [(168, 238), (128, 205), (102, 168), (94, 132)]
    d.line([(k(x), k(y)) for x, y in ekor], fill=EMAS, width=k(21))
    for (jx, jy) in ekor:
        elips(jx, jy, 10, 10, fill=EMAS)
    elips(92, 118, 24, 32, fill=SURAI_GELAP)

    # --- Kaki menahan badan (stance kokoh, sedikit lebih renggang) ---
    kaki_def = [(205, EMAS_GELAP), (315, EMAS), (565, EMAS_GELAP), (655, EMAS)]
    for cx, warna in kaki_def:
        kotak(cx - 29, 315, cx + 29, 520, fill=warna)
        elips(cx + 4, 522, 36, 14, fill=warna)

    # --- Badan ---
    d.rounded_rectangle([k(155), k(195), k(730), k(372)], radius=k(88),
                        fill=EMAS)
    elips(440, 334, 180, 32, fill=PERUT)

    # --- Surai lebih besar (mengembang saat mengaum) ---
    cx_s, cy_s, r_s = 750, 208, 148
    for sudut in range(0, 360, 24):
        a = math.radians(sudut)
        elips(cx_s + r_s * 0.84 * math.cos(a), cy_s + r_s * 0.84 * math.sin(a),
              44, 44, fill=SURAI)
    elips(cx_s, cy_s, r_s, r_s, fill=SURAI)
    elips(cx_s, cy_s, r_s - 24, r_s - 24, fill=SURAI_GELAP)

    # --- Telinga terlipat ke belakang ---
    elips(695, 105, 25, 25, fill=SURAI)
    elips(695, 105, 12, 12, fill=EMAS_MUDA)

    # --- Wajah mendongak ---
    elips(768, 198, 94, 94, fill=EMAS_MUDA)
    # Mata memejam garang (lengkungan tertutup)
    d.arc([k(782), k(138), k(830), k(180)], start=15, end=165,
          fill=(40, 26, 18), width=k(7))
    # Moncong terangkat
    elips(838, 200, 50, 38, fill=MUZZLE)
    d.rounded_rectangle([k(858), k(166), k(898), k(194)], radius=k(12),
                        fill=HIDUNG)
    # --- Mulut TERBUKA lebar: bagian dalam + lidah + taring ---
    elips(845, 258, 50, 44, fill=MULUT_DALAM)
    elips(845, 282, 32, 19, fill=LIDAH)  # lidah
    # Taring atas (putih, di DALAM mulut -> aman dari flood-fill)
    d.polygon([(k(813), k(228)), (k(829), k(228)), (k(821), k(254))],
              fill=PUTIH)
    d.polygon([(k(861), k(228)), (k(877), k(228)), (k(869), k(254))],
              fill=PUTIH)
    # Taring bawah kecil
    d.polygon([(k(825), k(294)), (k(837), k(294)), (k(831), k(276))],
              fill=PUTIH)
    d.polygon([(k(853), k(294)), (k(865), k(294)), (k(859), k(276))],
              fill=PUTIH)
    # Rahang bawah
    d.arc([k(799), k(228), k(891), k(306)], start=0, end=180,
          fill=SURAI_GELAP, width=k(5))

    return _skala(img, (W, H))


# ---------------------------------------------------------------------------
# Langkah 1 - Hapus background putih pada gambar
# ---------------------------------------------------------------------------
def hapus_background_putih(path_gambar=None, gambar=None):
    """Mengembalikan gambar RGBA dengan background transparan."""
    if gambar is None:
        gambar = Image.open(path_gambar).convert("RGB")
    piksel = np.array(gambar)

    nyaris_putih = (
        (piksel[:, :, 0] > 240)
        & (piksel[:, :, 1] > 240)
        & (piksel[:, :, 2] > 240)
    )
    # Kelompok piksel putih yang menyentuh tepi = background
    label, _ = ndimage.label(nyaris_putih)
    label_tepi = set(np.unique(np.concatenate([
        label[0, :], label[-1, :], label[:, 0], label[:, -1]
    ])))
    label_tepi.discard(0)
    background = np.isin(label, list(label_tepi))

    alpha = np.where(background, 0, 255).astype(np.uint8)
    alpha_img = Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(1))

    hasil = gambar.convert("RGBA")
    hasil.putalpha(alpha_img)
    return hasil.crop(hasil.getbbox())


# ---------------------------------------------------------------------------
# Langkah 2 - Rig walk cycle: potong gambar jalan menjadi badan + 4 kaki
# ---------------------------------------------------------------------------
def buat_rig_jalan(singa_jalan, y_potong_badan=0.64):
    """
    Memotong gambar pose berjalan menjadi:
      - badan (digambar paling atas, menutupi pangkal kaki)
      - 4 potongan kaki yang bisa diputar pada poros pangkalnya.
    Kelompok kaki dicari otomatis dari proyeksi piksel pada area
    bawah gambar. Pasangan kaki diagonal bergerak sefase (gaya trot):
    (kaki depan dekat + kaki belakang jauh) berlawanan fase dengan
    (kaki depan jauh + kaki belakang dekat).
    """
    lebar, tinggi = singa_jalan.size
    alpha = np.array(singa_jalan.getchannel("A"))

    # Proyeksi piksel tidak transparan pada 32% bagian bawah gambar
    proyeksi = (alpha[int(tinggi * 0.68):, :] > 30).sum(axis=0)
    kelompok = []
    awal = None
    for x, nilai in enumerate(proyeksi):
        if nilai > 5 and awal is None:
            awal = x
        elif nilai <= 5 and awal is not None:
            if x - awal > lebar * 0.02:
                kelompok.append((awal, x))
            awal = None
    if awal is not None:
        kelompok.append((awal, lebar))
    assert len(kelompok) == 4, f"Kaki terdeteksi {len(kelompok)}, harusnya 4"

    y_potong_badan = int(tinggi * y_potong_badan)   # badan menutupi sampai sini
    y_mulai_kaki = int(tinggi * 0.46)     # potongan kaki mulai dari sini
    badan = singa_jalan.crop((0, 0, lebar, y_potong_badan))

    # Urutan kelompok dari kiri: belakang-jauh, belakang-dekat,
    # depan-jauh, depan-dekat. Fase trot: kelompok 0 & 3 sefase,
    # kelompok 1 & 2 berlawanan.
    fase_kaki = [0.0, math.pi, math.pi, 0.0]
    kaki = []
    for (x0, x1), fase in zip(kelompok, fase_kaki):
        tepi = int(lebar * 0.02)
        x_kiri = max(0, x0 - tepi)
        x_kanan = min(lebar, x1 + tepi)
        potongan = singa_jalan.crop((x_kiri, y_mulai_kaki, x_kanan, tinggi))
        kaki.append({
            "gambar": potongan,
            "x": x_kiri,
            "y": y_mulai_kaki,
            "poros_x": (x0 + x1) // 2 - x_kiri,  # poros putar (pangkal kaki)
            "poros_y": int(tinggi * 0.06),
            "fase": fase,
            # Info tambahan untuk ekspor aset web (rig.js + PNG lapisan)
            "tengah_x": (x0 + x1) / 2 / lebar * 100,
        })
    return {"badan": badan, "kaki": kaki, "ukuran": (lebar, tinggi)}


def gambar_singa_jalan(rig, fase_jalan, kekuatan=1.0):
    """
    Merakit satu frame pose berjalan.
    fase_jalan : sudut siklus langkah (radian, bertambah selama berjalan)
    kekuatan   : 1 = melangkah penuh, 0 = kaki diam (dipakai saat berhenti)
    """
    lebar, tinggi = rig["ukuran"]
    kanvas = Image.new("RGBA", (lebar, tinggi), (0, 0, 0, 0))
    for kaki in rig["kaki"]:
        sudut = 8.0 * kekuatan * math.sin(fase_jalan + kaki["fase"])
        potongan = kaki["gambar"].rotate(
            sudut, resample=Image.BICUBIC,
            center=(kaki["poros_x"], kaki["poros_y"]),
        )
        kanvas.alpha_composite(potongan, (kaki["x"], kaki["y"]))
    # Badan digambar terakhir supaya menutupi pangkal kaki
    kanvas.alpha_composite(rig["badan"], (0, 0))
    return kanvas


# ---------------------------------------------------------------------------
# Langkah 2b - Ekspor aset web (badan.png, kaki1-4.png, singa_rawr.png, rig.js)
# ---------------------------------------------------------------------------
def ekspor_aset_web(singa_jalan_rgba, singa_aung_rgba, rig):
    """Lapisan PNG seukuran kanvas penuh + rig.js untuk halaman web."""
    lebar, tinggi = rig["ukuran"]
    y_potong = int(tinggi * 0.64)
    y_mulai = int(tinggi * 0.46)

    # singa_rawr.png = pose mengaum transparan
    singa_aung_rgba.save(FOLDER / "singa_rawr.png")

    # badan.png = kanvas penuh, isinya hanya bagian di atas potongan badan
    badan_full = Image.new("RGBA", (lebar, tinggi), (0, 0, 0, 0))
    badan_full.alpha_composite(
        singa_jalan_rgba.crop((0, 0, lebar, y_potong)), (0, 0))
    badan_full.save(FOLDER / "badan.png")

    data_rig = []
    alpha = np.array(singa_jalan_rgba.getchannel("A"))
    proyeksi = (alpha[int(tinggi * 0.68):, :] > 30).sum(axis=0)
    kelompok = []
    awal = None
    for x, nilai in enumerate(proyeksi):
        if nilai > 5 and awal is None:
            awal = x
        elif nilai <= 5 and awal is not None:
            if x - awal > lebar * 0.02:
                kelompok.append((awal, x))
            awal = None
    if awal is not None:
        kelompok.append((awal, lebar))

    poros_y_persen = (y_mulai + int(tinggi * 0.06)) / tinggi * 100
    for i, ((x0, x1), kaki) in enumerate(zip(kelompok, rig["kaki"]), start=1):
        lapisan = Image.new("RGBA", (lebar, tinggi), (0, 0, 0, 0))
        tepi = int(lebar * 0.02)
        x_kiri, x_kanan = max(0, x0 - tepi), min(lebar, x1 + tepi)
        potongan = singa_jalan_rgba.crop((x_kiri, y_mulai, x_kanan, tinggi))
        lapisan.alpha_composite(potongan, (x_kiri, y_mulai))
        # Nol-kan semua piksel di luar rentang x kaki ini (jaga-jaga tumpang tindih)
        arr = np.array(lapisan)
        arr[:, :x_kiri, 3] = 0
        arr[:, x_kanan:, 3] = 0
        arr[:y_mulai, :, 3] = 0
        lapisan = Image.fromarray(arr)
        lapisan.save(FOLDER / f"kaki{i}.png")
        data_rig.append({
            "file": f"kaki{i}.png",
            "porosX": round(kaki["tengah_x"], 2),
            "porosY": round(poros_y_persen, 2),
            "fase": round(kaki["fase"], 4),
        })

    isi = ("// Data walk cycle (poros putar dalam persen kanvas, "
           "fase dalam radian)\n")
    isi += "const RIG_KAKI = " + json.dumps(data_rig, indent=2) + ";\n"
    (FOLDER / "rig.js").write_text(isi, encoding="utf-8")
    print("Aset web tersimpan: badan.png, kaki1-4.png, singa_rawr.png, rig.js")


# ---------------------------------------------------------------------------
# Langkah 3 - Latar hutan saat petang
# ---------------------------------------------------------------------------
def buat_latar():
    """Gradasi langit petang + matahari terbenam + siluet hutan."""
    latar = Image.new("RGB", (LEBAR, TINGGI))
    piksel = np.zeros((TINGGI, LEBAR, 3), dtype=float)
    # Palet petang: ungu gelap -> magenta -> oranye -> kuning di horizon
    pemberhentian = [
        (0.00, np.array([38, 22, 66], dtype=float)),
        (0.34, np.array([110, 44, 94], dtype=float)),
        (0.58, np.array([214, 84, 62], dtype=float)),
        (0.76, np.array([255, 138, 61], dtype=float)),
        (0.86, np.array([255, 190, 92], dtype=float)),
        (1.00, np.array([66, 38, 52], dtype=float)),  # tanah gelap petang
    ]
    for y in range(TINGGI):
        t = y / TINGGI
        for (t0, c0), (t1, c1) in zip(pemberhentian, pemberhentian[1:]):
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0) if t1 > t0 else 0
                piksel[y, :, :] = c0 + (c1 - c0) * f
                break
    latar = Image.fromarray(piksel.astype(np.uint8), "RGB").convert("RGBA")
    gambar = ImageDraw.Draw(latar, "RGBA")

    rng = np.random.default_rng(42)
    # Bintang tipis di langit atas (petang baru mulai)
    bintang = []
    for _ in range(60):
        bx, by = int(rng.integers(0, LEBAR)), int(rng.integers(0, 240))
        br = float(rng.uniform(0.8, 1.8))
        bintang.append((bx, by, br))
        gambar.ellipse([bx - br, by - br, bx + br, by + br],
                       fill=(255, 244, 214, 150))
    # Kunang-kunang dekat tanah hutan
    kunang = []
    for _ in range(26):
        kx = int(rng.integers(0, LEBAR))
        ky = int(rng.integers(500, 660))
        kunang.append((kx, ky, float(rng.uniform(0, 6.28))))
    # Barisan pepohonan jauh (siluet)
    bukit = [(0, 520), (150, 470), (330, 512), (520, 462), (710, 508),
             (900, 470), (1080, 514), (1280, 478), (1280, 720), (0, 720)]
    gambar.polygon(bukit, fill=(52, 30, 58, 255))
    # Tanah hutan
    gambar.ellipse([-200, 580, LEBAR + 200, 920], fill=(36, 22, 40, 255))
    return latar, bintang, kunang, rng


def buat_matahari():
    ukuran = 420
    matahari = Image.new("RGBA", (ukuran, ukuran), (0, 0, 0, 0))
    d = ImageDraw.Draw(matahari)
    for r in range(190, 92, -6):  # cahaya menyebar (glow)
        alpha = int(80 * (190 - r) / 98)
        d.ellipse([ukuran / 2 - r, ukuran / 2 - r, ukuran / 2 + r,
                   ukuran / 2 + r], fill=(255, 176, 84, alpha))
    d.ellipse([ukuran / 2 - 92, ukuran / 2 - 92, ukuran / 2 + 92,
               ukuran / 2 + 92], fill=(255, 205, 105, 255))
    d.ellipse([ukuran / 2 - 92, ukuran / 2 - 30, ukuran / 2 + 92,
               ukuran / 2 + 92], fill=(255, 178, 84, 255))
    return matahari


def gambar_akasia(d, x, pangkal, tinggi):
    """Pohon akasia khas hutan/savana: batang bercabang + tajuk datar."""
    warna = (24, 15, 30, 255)
    d.line([(x, pangkal), (x - 6, pangkal - tinggi * 0.45)], fill=warna,
           width=9)
    d.line([(x, pangkal), (x + 16, pangkal - tinggi * 0.5)], fill=warna,
           width=7)
    for dx in (-46, -14, 22, 54):
        d.line([(x + dx // 3, pangkal - tinggi * 0.48),
                (x + dx, pangkal - tinggi * 0.62)], fill=warna, width=5)
    lebar_tajuk = tinggi * 1.15
    d.ellipse([x - lebar_tajuk / 2, pangkal - tinggi * 0.78,
               x + lebar_tajuk / 2, pangkal - tinggi * 0.52], fill=warna)
    d.ellipse([x - lebar_tajuk * 0.32, pangkal - tinggi * 0.88,
               x + lebar_tajuk * 0.32, pangkal - tinggi * 0.62], fill=warna)


def gambar_pinus_petang(d, x, pangkal, tinggi):
    warna = (24, 15, 30, 255)
    d.rectangle([x - 4, pangkal - 26, x + 4, pangkal], fill=warna)
    for i in range(3):
        lebar_i = (tinggi * 0.42) * (1 - i * 0.26)
        y_atas = pangkal - 20 - (i + 1) * (tinggi / 3.4)
        y_bawah = pangkal - 10 - i * (tinggi / 3.4)
        d.polygon([(x - lebar_i / 2, y_bawah), (x + lebar_i / 2, y_bawah),
                   (x, y_atas)], fill=warna)


# ---------------------------------------------------------------------------
# Langkah 4 - Animasi per frame
# ---------------------------------------------------------------------------
def muat_font(ukuran):
    for kandidat in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]:
        if Path(kandidat).exists():
            try:
                return ImageFont.truetype(kandidat, ukuran)
            except OSError:
                pass
    return ImageFont.load_default()


def amplop_aung(t):
    """Perkiraan kerasnya auman terhadap waktu (untuk denyut & gelombang)."""
    if t < MULAI_AUNG or t > AKHIR_AUNG:
        return 0.0
    x = (t - MULAI_AUNG) / (AKHIR_AUNG - MULAI_AUNG)
    # Auman singa: membuka keras, gelombang dengkur, lalu menutup
    return float(max(0.0, math.sin(x * math.pi) ** 1.4 *
                     (0.72 + 0.28 * math.sin(x * 22.0))))


def buat_audio_video():
    """Buat auman_singa.mp3: semilir hutan pelan + auman mulai detik 5,9."""
    if FILE_SUARA.exists() or not FILE_SUARA_WEB.exists():
        return
    jeda_ms = int(MULAI_AUNG * 1000)
    perintah = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(FILE_SUARA_WEB),
        "-f", "lavfi", "-i",
        f"anoisesrc=color=brown:duration={DURASI}:sample_rate=44100",
        "-filter_complex",
        (f"[1:a]lowpass=f=420,volume=0.055[ambien];"
         f"[0:a]adelay={jeda_ms}:all=1,volume=1.0[aung];"
         f"[ambien][aung]amix=inputs=2:duration=first:dropout_transition=0,"
         f"atrim=0:{DURASI},loudnorm=I=-16:TP=-1.5:LRA=11[out]"),
        "-map", "[out]", "-c:a", "libmp3lame", "-q:a", "3",
        str(FILE_SUARA),
    ]
    subprocess.run(perintah, check=True)
    print("Audio video dibuat:", FILE_SUARA.name)


def render_frame(t, latar, matahari, rig, singa_aung_img, kunang, pohon):
    frame = latar.copy()
    d = ImageDraw.Draw(frame, "RGBA")

    # --- Matahari terbenam: berdenyut halus, membesar saat mengaum ---
    env = amplop_aung(t)
    skala_m = 1.0 + 0.05 * math.sin(t * 1.6) + env * 0.10
    uk_m = int(330 * skala_m)
    m = matahari.resize((uk_m, uk_m), Image.BILINEAR)
    frame.alpha_composite(m, (LEBAR - 330 - (uk_m - 330) // 2,
                              205 - (uk_m - 330) // 2))

    # --- Pohon parallax (bergerak hanya saat singa berjalan) ---
    if t < AKHIR_JALAN:
        geser = (t / AKHIR_JALAN) * 620
    else:
        geser = 620
    for (px, ptinggi, jenis) in pohon:
        x = px - (geser * (0.35 if jenis == "akasia" else 0.6)) % (LEBAR + 320)
        if x < -180:
            x += LEBAR + 320
        if jenis == "akasia":
            gambar_akasia(d, int(x), 618, ptinggi)
        else:
            gambar_pinus_petang(d, int(x), 622, ptinggi)

    # --- Kunang-kunang berkelip ---
    for (kx, ky, fase_k) in kunang:
        kedip = 0.5 + 0.5 * math.sin(t * 2.2 + fase_k)
        r = 2 + 2 * kedip
        d.ellipse([kx - r, ky - r, kx + r, ky + r],
                  fill=(255, 236, 150, int(70 + 160 * kedip)))

    # --- Singa ---
    tinggi_tampil = int(LEBAR_TAMPIL * rig["ukuran"][1] / rig["ukuran"][0])
    if t < AKHIR_JALAN:
        # Berjalan masuk dari kiri dengan langkah trot
        kemajuan = t / AKHIR_JALAN
        kemajuan = kemajuan * kemajuan * (3 - 2 * kemajuan)  # smoothstep
        x_singa = int(-LEBAR_TAMPIL + (TARGET_X + LEBAR_TAMPIL) * kemajuan)
        fase = t * (2 * math.pi / 0.85)
        kekuatan = min(1.0, kemajuan * 4 + 0.25)
        img = gambar_singa_jalan(rig, fase, kekuatan)
        bob = -abs(math.sin(fase)) * 7
    elif t < AKHIR_GANTI_POSE:
        x_singa = TARGET_X
        img = gambar_singa_jalan(rig, AKHIR_JALAN * (2 * math.pi / 0.85), 0.0)
        bob = 0
        # Crossfade ke pose mengaum
        f = (t - AKHIR_JALAN) / (AKHIR_GANTI_POSE - AKHIR_JALAN)
        aung_kecil = singa_aung_img.resize((LEBAR_TAMPIL, tinggi_tampil),
                                           Image.LANCZOS)
        jalan_kecil = img.resize((LEBAR_TAMPIL, tinggi_tampil), Image.LANCZOS)
        img = Image.blend(jalan_kecil, aung_kecil, f)
        frame.alpha_composite(img, (x_singa, TANAH_Y - tinggi_tampil))
        img = None
    else:
        x_singa = TARGET_X
        denyut = 1.0 + env * 0.022
        cw, ch = singa_aung_img.size
        uk = (int(LEBAR_TAMPIL * denyut),
              int(LEBAR_TAMPIL * ch / cw * denyut))
        img = singa_aung_img.resize(uk, Image.LANCZOS)
        bob = 0
        # Gelombang suara keluar dari mulut
        mulut_x = x_singa + int(uk[0] * MULUT_X)
        mulut_y = (TANAH_Y - uk[1]) + int(uk[1] * MULUT_Y)
        if env > 0.03:
            for gi in range(3):
                fr = ((t * 0.85 + gi / 3) % 1)
                r_g = int(26 + fr * 175)
                alpha_g = int(max(0.0, (1 - fr)) * (40 + env * 190))
                d.ellipse([mulut_x - r_g, mulut_y - r_g,
                           mulut_x + r_g, mulut_y + r_g],
                          outline=(255, 240, 200, alpha_g), width=6)
        frame.alpha_composite(img, (x_singa, TANAH_Y - uk[1]))
        img = None

    if img is not None:
        img_kecil = img.resize((LEBAR_TAMPIL, tinggi_tampil), Image.LANCZOS)
        frame.alpha_composite(img_kecil,
                              (x_singa, TANAH_Y - tinggi_tampil + int(bob)))

    # --- Judul kecil di awal video ---
    if t < 3.2:
        alpha_j = int(255 * min(1.0, t / 0.6, (3.2 - t) / 0.8))
        font = muat_font(40)
        teks = "RAWR si Singa - Hutan Petang"
        kotak = d.textbbox((0, 0), teks, font=font)
        d.text(((LEBAR - (kotak[2] - kotak[0])) / 2, 36), teks, font=font,
               fill=(255, 240, 205, alpha_j))

    # --- Fade-out di akhir ---
    if t > AKHIR_AUNG:
        f = (t - AKHIR_AUNG) / (DURASI - AKHIR_AUNG)
        hitam = Image.new("RGBA", (LEBAR, TINGGI), (0, 0, 0, int(255 * f)))
        frame.alpha_composite(hitam)
    return frame.convert("RGB")


def main():
    # 0) Sumber gambar: gambar sendiri bila belum ada
    if not FILE_JALAN.exists():
        gambar_sumber_jalan().save(FILE_JALAN)
        print("Sumber digambar:", FILE_JALAN.name)
    if not FILE_AUNG.exists():
        gambar_sumber_aung().save(FILE_AUNG)
        print("Sumber digambar:", FILE_AUNG.name)

    # 1) Hapus background putih + buat rig
    print("Menghapus background putih (flood-fill dari tepi)...")
    jalan_rgba_penuh = hapus_background_putih(gambar=Image.open(FILE_JALAN).convert("RGB"))
    # Kembalikan ke kanvas penuh 1000x560 (crop getbbox mengubah ukuran) -
    # gambar ulang transparan di kanvas penuh lewat tempel di posisi bbox:
    # hapus_background_putih versi repo ini memotong rapat; untuk rig web
    # kita butuh kanvas konsisten, jadi tempel hasil crop ke kanvas kosong
    # tidak bisa memulihkan posisi aslinya. Karena itu lakukan penghapusan
    # tanpa crop untuk aset web:
    def transparan_tanpa_crop(path):
        g = Image.open(path).convert("RGB")
        piksel = np.array(g)
        putih = ((piksel[:, :, 0] > 240) & (piksel[:, :, 1] > 240)
                 & (piksel[:, :, 2] > 240))
        label, _ = ndimage.label(putih)
        tepi = set(np.unique(np.concatenate(
            [label[0, :], label[-1, :], label[:, 0], label[:, -1]])))
        tepi.discard(0)
        bg = np.isin(label, list(tepi))
        alpha = Image.fromarray(
            np.where(bg, 0, 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(1))
        out = g.convert("RGBA")
        out.putalpha(alpha)
        return out

    jalan_full = transparan_tanpa_crop(FILE_JALAN)
    aung_full = transparan_tanpa_crop(FILE_AUNG)
    aung_crop = hapus_background_putih(gambar=Image.open(FILE_AUNG).convert("RGB"))

    rig = buat_rig_jalan(jalan_full)
    print(f"Rig jadi: badan + {len(rig['kaki'])} kaki terdeteksi.")

    # 2) Ekspor aset web + pose mengaum transparan (ukuran crop rapat)
    ekspor_aset_web(jalan_full, aung_full, rig)
    # singa_rawr.png versi kanvas penuh ditimpa crop rapat untuk video? -
    # untuk web dipakai kanvas penuh agar posisinya sejajar pose jalan.
    # (ekspor_aset_web sudah menyimpan versi kanvas penuh.)

    # 3) Latar + pohon
    latar, _bintang, kunang, rng = buat_latar()
    matahari = buat_matahari()
    pohon = [(90, 150, "akasia"), (330, 105, "pinus"), (1110, 165, "akasia"),
             (1250, 95, "pinus"), (700, 80, "pinus")]

    # Pose mengaum untuk video: pakai versi crop rapat, diskalakan per frame
    singa_aung_img = aung_crop

    # Rig video memakai gambar crop? Tidak: rig dibuat dari kanvas penuh,
    # dan gambar_singa_jalan mengembalikan kanvas penuh 1000x560. Untuk
    # video, pose jalan dirakit dari rig kanvas penuh itu (konsisten).
    # Pose mengaum diskalakan ke lebar tampil yang sama, kakinya menapak
    # di TANAH_Y lewat perbandingan tinggi crop terhadap lebarnya.

    # 4) Audio video (bila belum ada)
    buat_audio_video()

    # 5) Render frame -> FFmpeg
    if not FILE_SUARA.exists():
        print("PERINGATAN: auman_singa.mp3 tidak ada, video tanpa suara.",
              file=sys.stderr)
        cmd_audio = ["-an"]
    else:
        cmd_audio = ["-i", str(FILE_SUARA), "-c:a", "aac", "-b:a", "160k",
                     "-shortest"]
    perintah = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{LEBAR}x{TINGGI}", "-r", str(FPS), "-i", "-",
        *cmd_audio,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19",
        "-movflags", "+faststart", str(FILE_VIDEO),
    ]
    print(f"Merender {TOTAL_FRAME} frame -> {FILE_VIDEO.name} ...")
    proses = subprocess.Popen(perintah, stdin=subprocess.PIPE)
    poster_tersimpan = False
    try:
        for i in range(TOTAL_FRAME):
            t = i / FPS
            frame = render_frame(t, latar, matahari, rig, singa_aung_img,
                                 kunang, pohon)
            if not poster_tersimpan and t >= 8.0:
                frame.save(FOLDER / "poster.jpg", quality=88)
                poster_tersimpan = True
            proses.stdin.write(frame.tobytes())
            if i % 60 == 0:
                print(f"  frame {i}/{TOTAL_FRAME}")
    finally:
        if proses.stdin:
            proses.stdin.close()
        proses.wait()
    if proses.returncode != 0:
        raise SystemExit("FFmpeg gagal membuat video.")
    print("Selesai:", FILE_VIDEO)


if __name__ == "__main__":
    main()
