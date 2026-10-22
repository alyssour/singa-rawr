# Singa Bergerak dan Bersuara (Python) — RAWR si Singa 🦁

Tugas Multimedia: mengubah gambar diam hewan singa menjadi video yang
bergerak dan bersuara, dibuat dengan Python (Pillow, NumPy, SciPy, FFmpeg).
Tema: singa berjalan di **hutan saat petang** (matahari terbenam), lalu
berhenti dan **mengaum — "AUUUMMM... RAWR!"**

**Halaman tugas (GitHub Pages):** https://alyssour.github.io/singa-rawr/

Halamannya interaktif: singa berjalan terus di panggung (walk cycle),
klik singanya atau tekan Spasi untuk mengaum, ada slider kecepatan
dan volume, dan equalizer yang bergerak mengikuti suara (Web Audio API).
Di halaman yang sama ada juga versi video MP4 hasil program Python.

Isi repo:
- `index.html` - halaman GitHub Pages interaktif
- `rig.js` - data poros putar kaki untuk walk cycle
- `badan.png`, `kaki1-4.png` - lapisan gambar pose berjalan
- `singa_rawr.png` - gambar pose mengaum transparan
- `auman.mp3` - suara auman untuk halaman interaktif
- `singa_bergerak.mp4` - video hasil program Python (14 detik, 720p)
- `buat_singa_bergerak.py` - program Python pembuat video + aset web
- `singa_jalan.png`, `singa.png` - gambar sumber kedua pose (digambar
  sendiri oleh program Python di atas latar putih)
- `auman_singa.mp3` - audio video (semilir hutan petang + auman)
- `poster.jpg` - gambar sampul pemutar video

Menjalankan ulang program video:
```
pip install pillow numpy scipy
python buat_singa_bergerak.py
```
(FFmpeg harus terinstall.)

Cara kerja singkat:
1. Program **menggambar sendiri** kedua pose singa memakai Pillow.
2. Background putih dihapus dengan flood-fill dari tepi gambar
   (SciPy `ndimage.label`) sehingga menjadi transparan.
3. Pose berjalan dipotong menjadi badan + 4 kaki (rig walk cycle,
   pola trot: kaki diagonal bergerak sefase).
4. 420 frame (14 detik @ 30 fps) dirender satu per satu: singa berjalan
   masuk melintasi hutan petang (parallax pohon akasia, kunang-kunang,
   matahari terbenam), berhenti, lalu mengaum dengan gelombang suara
   dari mulutnya — persis bersamaan dengan audio aumannya.
5. Frame digabung menjadi MP4 memakai FFmpeg.

Suara auman: rekaman singa asli "Lion roaring", Wikimedia Commons
(singa jantan di Tamil Nadu), dipotong + dinaikkan volumenya dengan FFmpeg.

Alyssa Nurul Hidayat - NIM 242502040081 - Kelas 3TI01
