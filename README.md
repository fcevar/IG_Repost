# Instagram video indirici

## Telefonda kullanım (Render ile, ücretsiz katman yeterli)
1. Bu klasörü bir GitHub deposuna yükle.
2. render.com → New → Web Service → depoyu seç → "Docker" olarak dağıt (ffmpeg dahil gelir).
3. Environment değişkenleri:
   - `APP_PASSWORD` = kendi belirlediğin şifre (başkaları kullanmasın)
   - `COOKIES_FILE` = `/etc/secrets/cookies.txt` (gerekirse, aşağıya bak)
4. Çıkan adresi telefonda aç → Safari'de "Paylaş → Ana Ekrana Ekle".

## Instagram "giriş gerekli" derse
Sunucu IP'lerini Instagram sık sık engelliyor. Çözüm: tarayıcıda Instagram'a giriş yap,
"Get cookies.txt LOCALLY" eklentisiyle cookies.txt al, Render'da "Secret Files" olarak
`cookies.txt` adıyla yükle. Ana hesabın yerine ayrı bir hesap kullanman daha güvenli.

## Güncelleme
Çalışmayı bırakırsa yt-dlp'yi güncelle: Render'da "Manual Deploy → Clear build cache & deploy".

## Bilgisayarda deneme
pip install -r requirements.txt && python app.py  →  http://localhost:8000
