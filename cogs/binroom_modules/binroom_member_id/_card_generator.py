import io

import qrcode
from PIL import Image, ImageDraw, ImageFont

BULAN_BHS_INDO = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}

def bikin_pojokan_melengkung(gmbr:Image.Image, radius:int=35) -> Image.Image:
    mask = Image.new("L", gmbr.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), gmbr.size], radius=radius, fill=255)
    
    output = gmbr.copy()
    output.putalpha(mask)
    return output

def bikin_kartu_member(
    gambar_polosan: str,
    ukuran_byte_pfp: bytes,
    user_id: int,
    display_name: str,
    tanggal_join: str,
    nomor_member: int,
    jenis_member: str,
) -> io.BytesIO:
    base = Image.open(gambar_polosan).convert("RGBA")
    
    diameter_pfp = 244  
    
    avatar = Image.open(io.BytesIO(ukuran_byte_pfp)).convert("RGBA")
    avatar = avatar.resize((diameter_pfp, diameter_pfp), Image.Resampling.LANCZOS)
    
    mask = Image.new("L", (diameter_pfp, diameter_pfp), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, diameter_pfp, diameter_pfp), fill=255)
    
    base.paste(avatar, (82, 258), mask)
    
    
    qr_url = f"https://discord.com/users/{user_id}"
    qr = qrcode.QRCode(box_size=3, border=0)
    qr.add_data(qr_url)
    qr.make(fit=True)
    
    qr_img = qr.make_image(
        #image_factory=StyledPilImage,
        #module_drawer=RoundedModuleDrawer(),
        fill_color=(222, 130, 207),
        back_color="transparent",
    ).convert("RGBA")
    qr_img = qr_img.resize((100, 100), Image.Resampling.LANCZOS)
    
    base.paste(qr_img, (838, 458), qr_img)
    
    
    font_dongle_bold = ImageFont.truetype("media/binroom_id/Dongle-Regular.ttf", 64)
    font_dongle_id = ImageFont.truetype("media/binroom_id/Dongle-Bold.ttf", 40)
    
    draw = ImageDraw.Draw(base)
    WARNA_ISIAN = "#FFFFFF"
    
    draw.text((928, 80), str(user_id), fill=WARNA_ISIAN, font=font_dongle_id, anchor="ra")
    draw.text((400, 245), display_name, fill=WARNA_ISIAN, font=font_dongle_bold)
    draw.text((400, 375), tanggal_join, fill=WARNA_ISIAN, font=font_dongle_bold)
    draw.text((400, 495), f"#{nomor_member}", fill=WARNA_ISIAN, font=font_dongle_bold)
    draw.text((604, 495), jenis_member, fill=WARNA_ISIAN, font=font_dongle_bold)
    
    kartu_akhir = bikin_pojokan_melengkung(base, radius=35)
    
    buffer = io.BytesIO()
    kartu_akhir.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer