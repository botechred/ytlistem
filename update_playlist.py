#!/usr/bin/env python3
"""
M3U Playlist Güncelleyici v3.6 - Gist Odaklı + Worker Güncelleme
"""

import os
import re
import urllib.request
import urllib.error
import time
import ssl

M3U_DOSYASI = "ytlistem.m3u"
# En stabil raw URL (dosya adıyla)
GIST_RAW_URL = "https://gist.githubusercontent.com/botechred/69356131d65dc88e267300e867641048/raw/ytlistem.m3u"
REQUEST_TIMEOUT = 25


def download_from_gist():
    print(f"[*] Gist'ten M3U indiriliyor: {GIST_RAW_URL}")
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(
            GIST_RAW_URL,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=ctx) as response:
            content = response.read().decode('utf-8')

        if len(content.strip()) < 300:
            raise Exception("Gist içeriği çok kısa")

        with open(M3U_DOSYASI, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[✓] Gist'ten indirildi ({len(content)} karakter)")
        return True
    except Exception as e:
        print(f"[✗] Gist indirme hatası: {e}")
        return False


def get_stream_url(kaynak_url):
    """Worker'dan gerçek stream linkini çeker."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(
            kaynak_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*'
            }
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=ctx) as response:
            body = response.read().decode('utf-8', errors='ignore')
            final_url = response.geturl()

        # m3u8 link ara
        m3u8_match = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', body)
        if m3u8_match:
            return m3u8_match.group(1)

        # Herhangi bir http link
        http_match = re.search(r'(https?://[^\s"\'<>]+)', body)
        if http_match:
            return http_match.group(1)

        if body.strip().startswith('http'):
            return body.strip()

        return final_url
    except Exception as e:
        print(f"    [✗] {kaynak_url} için hata: {e}")
        return None


def parse_secretlar():
    base_url = os.environ.get("BASE_URL", "").strip()
    kanallar_raw = os.environ.get("KANALLAR", "").strip()
    kanallar = {}

    if not base_url or not kanallar_raw:
        print("[!] BASE_URL veya KANALLAR secret/variable eksik!")
        return kanallar

    for line in kanallar_raw.splitlines():
        line = line.strip()
        if "=" not in line:
            continue
        try:
            kanal_adi, video_id = [x.strip() for x in line.split("=", 1)]
            if kanal_adi and video_id:
                kanallar[kanal_adi] = base_url + video_id
        except:
            continue
    return kanallar


def m3u_guncelle(kanallar):
    if not os.path.exists(M3U_DOSYASI):
        print(f"[-] {M3U_DOSYASI} bulunamadı!")
        return False

    with open(M3U_DOSYASI, 'r', encoding='utf-8') as f:
        satirlar = f.readlines()

    guncellendi = False
    i = 0
    while i < len(satirlar):
        satir = satirlar[i].strip()
        if satir.startswith("#KANAL:"):
            kanal_adi = satir[7:].strip()
            if kanal_adi in kanallar:
                # #EXTINF satırını atla
                if i + 1 < len(satirlar) and satirlar[i + 1].startswith("#EXTINF"):
                    i += 2
                else:
                    i += 1

                if i < len(satirlar):
                    print(f"[→] {kanal_adi} için yeni link alınıyor...")
                    yeni_link = get_stream_url(kanallar[kanal_adi])
                    if yeni_link:
                        satirlar[i] = yeni_link + "\n"
                        print(f"[✓] {kanal_adi} güncellendi")
                        guncellendi = True
                    else:
                        print(f"[!] {kanal_adi} link alınamadı")
        i += 1

    if guncellendi:
        with open(M3U_DOSYASI, 'w', encoding='utf-8') as f:
            f.writelines(satirlar)
        print("[✓] Playlist başarıyla güncellendi ve kaydedildi")
        return True
    else:
        print("[.] Hiçbir kanal güncellenemedi")
        return True


def main():
    print(f"\n{'='*75}")
    print("     M3U PLAYLIST GÜNCELLEYİCİ v3.6 (Gist + Worker)")
    print(f"{'='*75}")

    if not os.path.exists(M3U_DOSYASI) or os.path.getsize(M3U_DOSYASI) < 300:
        if not download_from_gist():
            print("[!] Gist'ten dosya çekilemedi!")
            return False

    kanallar = parse_secretlar()
    if not kanallar:
        print("[!] Kanal listesi alınamadı!")
        return False

    print(f"[*] {len(kanallar)} kanal bulundu.")
    return m3u_guncelle(kanallar)


if __name__ == "__main__":
    baslangic = time.time()
    sonuc = main()
    print(f"\n[.] Toplam süre: {time.time() - baslangic:.1f} saniye")
    exit(0 if sonuc else 1)
