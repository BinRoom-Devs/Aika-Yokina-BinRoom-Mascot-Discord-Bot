# Changelog (Riwayat Pembaruan)

Perubahan pada bot akan dicatat pada file ini.

Changelog ini mengikuti format [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) dan projek ini mengadopsi sistem [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## v3.1.0 - 1 Okt 2026
### Penambahan:
- SISTEM STREAK! Sering2 nimbrung kalian di BinRoom, nanti streak harian kalian bakal naik. Absen sehari? Streak-mu hangus ygy. (Terinspirasi dari bot Kythia di Discord ID :DDDD)

- Command utilitas baru! `stiker` dan `emoji`, buat nampilin emoji atau stiker yang kalian request ke Aika.

### Perbaikan:
- Bugfix dan perbaikan logic pada `daily_stats.py` supaya statistiknya akurat, sesuai, dan logic pelaporannya tiap tengah malam di channel logging khusus admin betulan bisa work.


## v3.0.3 - 29 Sept 2026
### Penambahan:
- Ditambahkan countdown anniversary BinRoom, sekaligus kalimat ucapannya ke status kustomnya Aika.


## v3.0.2 - 28 Sept 2026
### Perbaikan:
- Bug pada command `userinfo` untuk membaca status voice yang menyebabkan command jadi crash diperbaiki.

- Sedikit perbaikan pada `serverinfo` yang menyebabkan tulisan "...lainnya" pada bagian emoji jadi ikutan besar gara-gara heading 1 nya Markdown.


## v3.0.1
### Perubahan:
- Pada command `userinfo`:
  - Jika orangnya lagi gak ada activity, field info-nya sekalian gabakal muncul.

  - Kalau orangnya cuma member biasa, alias gaada izin khusus, field info-nya sekalian juga gabakal muncul. 

  - Status VC-nya diubah dari teks jadi full emoji.

- Pada command `serverinfo`, rincian daftar emoji server dipakaikan pembatas huruf biar command-nya gak crash.

- Pada command `roleinfo`, ditambahkan handling kalau user gak ngasih role-nya.

### Perbaikan:
- Perbaikan penulisan dan huruf kapital.

- Pada command `userinfo`, emoji badge udah dibenerin dan dipastikan bakal nampilin emoji badge nya.

- Di command `userinfo` juga dihilangkan penanda code snippet (``) yang gak sengaja ternyata ngebungkus emoji status voice sekaligus sedikit bug fix.

- Sedikit bugfix di command `sistem` karena dia sebelumnya gabisa ngebaca penggunaan disk ketimbang di command `info`.


### Penambahan:
- Ditambahin tombol `Source code` di comand `help`.

## v3.0.0
### Perubahan:
- (Dalam kodingan) file-file cogs diatur dan dikategorikan dalam sub-folder.

- (Dalam kodingan) Di `bot.py` metode pencarian jalur file utama absolut diubah dari `.parent.parent` jadi `.parents` doang, sekaligus mindahin tempat deklarasi token ke dalam `start_bot()`.

- Ngubah semua nama command dari `snake_case` jadi `kebab-case`.

- Nge-hide semua command-command admin/dev only.

- Migrasi database total. 
  - Sebelumnya, ada beberapa data yang pakai JSON walaupun udah ada SQLite. Sekarang dipindahin dan digabungin semuanya ke SQLite.

  - Masih bagian dari migrasi database total, library `sqlite` + metode `threading.RLock` sekarang dialihkan ke `aiosqlite` biar fungsi asinkronisnya makin mantap.

### Penambahan:
- Akhirnya ni bot punya command `help` yang rapi dan custom... Command `help` nya mencakup command utama yang menampilkan seluruh command publiknya Aika, sekaligus sub-command yang bisa menampilkan detail tentang sebuah command (misalnya `ak!help pfp`).

- Command-command utilitas baru!
  - Fungsional bot: `status`/`uptime-status`: Kamu bisa intip status aktif Aika sekaligus riwayat gangguan koneksinya, apakah sempat down atau lancar-lancar aja.
  
  - Server dan Discord related: `userinfo`, `serverinfo`, `roleinfo`, `channelinfo`, `threadinfo`, dan `categoryinfo`.

  - Tool utilitas lainnya: `frame`, bisa kamu pakai untuk mem-fetch avatar frame / decoration nya orang. Command ini kayak pendampingnya `avatar` sama `banner` gitu.

- Fitur baru: kartu membership BinRoom!
  - Fitur ini memungkinkan para member mencetak kartu keanggotaan/membership BinRoom. Di kartunya mencakup foto profil, nama, tanggal bergabung, nomor member, status anggota, ID-mu, dan kode QR yang mengarah ke link profilmu.

  - Fitur ini juga disertai command untuk mengaksesnya:
    - `membership`: Menampilkan kartu membership-mu. Kalau sebelumnya belum pernah, nanti bakal dibuatin sama Aika. (Bisa juga dipake ke orang lain. Contoh: `ak!membership @Daffa`).

    - `membership customname`: Kalau kamu pengen nama kustom ketimbang nama akun Discord, pakai command ini. Contoh: `ak!membership customname Ilyas Hendika`. Bisa juga dipakai untuk menimpa nama kustom sebelumnya, caranya langsung eksekusi aja nama baru. Contoh, `ak!membership customname Orityles`

    - `membership resetname`: Mau reset dan balik ke nama Discord semula? Eksekusi aja ini.


### Perbaikan:
- Beberapa bug di logging, statistik harian, dan chatbot AI diperbaiki.

- Khususnya di fitur chatbot AI, sebelumnya, jika user sempat memakai fitur penalaran/reasoning, pesan-pesan non-reasoning selanjutnya juga akan menyedot token yang besar. Sekarang ini sudah diperbaiki, hore.

- Ngerapiin penamaan file jadi `snake_case` semua biar patuh dengan ketentuan PEP 8-nya Python.

### Penghapusan:
- Logging perubahan username global dihilangkan, opt total ke perubahan username lokal/server.


## v2.7.2 - 21 Sept 2026
### Perbaikan: 
- API key-nya Groq untuk fitur chatbot gak sengaja ke-revoke anjim, untung ditegur sama member 😂

- Pada logging, ditambahkan logic pembeda antara bot atau member saat ada yang keluar.

### Penambahan:
- Integrasi fitur bawaan Discord yang memungkinkan aplikasi/bot punya kontainer emojinya sendiri. Supaya gaperlu lagi minjam emoji dari server.


## v2.7.1
### Perbaikan:
- Sedikit bugfix di `info`: 

  - Ganti tulisan dari "Bahasa pemrograman" jadi "Bahasa program" biar lebih singkat.
  
  - (Dalam kodingan) fix bug kecil soalnya cog-nya gabisa ke-load otomatis njir (harus di-load manual pakai command `eval`).

  - Ganti format tanggal di footer update dari bentuk full (`20 September 2026`) jadi lebih singkat biar gak bocor sampe dua baris kalo diliat dari hape (`20/09/26`).

### Penghapusan:
- (Dalam hostingan) lupa ngehapus file stats.py njirrr.


## v2.7.0 - 20 Sept 2026
### Penambahan:
- Command baru: `info` dan `system`. Mereka ini basically pemisahan dari `stats` karena informasinya kegabung di command itu. Akhirnya sekarang dipisahin. `info` pure nampilin informasi bot nya, sedangkan `system` fokus ke informasi alokasi / rincian sistem. (Anggap aja command `info` itu versi refresh dari `stats` wkwk, skalian juga migrasi tampilan dari embed ke Components v2).

- Pada logging member keluar, di-kick, atau di-ban, ditambahkan info rentang waktu member tersebut berada di server. (Misalnya: member selama <u>2 tahun</u>).

- Aika sekarang bakal nyambut dan ngucapin dadah di `#keluar-masuk` kalau ada yang join atau keluar (atau bahkan ke-kick / ke-ban).

### Perubahan:
- Tampilan baru pada command `ping` dan `uptime`! Mereka berdua juga hijrah dari embed ke Components v2 biar lebih ganteng dan rapi, baik untuk mobile maupun desktop.

  - Pada command `ping`, selain redesain ulang tampilan, command ini juga ketambahan informasi latensi lain, yaitu REST API, Round-Trip, dan database.

- Command `eval` dan `terminal` juga ada perubahan tampilan: ditambahin header seolah-olah kayak window CMD di MacOS wkwk.

### Penghapusan:
- Sebagai bagian dari redesain tampilan `stats` yang sekarang berubah jadi `system`, tombol pada bawah embed-nya sekarang dihilangkan.



## v2.6.1 - 18 Sept 2026
### Perbaikan:
- Sedikit fix di command `version` biar bisa nge-fetch info build dan pembaruan dari git kalo lagi di hostingan.


## v2.6.0
## v2.6.0
### Penambahan:
- Command baru:

  - `eval` (khusus owner/dev) biar bisa utak-atik bot-nya lewat terminal **live langsung dari Discord** tanpa perlu repot-repot ke website hostingan.

  - `version`, buat ngecek versi bot tanpa harus baca embed besar lewat command `stats`.

- Ditambahkan error handling untuk command yang tak diketahui bot, sekaligus sistem saran jika ada typo saat ngetik nama command-nya.

- Ditambahin keterangan waktu pada footer di logging biar gampang ngeliat waktu logging-nya dari hape.

### Perubahan:
- (Dalam kodingan) variabel yang nge-host versi bot-nya dipindahin dari stats.py ke version.py 

- (Dalam kodingan) sistem deteksi token bot pada .env di bot.py diperkuat dengan `override=True`

- Command `terminal` migrasi dari embed ke Components v2.

- Optimisasi cog log.py.


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


## v2.0.1
### Perbaikan:
- Sedikit perbaikan pada command leaderboard GD (ada ketidakcocokan gambar kategori dengan warna embed).


## v2.0.0
Update besar-besaran untuk Aika! Setelah ngoding selama 2 minggu buat ngisi sisa-sisa libur semesternya owner loh ya.

### Penambahan:

- Respon dari Aika (chatbot AI) sekarang bisa di-regenerate! Caranya yaitu klik kanan di pesan terbaru dari AI Aika nya (kalau di hape, pesannya di klik trus tahan), pergi ke Apps, lalu pilih 'Buat ulang respon.'

- Sistem logging ketambahan beberapa kategori sekaligus ada peningkatan.

  - Judul embed-nya sekarang ditambahin emoji di awal biar makin representatif secara visual. (Baru ditengok bentar doang udah bisa ketahuan ini apa sebelum ngebaca teks apapun).

  - Ditambahkan logging on dan off Aika, sekalian juga kalau Aika-nya sempat keputus dari session gateway.

  - Ketambahan juga sistem pendeteksi konten sensitif dan Aika bakal ngelaporin ke para admin dengan cara nge-tag (hayoloh). Ditenagai oleh [Sightengine](https://sightengine.com/), sistem ini bisa mendeteksi konten sensitif mulai dari pesan yang bernada umpatan atau ujaran tak senonoh, sampai gambar/media sugestif, eksplisit, dan gore.

- Penambahan beberapa command-command utilitas:

  - `pfp`, buat ngeliat/nampilin foto profil orang.

  - `banner`, buat nampilin foto sampul orang.

  - `clear-cache` (khusus owner) buat ngebersihin bot Aika tanpa perlu restart.

  - `restart` dan `shutdown` (khusus owner) buat nge-restart atau matiin bot tanpa harus utak-atik terminal.

- Halaman web dashboard (khusus para admin) buat ngelola bot Aika!

- Leaderboard Geometry Dash untuk para player GD BinRoom! Bisa dilihat di channel `#leaderboard` pada kategori `BinRoom GD` atau lewat command `binroom-gd-leaderboard`.

### Perubahan:
- Migrasi sistem database dari JSON ke SQLite.

- Pembaruan dan peningkatan pada command `snipe`:

  - Tampilannya diganti, dari yang sebelumnya pakai embed biasa, sekarang pakai Components v2, bentuk *embed* baru dari Discord yang bisa muat lebih banyak info, dan bisa nampilin media lebih gede dari embed.

  - Daripada cuma bisa nangkap 1 pesan doang, command-nya sekarang bisa nangkap sampai **5 pesan**! Dan bisa dinavigasikan pakai sistem halaman.

  - Sebelumnya kalau pake embed cuma bisa nampilin 1 media (kalau pesan yang dihapus ada attachment-nya), sekarang berkat Components v2, attachment yang ditampilkan bisa lebih dari satu! (Kalau pesan yang dihapus punya attachment ganda).

  - Selain attachment gambar, command-nya juga udah bisa nangkap bentuk attachment lain kayak gif, video, bahkan file.

  - Sebagai cherry on top, warna embed — ehem, Components-nya — sekarang nyesuaiin sama warna dominan dari gambar yang ditampilin. 

- Command `uptime` ditambahkan detail waktu dinamis.

- Pada command `stats`, versi Aika sekarang ditampilkan di footer embed-nya.


### Perbaikan:
- Format waktu pada bagian uptime di command `stats` diperbaiki.


## v1.3.0 - 26 Agst 2026
### Penambahan:
- Command baru: `cek-kuota-ai`: mirip dengan `ai-chatbot-stats` tapi yang ini lebih ringkas; cuma info kuotanya doang, gaada info tambahan/lengkap kayak berapa token yang kepake macam di command `ai-chatbot-stats`.

- Command `ping` ditambahin logic full-range RGB biar makin dinamis sama angka latensinya.

- Footer embed untuk aktivitas VC ditambahin dengan ID dari VC-nya.

### Perubahan:
- Migrasi hostingan.

- Tampilan embed di command `ping`: ditambahin tulisan "Latensi Aika" di bagian atas.

- Bar/garis indikator kuota AI dikasih warna kayak meteran, dan redesain tampilan bar-nya.


## v1.2.0 - 24 Agst 2026
### Penambahan:
- Command baru: `ai-chatbot-stats` biar bisa liat statistik penggunaan API dari Groq buat AI-nya Aika.

- Sistem logging untuk para admin! Tersedia di channel khusus.

- Command baru lainnya untuk utilitas: `about`, `stats`, `invite`, `source-code`, `snipe`, dan `uptime`.


## v1.1.0 - 23 Agst 2026
### Penambahan:
- Fitur baru: Aika AI! Ditenagai oleh [Groq Qwen 3.6-27B](https://qwen.ai/blog?id=qwen3.6-27b), Aika kini bisa berinteraksi dengan kalian para member server layaknya chatbot pada umumnya! Dia pun ngeresponnya pake persona-nya yang dingin. Penambahan ini bertujuan agar maskot server terasa hadir di tengah-tengah kita.

  - Aika bisa kalian ajak berinteraksi di channel khususnya atau bisa juga di-mention (kalau di luar channel-nya).

  - Di dalam channel-nya, kalau ingin mengirim pesan tanpa direspons Aika (kayak comment gitu), sertakan `,,` di awal pesan kalian.

  - Di samping fiturnya, tersedia juga command-command utilitas untuk chatbot-nya antara lain `memory-status` untuk ngecek kapasitas chat / ingatan Aika sama kalian, dan `reset_chat` buat ngehapus semua ingatan Aika tentangmu (ibarat kayak buat ulang chat baru).


## v1.0.0 - 20 Agst 2026
Pada versi ini, Aika pertama kali diumumkan di pengumuman server.

Di titik ini, fungsi bot Aika masih sangat sederhana, yaitu sekedar ngisi channel `#info-server` dan `#ambil-role`, lebih tepatnya nge-host info-info di dalamnya kayak rules, tentang server, dll. 

Fungsi lainnya juga yaitu untuk membawa sosok maskot server makin dekat dengan kita dengan hadir di tengah-tengah member list, sekaligus untuk menggantikan posisi owner di dua channel tadi (karena pesan asli di situ terhapus gara-gara akun owner kena suspend sama Discord).

Pada titik ini pula, bot Aika masih belum punya command apa pun yang secara publik bisa diakses oleh para member server. Command yang ada yaitu cuma untuk nge-trigger dan ngirim pesan di dua channel di atas, dan command-command ini cuma terkunci untuk admin.
