#!/usr/bin/env python3
"""
M3U Playlist Güncelleyici v3.3
- Worker URL'sine GET request atar
- Redirect veya body'den gerçek stream linkini alır
- M3U'da #KANAL:xxx etiketine göre günceller
"""

import os
import re
import urllib.request
import urllib.error
import socket
import time
import ssl

M3U_DOSYASI = "ytlistem.m3u"
REQUEST_TIMEOUT = 30


def get_stream_url(kaynak_url):
    """
    Worker URL'sine istek atar.
    - Redirect (301, 302, 303, 307, 308) varsa Location header'ından URL'yi alır
    - Redirect yoksa body'yi okuyup içindeki ilk HTTP linkini döndürür
    """
    try:
        # SSL sertifika hatalarını görmezden gel
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(
            kaynak_url,
            method='GET',
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*',
                'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            }
        )
        
        # Redirect'leri TAKİP ETME, kendimiz yönetelim
        try:
            response = urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=ctx)
        except urllib.error.HTTPError as e:
            # 3xx redirect'lerde HTTPError fırlatılabilir, Location header'ını kontrol et
            if e.code in (301, 302, 303, 307, 308):
                redirect_url = e.headers.get('Location')
                if redirect_url:
                    print(f"    [→] Redirect (HTTP {e.code}): {redirect_url[:80]}...")
                    # Redirect URL'sine git
                    return get_final_url(redirect_url)
            print(f"    [✗] HTTP Hatası {e.code}: {e.reason}")
            return None
        except urllib.error.URLError as e:
            print(f"    [✗] URL Hatası: {e.reason}")
            return None
        
        # Başarılı yanıt
        status = response.status
        final_url = response.geturl()
        
        print(f"    [DEBUG] HTTP Status: {status}")
        
        # Redirect mi kontrol et
        if status in (301, 302, 303, 307, 308):
            redirect_url = response.headers.get('Location')
            if redirect_url:
                print(f"    [→] Redirect (Location): {redirect_url[:80]}...")
                return get_final_url(redirect_url)
        
        # Body'yi oku
        body = response.read().decode('utf-8', errors='ignore')
        
        # Body'de .m3u8 linki ara
        m3u8_match = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', body)
        if m3u8_match:
            stream_url = m3u8_match.group(1)
            print(f"    [✓] Body'den .m3u8 linki bulundu")
            return stream_url
        
        # Body'de herhangi bir http/https linki ara
        http_match = re.search(r'(https?://[^\s"\'<>]+)', body)
        if http_match:
            stream_url = http_match.group(1)
            print(f"    [✓] Body'den HTTP linki bulundu")
            return stream_url
        
        # Body'nin kendisi link olabilir mi?
        body_stripped = body.strip()
        if body_stripped.startswith("http://") or body_stripped.startswith("https://"):
            if len(body_stripped) < 1000:
                print(f"    [✓] Body direkt link")
                return body_stripped
        
        print(f"    [✗] Hiçbir link bulunamadı! Body (ilk 200 karakter):")
        print(f"    [DEBUG] {body[:200]}")
        return None
            
    except socket.timeout:
        print(f"    [✗] Zaman aşımı (>{REQUEST_TIMEOUT}s)")
        return None
    except Exception as e:
        print(f"    [✗] Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_final_url(url):
    """
    Redirect sonrası final URL'yi almak için ikinci istek.
    """
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(
            url,
            method='GET',
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
        )
        
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=ctx) as response:
            final_url = response.geturl()
            print(f"    [→] Final URL: {final_url[:80]}...")
            
            # Eğer final URL .m3u8 ile bitiyorsa direkt döndür
            if '.m3u8' in final_url:
                return final_url
            
            # Body'yi de kontrol et
            body = response.read().decode('utf-8', errors='ignore')
            m3u8_match = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', body)
            if m3u8_match:
                return m3u8_match.group(1)
            
            http_match = re.search(r'(https?://[^\s"\'<>]+)', body)
            if http_match:
                return http_match.group(1)
            
            return final_url
            
    except Exception as e:
        print(f"    [✗] Final URL hatası: {e}")
        return None


def parse_secretlar():
    """BASE_URL ve KANALLAR secret'larını birleştirir."""
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
            print(f"[!] Geçersiz satır (atlanıyor): '{line}'")
            continue
        
        kanal_adi, video_id = line.split("=", 1)
        kanal_adi = kanal_adi.strip()
        video_id = video_id.strip()
        
        if kanal_adi and video_id:
            tam_link = base_url + video_id
            kanallar[kanal_adi] = {"link": tam_link, "video_id": video_id}
            print(f"[+] '{kanal_adi}' → videoId={video_id}")
        else:
            print(f"[!] Boş kanal adı veya video ID: '{line}'")
    
    return kanallar


def m3u_guncelle(kanallar):
    """M3U dosyasını kanal adına göre günceller."""
    
    if not os.path.exists(M3U_DOSYASI):
        print(f"[-] {M3U_DOSYASI} dosyası bulunamadı!")
        return False
    
    with open(M3U_DOSYASI, 'r', encoding='utf-8') as f:
        satirlar = f.readlines()
    
    print(f"\n{'='*60}")
    print(f"  ADIM 1: Worker URL'lerine istek atılıyor...")
    print(f"{'='*60}")
    
    stream_linkleri = {}
    hata_sayisi = 0
    
    for kanal_adi, bilgi in kanallar.items():
        kaynak_link = bilgi["link"]
        video_id = bilgi["video_id"]
        
        print(f"\n  [{kanal_adi}] (videoId: {video_id})")
        print(f"    Worker: {kaynak_link}")
        
        yeni_link = get_stream_url(kaynak_link)
        
        if yeni_link:
            stream_linkleri[kanal_adi] = yeni_link
            print(f"    [✓] Stream linki alındı")
        else:
            print(f"    [✗] Stream linki ALINAMADI!")
            hata_sayisi += 1
    
    print(f"\n{'='*60}")
    print(f"  ADIM 2: M3U güncelleniyor...")
    print(f"{'='*60}")
    
    degisiklik_sayisi = 0
    yeni_satirlar = []
    su_an_kanal = None
    
    for i, satir in enumerate(satirlar):
        satir_stripped = satir.strip()
        
        # #KANAL:xxx satırını bul
        kanal_match = re.match(r'#KANAL[İI]?:\s*(.+)', satir_stripped, re.IGNORECASE)
        if kanal_match:
            su_an_kanal = kanal_match.group(1).strip()
            print(f"  [*] Satır {i+1}: #KANAL:{su_an_kanal}")
            yeni_satirlar.append(satir)
            continue
        
        # URL satırı mı?
        if satir_stripped.startswith("http://") or satir_stripped.startswith("https://"):
            if su_an_kanal and su_an_kanal in stream_linkleri:
                yeni_link = stream_linkleri[su_an_kanal]
                print(f"  [✓] Satır {i+1}: '{su_an_kanal}' linki GÜNCELLENDİ")
                yeni_satirlar.append(yeni_link + "\n")
                degisiklik_sayisi += 1
                su_an_kanal = None
            else:
                yeni_satirlar.append(satir)
        else:
            yeni_satirlar.append(satir)
    
    print(f"\n{'='*60}")
    print(f"  RAPOR")
    print(f"{'='*60}")
    print(f"  Toplam kanal        : {len(kanallar)}")
    print(f"  Başarılı            : {len(stream_linkleri)}")
    print(f"  Hatalı              : {hata_sayisi}")
    print(f"  M3U'da güncellenen  : {degisiklik_sayisi}")
    
    if degisiklik_sayisi > 0:
        with open(M3U_DOSYASI, 'w', encoding='utf-8') as f:
            f.writelines(yeni_satirlar)
        print(f"\n  ✅ M3U dosyası güncellendi ve kaydedildi!")
        return True
    else:
        print(f"\n  ⚠️  Hiçbir değişiklik yapılmadı!")
        return False


def main():
    print(f"\n{'='*60}")
    print(f"  M3U PLAYLIST GÜNCELLEYİCİ v3.3")
    print(f"  Worker → Stream Link Çözücü")
    print(f"{'='*60}")
    
    kanallar = parse_secretlar()
    
    if not kanallar:
        print("\n[!] Secret'lardan veri alınamadı!")
        return False
    
    print(f"\n[+] {len(kanallar)} kanal bulundu:")
    for kanal, bilgi in kanallar.items():
        print(f"    • {kanal} → videoId: {bilgi['video_id']}")
    
    if os.path.exists(M3U_DOSYASI):
        with open(M3U_DOSYASI, 'r', encoding='utf-8') as f:
            icerik = f.read()
        kanal_etiketleri = re.findall(r'#KANAL[İI]?:\s*(.+)', icerik, re.IGNORECASE)
        print(f"\n[.] M3U dosyasındaki #KANAL etiketleri: {kanal_etiketleri}")
        
        for kanal in kanallar:
            if kanal in kanal_etiketleri:
                print(f"    ✓ '{kanal}' → M3U'da bulundu")
            else:
                print(f"    ⚠️ '{kanal}' → M3U'da BULUNAMADI!")
    else:
        print(f"\n[-] {M3U_DOSYASI} bulunamadı!")
        return False
    
    success = m3u_guncelle(kanallar)
    return success


if __name__ == "__main__":
    baslangic = time.time()
    sonuc = main()
    gecen_sure = time.time() - baslangic
    print(f"\n[.] İşlem süresi: {gecen_sure:.1f} saniye")
    exit(0 if sonuc else 1)
