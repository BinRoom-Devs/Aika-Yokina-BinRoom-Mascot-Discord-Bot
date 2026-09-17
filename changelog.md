# Changelog

Perubahan pada bot akan dicatat pada file ini.

Changelog ini mengikuti format [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) dan projek ini mengadopsi [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## v2.5.3 - 16 Sept 2026
### Perubahan:
- Model AI Aika diganti ke [Groq Qwen 3.8 27B](https://console.groq.com/docs/model/qwen/qwen3.8-27b) karena model sebelumnya (3.6) tiba-tiba gabisa njir.


## v2.5.2 - 14 Sept 2026
### Perbaikan:
- Ngebenerin logging yang gak work, sekaligus ngerapiin tampilan embed-nya.


## v2.5.1
### Perbaikan:
- Sistem pencatatan durasi voice channel untuk logging diperbaiki.


## v2.5.0
### Penambahan:
- Implementasi JSON untuk menampung data waktu voice agar timer tidak reset dari awal kalau bot restart.

- Ditambahkan satu kategori aktivitas voice untuk direkam durasinya: durasi VC.

### Perbaikan:
- Beberapa bug di logging diperbarui.

- Sedikit perubahan pada peletakan variabel yang berisi versioning bot.


## v2.4.0
### Penambahan:
- AI Aika ditambahkan fitur penalaran. Normalnya, Aika tidak menerima pertanyaan atau prompt kompleks; pure sebagai chatbot persona biasa. Dengan penambahan penalaran ini (yang bisa diaktifkan dengan me-mention role `@reasoning`), para member bisa menanyakan pertanyaan kompleks kepada Aika dan Aika pun akan menjawabnya. (⚠️ Agak boros token sih untuk tiap pesan yang pakai reasoning, jadi tolong gunakan dengan bijak).

- Saat Aika mengirim respon AI, dia akan nge-log ke channel logging khusus admin dan nampilin berapa token terpakai.


## v2.3.0 - 13 Sept 2026
### Penambahan:
- Logging ketambahan pencatat waktu untuk aktivitas VC: streaming.

- Laporan rangkuman logging untuk seharian aktivitas server.

### Perubahan:
- Keterangan pada command `clear cache` diubah ke bahasa Indonesia.


## v2.2.0
### Penambahan:
- Ditambahkan penghitung waktu member VC untuk logging dan akan diberitahu jika member keluar VC.

- Logging pesan dihapus kini bisa menangkap attachments lebih dari satu menggunakan Components v2.


## v2.1.4
### Perubahan:
- Rapiin kodingan pake linter.


## v2.1.1 - 11 Sept 2026
### Perbaikan:
- Emoji untuk kategori aktviitas masuk server/vc diubah dari 📩 ke 📥.
### Perubahan:
- Logging foto profil member diubah dari global ke lokal. Dari yang logging-nya ke-trigger kalo ngubah pfp asli akun ke ngubah pfp khusus BinRoom doang.


## v2.1.0
### Penambahan:
- Logging ketambahan satu aktivitas baru: reaction.
- Command `stats` ditambahkan keterangan versi bot nya Aika.

### Perubahan:
- Upgrade Python dari v3.13.14 ke v.3.14.7


## v2.0.2 - 9 Sept 2026


## v2.0.1


## v2.0.0


## v1.3.0 - 26 Agst 2026
### Penambahan:
- Command baru: `cek_kuota_ai`: mirip dengan `ai_chatbot_stats` tapi yang ini lebih ringkas; cuma info kuotanya doang, gaada info tambahan/lengkap kayak berapa token yang kepake macam di command `ai_chatbot_stats`.

- Command `ping` ditambahin logic full-range RGB biar makin dinamis sama angka latensinya.

- Footer embed untuk aktivitas VC ditambahin dengan ID dari VC-nya.

### Perubahan:
- Migrasi hostingan.

- Tampilan embed di command `ping`: ditambahin tulisan "Latensi Aika" di bagian atas.

- Bar/garis indikator kuota AI dikasih warna kayak meteran, dan redesain tampilan bar nya.


## v1.2.0 - 24 Agst 2026
### Penambahan:
- Command baru: `ai_chatbot_stats` biar bisa liat statistik penggunaan API dari Groq buat AI nya Aika.

- Sistem logging untuk para admin! Tersedia di channel khusus.


## v1.1.0 - 23 Agst 2026
### Perubahan:



## v1.0.0 - 20 Agst 2026