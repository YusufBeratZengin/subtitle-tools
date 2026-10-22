# subtitle-tools

SubRip (`.srt`), WebVTT (`.vtt`) ve Advanced SubStation Alpha (`.ass` / `.ssa`) altyazı dosyalarını dönüştürmek, düzenlemek, onarmak ve lint etmek için sıfır bağımlılıklı Python komut satırı aracı ve kütüphanesi.

[English README](README.md)

## Genel Bakış

İçerik üreticileri, video kurgucuları ve çevirmenler altyazı dosyalarını sıklıkla kaydırmak, ölçeklemek, birleştirmek, bölmek ve temizlemek zorunda kalmaktadır. Mevcut araçlar çoğunlukla yalnızca grafik arayüze (GUI) sahiptir, terk edilmiştir veya ağır harici C/FFmpeg bağımlılıklarına ihtiyaç duyar.

`subtitle-tools`, hiçbir çalışma zamanı bağımlılığı bulunmayan (yalnızca Python standart kütüphanesi kullanan), yüksek hassasiyetli bir CLI aracı (`subtool`) ve tip tanımlı Python kütüphanesi (`src/` yerleşimi, `py.typed`) sunar.

## Temel Özellikler

- **Sıfır çalışma zamanı bağımlılığı**: Yalnızca Python >= 3.10 standart kütüphanesi.
- **Çoklu format desteği**:
  - **SubRip (`.srt`)**: Yaygın sözdizimi hatalarına karşı toleranslı, dayanıklı zaman ve indeks ayrıştırma.
  - **WebVTT (`.vtt`)**: İpucu kimliklerini, ayarlarını, `NOTE`, `STYLE` ve `REGION` bloklarını korur.
  - **ASS / SSA (`.ass`, `.ssa`)**: `[Script Info]`, `[V4+ Styles]` ve `[Events]` bölümlerini işler; bilinmeyen bölümleri (`[Aegisub Project Garbage]`, fontlar, grafikler) olduğu gibi korur.
- **İşlemler**:
  - `convert`: SRT, WebVTT ve ASS formatları arasında dönüştürme.
  - `shift`: Zaman damgalarını pozitif/negatif değerlerle kaydırma (`1500ms`, `-2s`) veya hedef zamana hizalama.
  - `scale`: Kare hızı dönüştürme (ör. 23.976 <-> 25 fps PAL hızlandırması) veya özel çarpan uygulama.
  - `merge`: İki dildeki altyazıyı üst üste bindirilmiş çift dilli ipuçları halinde birleştirme.
  - `split`: Altyazı dosyalarını süre aralıklarına göre parçalara ayırma (ör. 20 dakikalık bölümler).
  - `join`: Birden çok altyazı dosyasını aralarına isteğe bağlı boşluk koyarak sıralı birleştirme.
  - `renumber`: İpuçlarını 1'den başlayarak sıralı yeniden numaralandırma.
  - `strip-tags`: HTML, WebVTT ve ASS biçimlendirme etiketlerini temizleme ve HTML varlıklarını çözme.
- **Kapsamlı Lint ve Otomatik Onarım**:
  - Zamanlama, okuma hızı (CPS), satır uzunluğu ve etiket dengesini yapılandırılabilir eşiklerle denetler.
  - Güvenli kurallar için otomatik onarım (`--fix`): küçük çakışmaları düzeltir, sıfır/negatif süreleri giderir, boş ipuçlarını siler ve açık kalan etiketleri kapatır.
- **Belgelenmiş Eski Kodlama Algılama**:
  - Otomatik algılama sırası: `utf-8-sig` -> `utf-8` -> `cp1252` -> `cp1254` -> `latin-1`.

## Kurulum

Pip kullanarak kurun:

```bash
pip install .
```

Geliştirme ve testler için:

```bash
pip install -e ".[dev]"
```

## CLI Kullanım Kılavuzu (`subtool`)

### Format dönüştürme
```bash
# Dosya uzantısına göre otomatik dönüştürme
subtool convert giris.srt cikis.vtt
subtool convert giris.vtt cikis.ass

# Formatı açıkça belirterek dönüştürme
subtool convert giris.txt cikis.vtt --from-format srt --to-format vtt
```

### Zaman kaydırma
```bash
# 1500 milisaniye ileri kaydırma
subtool shift giris.srt -o kaydirilmis.srt --by 1500ms

# 2 saniye geri kaydırma
subtool shift giris.srt -o kaydirilmis.srt --by -2s

# İlk ipucunu tam 00:01:00.000 zamanına hizalama
subtool shift giris.srt -o kaydirilmis.srt --to 00:01:00.000

# Dosyayı yerinde güncelleme
subtool shift giris.srt --in-place --by 500ms
```

### Kare hızı / zaman ölçekleme
```bash
# 23.976 fps'ten 25 fps'e dönüştürme (PAL hızlandırması)
subtool scale giris.srt -o olcekli.srt --from-fps 23.976 --to-fps 25

# 25 fps'ten 23.976 fps'e dönüştürme
subtool scale giris.srt -o olcekli.srt --from-fps 25 --to-fps 23.976

# Doğrudan zaman çarpanı uygulama
subtool scale giris.srt -o olcekli.srt --factor 1.05
```

### Çift dilli altyazı birleştirme
```bash
# İngilizce ve Türkçe altyazıları üst üste bindirilmiş çift dil olarak birleştirme
subtool merge ingilizce.srt turkce.srt -o cift_dil.srt

# Özel satır ayırıcı belirleme
subtool merge ingilizce.srt turkce.srt -o cift_dil.srt --separator " | "
```

### Süreye göre bölme
```bash
# 20 dakikalık parçalara bölme
subtool split giris.srt --duration 20m -o parca

# 1200 saniyelik parçalara bölme
subtool split giris.srt --duration 1200s
```

### Dosyaları birleştirme
```bash
# Dosyalar arasına 1 saniye boşluk koyarak sıralı birleştirme
subtool join parca1.srt parca2.srt parca3.srt -o tam.srt --gap 1000ms
```

### Yeniden numaralandırma
```bash
subtool renumber giris.srt -o numarali.srt --start 1
```

### Biçimlendirme etiketlerini temizleme
```bash
# <i>, <b>, <font> ve ASS stil geçersiz kılma etiketlerini kaldırma
subtool strip-tags giris.srt -o temiz.srt
```

### Lint ve otomatik onarım
```bash
# Dosyaları denetleme ve rapor üretme
subtool lint *.srt

# Makine tarafından okunabilir JSON çıktısı
subtool lint *.srt --format json

# Onarılabilir sorunları yerinde otomatik düzeltme
subtool lint *.srt --fix

# Lint eşik değerlerini özelleştirme
subtool lint *.srt --max-cps 18 --max-line-length 40 --max-lines 2 --min-duration 400
```

### Altyazı dosyası bilgilerini inceleme
```bash
subtool info *.srt *.vtt *.ass
```

## Lint Kuralları

| Kural ID | Seviye | Açıklama | `--fix` ile Onarılabilir |
| -------- | ------ | -------- | ------------------------ |
| `overlap` | Hata | İpucu, önceki ipucu bitmeden başlıyor. | Evet (çakışma <= 1500ms ise) |
| `negative-duration` | Hata | İpucu bitiş zamanı başlangıç zamanından önce. | Evet (yer değiştirilir veya düzeltilir) |
| `zero-duration` | Hata | İpucu süresi sıfır. | Evet (asgari süreye çekilir) |
| `too-short-duration` | Uyarı | İpucu süresi asgari değerden kısa (varsayılan: 500ms). | Hayır |
| `too-long-duration` | Uyarı | İpucu süresi azami değerden uzun (varsayılan: 7000ms). | Hayır |
| `cps-limit` | Uyarı | Saniyedeki karakter sayısı okuma sınırını aşıyor (varsayılan: 17 cps). | Hayır |
| `line-length` | Uyarı | Tek satırdaki karakter sayısı sınırı aşıyor (varsayılan: 42 karakter). | Hayır |
| `line-count` | Uyarı | İpucundaki satır sayısı sınırı aşıyor (varsayılan: 2 satır). | Hayır |
| `empty-cue` | Hata | İpucunda görünür metin yok (yalnızca boşluk veya etiket). | Evet (silinir) |
| `unbalanced-tags` | Hata | Kapatılmamış veya eşleşmeyen HTML/VTT/ASS etiketleri. | Evet (kapatılır veya temizlenir) |
| `encoding-issue` | Uyarı | UTF-8 BOM varlığı veya karışık CRLF/LF satır sonları. | Evet (normalize edilir) |

## Kodlama Algılama Sırası

Açık bir `--encoding` parametresi verilmediğinde, `subtitle-tools` aşağıdaki sırayı takip eder:

1. **`utf-8-sig`**: 3 baytlık UTF-8 BOM (`0xEF, 0xBB, 0xBF`) denetlenir.
2. **`utf-8`**: Katı UTF-8 çözme denenir.
3. **`cp1254` / `cp1252`**: UTF-8 dışındaki baytlarda Windows-1254 Türkçe karakterleri (`ş`, `ğ`, `ı`, `Ş`, `Ğ`, `İ`) bulunursa `cp1254` seçilir. Aksi halde Windows-1252 (Batı Avrupa ANSI) kullanılır.
4. **`cp1254`**: CP1252 tanımsız baytlar nedeniyle başarısız olursa Windows-1254 denenir.
5. **`latin-1`**: Tüm baytları (0x00 - 0xFF) hatasız eşleyen ISO-8859-1 son çare olarak kullanılır.

## Python Kütüphane API'si

```python
from subtitle_tools import parse, write, shift, merge, lint_document, LintConfig

# Altyazı dosyasını ayrıştırma
with open("giris.srt", "r", encoding="utf-8") as f:
    doc = parse(f.read(), fmt="srt")

# İpuçlarını 1.5 saniye ileri kaydırma
kaydirilmis = shift(doc, by_ms=1500)

# Belgeyi lint etme
config = LintConfig(max_cps=17.0, max_line_length=42)
sorunlar = lint_document(kaydirilmis, config=config)

for sorun in sorunlar:
    print(f"[{sorun.severity.upper()}] {sorun.rule_id}: {sorun.message}")

# WebVTT formatında serileştirme
vtt_metin = write(kaydirilmis, fmt="vtt")
```

## Testleri Çalıştırma

Testler hiçbir harici paket gerektirmeden standart `unittest` ile çalıştırılabilir:

```bash
python -m unittest discover -s tests
```

Veya `pytest` ile:

```bash
pytest
```

## Katkıda Bulunma

Geliştirme yönergeleri ve iş akışı için lütfen [CONTRIBUTING.md](CONTRIBUTING.md) dosyasını inceleyin.

## Lisans

Bu proje MIT Lisansı altında lisanslanmıştır. Ayrıntılar için [LICENSE](LICENSE) dosyasına bakın.

Copyright (c) 2026 Yusuf Berat Zengin.
