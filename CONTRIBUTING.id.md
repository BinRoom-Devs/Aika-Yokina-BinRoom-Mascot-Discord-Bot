# Berkontribusi ke Bot Aika Yokina

Makasih udah tertarik buat berkontribusi pada Aika Yokina, bot maskot Discord BinRoom!

## Siapkan Environmental untuk Development

1. **Klon reponsitori**
   ```bash
   git clone https://github.com/AbinDai/Aika-Yokina-BinRoom-Mascot-Discord-Bot.git
   cd Aika-Yokina-BinRoom-Mascot-Discord-Bot
   ```

2. **Bikin virtual environment**
   ```bash
   python -m venv .venv
   # Di Windows:
   .venv\Scripts\activate
   # Di Unix/macOS:
   source .venv/bin/activate
   ```

3. **Install dependensi**
   ```bash
   pip install -r requirements.txt
   ```

4. **Konfigurasi environment variables**
   - Copy `.env.example` ke `.env`
   - Isi API keys dan nilai konfigurasi yang diperlukan
   ```bash
   cp .env.example .env
   # Edit .env dengan nilai asli kamu
   ```

## Panduan Pengembangan

### Gaya Kodingan
- Ikutin pedoman PEP 8 buat kode Python
- Pake nama variabel dan fungsi yang bermakna
- Tambahin docstring ke fungsi dan kelas
- Bikin fungsi terfokus dan modular

### Menambah Fitur Baru
1. Bikin branch baru buat fitur kamu
   ```bash
   git checkout -b feature/nama-fitur-kamu
   ```

2. Lakuin perubahan dan uji secara menyeluruh

3. Pastiin environment variables dipake buat data sensitif apa pun
   - Jangan pernah nge-hardcode API keys, tokens, atau secrets
   - Pake `os.getenv()` dengan default yang wajar

4. Uji perubahan kamu
   - Uji di development environment terlebih dahulu
   - Pastikan fitur yang ada masih berfungsi

### Menambah Cog Baru
- Tempatkan cog baru di direktori `cogs/`
- Ikuti struktur cog yang sudah ada
- Sertakan penanganan error yang tepat
- Tambahkan pemeriksaan izin yang sesuai

### Perubahan Database
- Modifikasi `database.py` untuk perubahan skema
- Sertakan skrip migrasi jika diperlukan
   - Uji operasi database secara menyeluruh

## Mengirim Perubahan

1. **Commit perubahan kamu**
   ```bash
   git add .
   git commit -m "feat: tambahkan deskripsi fitur kamu"
   ```

2. **Push ke fork kamu**
   ```bash
   git push origin feature/nama-fitur-kamu
   ```

3. **Buat Pull Request**
   - Jelasin perubahan kamu dengan jelas
   - Referensiin issue terkait kalau ada
   - Kasih screenshot kalo perlu

## Proses Review Kode

- Semua pengiriman memerlukan review
- Tanggapin umpan balik dari maintainer
- Pastikan tes lulus sebelum digabungkan

## Pertanyaan?

Jangan ragu buat nanya di issue buat pertanyaan atau diskusi tentang kontribusi.

---

**Catatan**: Ini adalah proyek hobi untuk komunitas BinRoom. Hormatilah dan ikuti Syarat dan Ketentuan Discord saat mengembangkan fitur.