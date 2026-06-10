#!/usr/bin/env python3
"""
M3U Playlist Güncelleyici v3.0
- BASE_URL ve KANAL=VIDEO_ID ayrı secret'lardan alınır
"""

import os
import re
import urllib.request
import urllib.error
import socket
import time

M3U_DOSYASI = "ytlistem.m3u"
REQUEST_TIMEOUT = 15


def get_stream_url(kaynak_url):
    try:
        req = urllib.request.Request(kaynak_url, method='GET', headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
        
        with opener.open(req, timeout=REQUEST_TIMEOUT) as response:
            final_url = response.geturl()
            
            if final_url != kaynak_url:
                print(f"    [→] Redirect: {final_url[:80]}...")
                return final_url
            
            body = response.read().decode('utf-8', errors='ignore')
            
            m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', body)
            if m3u8_match:
                print(f"    [✓] Body'den m3u8 linki bulundu")
                return m3u8_match.group(1)
            
            body = body.strip()
            if body.startswith("http://") or body.startswith("https://"):
                if len(body) < 500:
                    return body
            
            return final_url
            
    except Exception as e:
        print(f"    [✗] Hata: {e}")
        return None


def parse_secretlar():
    base_url = os.environ.get("BASE_URL", "").strip()
    kanallar_raw = os.environ.get("KANALLAR", "").strip()
    
    kanallar = {}
    
    print(f"\n[*] BASE_URL: {base_url}")
    
    if not base_url:
        print("[!] BASE_URL secret'ı boş!")
        return kanallar
    
    if not kanallar_raw:
        print("[!] KANALLAR secret'ı boş!")
        return kanallar
    
    for line in kanallar_raw.split("\n"):
        line = line.strip()
        if not line or "=" not in line:
            continue
        
        kanal_adi, video_id = line.split("=", 1)
        kanal_adi = kanal_adi.strip()
        video_id = video_id.strip()
        
        if kanal_adi and video_id:
            tam_link = base_url + video_id
            kanallar[kanal_adi] = tam_link
            print(f"[+] '{kanal_adi}' → {tam_link}")
        else:
            print(f"[!] Geçersiz satır: {line}")
    
    return kanallar


def parse_m3u_dosyasi(m3u_icerik):
    satirlar = []
    son_kanal = None
    
    for i, satir in enumerate(m3u_icerik.split("\n")):
        entry = {
            "satir_no": i,
            "icerik": satir,
            "tip": "normal",
            "deger": None,
            "kanal": son_kanal
        }
        
        satir_stripped = satir.strip()
        
        if not satir_stripped:
            entry["tip"] = "bosluk"
        elif satir_stripped.upper().startswith("#EXTM3U"):
            entry["tip"] = "header"
        elif satir_stripped.upper().startswith("#KATEGORİ:") or satir_stripped.upper().startswith("#KATEGORI:"):
            entry["tip"] = "kategori"
            entry["deger"] = satir_stripped.split(":", 1)[1].strip()
        elif satir_stripped.upper().startswith("#KANAL:"):
            entry["tip"] = "kanal"
            entry["deger"] = satir_stripped.split(":", 1)[1].strip()
            son_kanal = entry["deger"]
        else:
            entry["kanal"] = son_kanal
        
        satirlar.append(entry)
    
    return satirlar


def m3u_guncelle(kanallar):
    if not os.path.exists(M3U_DOSYASI):
        print(f"[-] {M3U_DOSYASI} bulunamadı!")
        return False
    
    with open(M3U_DOSYASI, 'r', encoding='utf-8') as f:
        orijinal_icerik = f.read()
    
    satirlar = parse_m3u_dosyasi(orijinal_icerik)
    yeni_satirlar = []
    degisiklik_sayisi = 0
    hata_sayisi = 0
    
    print(f"\n{'='*60}")
    print(f"  ADIM 1: Stream linkleri çözülüyor...")
    print(f"{'='*60}")
    
    stream_linkleri = {}
    
    for kanal_adi, kaynak_link in kanallar.items():
        print(f"\n  [{kanal_adi}]")
        print(f"    Kaynak: {kaynak_link}")
        
        yeni_link = get_stream_url(kaynak_link)
        
        if yeni_link:
            stream_linkleri[kanal_adi] = yeni_link
            print(f"    [✓] Stream linki alındı ✓")
        else:
            print(f"    [✗] Stream linki ALINAMADI!")
            hata_sayisi += 1
    
    print(f"\n{'='*60}")
    print(f"  ADIM 2: M3U güncelleniyor...")
    print(f"{'='*60}")
    
    for entry in satirlar:
        if entry["tip"] == "url" and entry["kanal"] in stream_linkleri:
            yeni_link = stream_linkleri[entry["kanal"]]
            yeni_satirlar.append(yeni_link)
            print(f"  [✓] Satır {entry['satir_no']}: '{entry['kanal']}' güncellendi")
            degisiklik_sayisi += 1
        else:
            yeni_satirlar.append(entry["icerik"])
    
    yeni_icerik = "\n".join(yeni_satirlar)
    
    print(f"\n{'='*60}")
    print(f"  RAPOR")
    print(f"{'='*60}")
    print(f"  Toplam kanal      : {len(kanallar)}")
    print(f"  Başarılı          : {len(stream_linkleri)}")
    print(f"  Hatalı            : {hata_sayisi}")
    print(f"  M3U'da güncellenen: {degisiklik_sayisi}")
    
    if degisiklik_sayisi > 0:
        with open(M3U_DOSYASI, 'w', encoding='utf-8') as f:
            f.write(yeni_icerik)
        print(f"\n  ✅ M3U dosyası güncellendi!")
        return True
    else:
        print(f"\n  ℹ️  Hiçbir değişiklik yapılmadı.")
        return False


def main():
    print(f"\n{'='*60}")
    print(f"  M3U PLAYLIST GÜNCELLEYİCİ v3.0")
    print(f"  BASE_URL + KANALLAR (Ayrı Secret)")
    print(f"{'='*60}")
    
    kanallar = parse_secretlar()
    
    if not kanallar:
        print("\n[!] Secret'lardan veri alınamadı!")
        return False
    
    print(f"\n[+] {len(kanallar)} kanal bulundu:")
    for kanal in kanallar:
        print(f"    • {kanal}")
    
    success = m3u_guncelle(kanallar)
    return success


if __name__ == "__main__":
    baslangic = time.time()
    sonuc = main()
    gecen_sure = time.time() - baslangic
    print(f"\n[.] İşlem süresi: {gecen_sure:.1f} saniye")
    exit(0 if sonuc else 1)
