#!/usr/bin/env python3
"""
M3U Playlist Güncelleyici v3.2
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
    - Redirect (301, 302, 303, 307, 308) varsa final URL'yi alır
    - Redirect yoksa body'yi okuyup içindeki ilk HTTP linkini döndürür
    """
    try:
        # SSL sertifika hatalarını görmezden gel (bazı worker'larda sorun olabiliyor)
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
        # Önce redirect'siz bir istek yapalım
        class NoRedirectHandler(ur.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                # Redirect'i engelle, direkt olarak newurl'yi döndürelim
                return None
        
        opener = ur.request.build_opener(NoRedirectHandler)
        
        with opener.open(req, timeout=REQUEST_TIMEOUT) as response:
            status = response.status
            final_url = response.geturl()  # Redirect yoksa bu kaynak_url ile aynı
            
            print(f"    [DEBUG] HTTP Status: {status}")
            print(f"    [DEBUG] Response URL: {final_url[:80]}...")
            
            # Redirect var mı kontrol et (status 3xx)
            if status in (301, 302, 303, 307, 308):
                redirect_url = response.headers.get('Location')
                if redirect_url:
                    print(f"    [→] Redirect (Location header): {redirect_url[:80]}...")
                    # Redirect URL'sine ikinci bir istek yapalım
                    return get_final_url(redirect_url)
            
            # Redirect yok, body'yi oku
            body = response.read().decode('utf-8', errors='ignore')
            
            # Body'de .m3u8 linki ara (önce bunu dene)
            m3u8_match = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', body)
            if m3u8_match:
                stream_url = m3u8_match.group(1)
                print(f"    [✓] Body'den .m3u8 linki bulundu ✓")
                print(f"    [DEBUG] Link: {stream_url[:80]}...")
                return stream_url
            
            # Body'de herhangi bir http/https linki ara
            http_match = re.search(r'(https?://[^\s"\'<>]+)', body)
            if http_match:
                stream_url = http_match.group(1)
                print(f"    [✓] Body'den HTTP linki bulundu ✓")
                print(f"    [DEBUG] Link: {stream_url[:80]}...")
                return stream_url
            
            # Body'nin kendisi link olabilir mi?
            body_stripped = body.strip()
            if body_stripped.startswith("http://") or body_stripped.startswith("https://"):
                if len(body_stripped) < 1000:  # Çok uzunsa body'dir, link değildir
                    print(f"    [✓] Body direkt link ✓")
                    return body_stripped
            
            print(f"    [✗] Hiçbir link bulunamadı! Body (ilk 200 karakter): {body[:200]}")
            return None
            
    except ur.error.HTTPError as e:
        print(f"    [✗] HTTP Hatası {e.code}: {e.reason}")
        # Bazı worker'lar 200 döner ama body'de link olur, bu durumda hata değil
        if e.code == 200:
            try:
                body = e.read().decode('utf-8', errors='ignore')
                http_match = re.search(r'(https?://[^\s"\'<>]+)', body)
                if http_match:
                    stream_url = http_match.group(1)
                    print(f"    [✓] HTTP 200 body'sinden link bulundu ✓")
                    return stream_url
            except:
                pass
        return None
    except ur.error.URLError as e:
        print(f"    [✗] URL Hatası: {e.reason}")
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
        
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
        
        with opener.open(req, timeout=REQUEST_TIMEOUT) as response:
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
    
    stream_linkleri = {}  # kanal_adi -> yeni_stream_linki
    hata_sayisi = 0
    
    for kanal_adi, bilgi in kanallar.items():
        kaynak_link = bilgi["link"]
        video_id = bilgi["video_id"]
        
        print(f"\n  [{kanal_adi}] (videoId: {video_id})")
        print(f"    Worker: {kaynak_link}")
        
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
    
    degisiklik_sayisi = 0
    yeni_satirlar = []
    su_an_kanal = None
    
    for i, satir in enumerate(satirlar):
        satir_stripped = satir.strip()
        
        # #KANAL:xxx satırını bul (Türkçe İ ve normal I, büyük-küçük harf duyarsız)
        kanal_match = re.match(r'#KANAL[İI]?:\s*(.+)', satir_stripped, re.IGNORECASE)
        if kanal_match:
            su_an_kanal = kanal_match.group(1).strip()
            print(f"  [*] Satır {i+1}: #KANAL:{su_an_kanal}")
            yeni_satirlar.append(satir)
            continue
        
        # URL satırı mı? (http ile başlıyor)
        if satir_stripped.startswith("http://") or satir_stripped.startswith("https://"):
            if su_an_kanal and su_an_kanal in stream_linkleri:
                yeni_link = stream_linkleri[su_an_kanal]
                print(f"  [✓] Satır {i+1}: '{su_an_kanal}' linki GÜNCELLENDİ")
                print(f"       Yeni link: {yeni_link[:80]}...")
                yeni_satirlar.append(yeni_link + "\n")
                degisiklik_sayisi += 1
                su_an_kanal = None
            else:
                # Kanala ait değil veya stream linki yok, olduğu gibi bırak
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
    print(f"  M3U PLAYLIST GÜNCELLEYİCİ v3.2")
    print(f"  Worker → Stream Link Çözücü")
    print(f"{'='*60}")
    
    kanallar = parse_secretlar()
    
    if not kanallar:
        print("\n[!] Secret'lardan veri alınamadı!")
        print("    Lütfen GitHub repo Settings → Secrets → Actions bölümünden")
        print("    BASE_URL ve KANALLAR secret'larını kontrol edin.")
        return False
    
    print(f"\n[+] {len(kanallar)} kanal bulundu:")
    for kanal, bilgi in kanallar.items():
        print(f"    • {kanal} → videoId: {bilgi['video_id']}")
    
    # M3U dosyasını kontrol et
    if os.path.exists(M3U_DOSYASI):
        with open(M3U_DOSYASI, 'r', encoding='utf-8') as f:
            icerik = f.read()
        kanal_etiketleri = re.findall(r'#KANAL[İI]?:\s*(.+)', icerik, re.IGNORECASE)
        print(f"\n[.] M3U dosyasındaki #KANAL etiketleri: {kanal_etiketleri}")
        
        # Eşleşme kontrolü
        for kanal in kanallar:
            if kanal in kanal_etiketleri:
                print(f"    ✓ '{kanal}' → M3U'da bulundu, eşleşecek")
            else:
                print(f"    ⚠️ '{kanal}' → M3U'da BULUNAMADI!")
                print(f"       Secret'taki kanal adı ile M3U'daki #KANAL etiketi birebir aynı olmalı!")
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
