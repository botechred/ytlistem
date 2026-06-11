#!/usr/bin/env python3
"""
M3U Playlist Güncelleyici v3.4 (Gist Destekli)
- Gist'ten M3U'yu çeker
- Worker ile stream linklerini günceller
- Yerel dosyayı günceller → Workflow Gist'e yükler
"""

import os
import re
import urllib.request
import urllib.error
import socket
import time
import ssl

M3U_DOSYASI = "ytlistem.m3u"
GIST_RAW_URL = "https://gist.githubusercontent.com/botechred/69356131d65dc88e267300e867641048/raw"
REQUEST_TIMEOUT = 30


def download_from_gist():
    """Gist'ten en güncel M3U'yu indirir."""
    print(f"[*] Gist'ten M3U indiriliyor: {GIST_RAW_URL}")
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(
            GIST_RAW_URL,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=ctx) as response:
            content = response.read().decode('utf-8')
            
        with open(M3U_DOSYASI, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[✓] Gist'ten {M3U_DOSYASI} indirildi ({len(content)} karakter)")
        return True
    except Exception as e:
        print(f"[✗] Gist'ten indirme hatası: {e}")
        return False


def get_stream_url(...):  # (mevcut fonksiyon aynı kalacak)


# ... (get_final_url, parse_secretlar, m3u_guncelle fonksiyonları aynı kalacak)

def main():
    print(f"\n{'='*60}")
    print(f"  M3U PLAYLIST GÜNCELLEYİCİ v3.4 (Gist Odaklı)")
    print(f"{'='*60}")
    
    # Gist'ten dosya yoksa veya boşsa indir
    if not os.path.exists(M3U_DOSYASI) or os.path.getsize(M3U_DOSYASI) < 100:
        if not download_from_gist():
            print("[!] Gist'ten dosya indirilemedi!")
            return False
    
    kanallar = parse_secretlar()
    if not kanallar:
        print("\n[!] Secret'lardan veri alınamadı!")
        return False
    
    # ... (mevcut main mantığı devam eder)
    success = m3u_guncelle(kanallar)
    return success


if __name__ == "__main__":
    baslangic = time.time()
    sonuc = main()
    gecen_sure = time.time() - baslangic
    print(f"\n[.] İşlem süresi: {gecen_sure:.1f} saniye")
    exit(0 if sonuc else 1)
