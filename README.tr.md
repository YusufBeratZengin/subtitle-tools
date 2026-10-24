# subtitle-tools

[![CI](https://github.com/YusufBeratZengin/subtitle-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/YusufBeratZengin/subtitle-tools/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/subtitle-tools.svg?color=blue)](https://pypi.org/project/subtitle-tools/)
[![Python 3.10+](https://img.shields.io/badge/python-%3E%3D3.10-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[English](README.md) | [Turkce](README.tr.md)

SubRip (`.srt`), WebVTT (`.vtt`) ve Advanced SubStation Alpha (`.ass` / `.ssa`) altyazı dosyalarını dönüştürmek, düzenlemek, onarmak ve denetlemek (lint) için sıfır bağımlılıklı Python komut satırı aracı ve kütüphanesi.

![subtitle-tools demo](docs/demo.svg)

## Neden subtitle-tools?

- **Sıfır çalışma zamanı bağımlılığı**: Yalnızca Python standart kütüphanesini (>= 3.10) kullanır. Harici C kütüphaneleri, FFmpeg ikilileri veya derleme adımları gerektirmez.
- **Çoklu format desteği ve tam doğruluk**: SubRip (`.srt`), WebVTT (`.vtt`) ve ASS/SSA (`.ass`) arasında iki yönlü kayıpsız dönüştürme yapar; stilleri, ipucu ayarlarını, notları ve bilinmeyen bölümleri olduğu gibi korur.
- **Dahili denetleme (lint) ve otomatik onarım**: Zamanlama çakışmalarını, sıfır/negatif süreleri, satır sınırlarını ve okuma hızı (CPS) aşımlarını tespit eder; güvenli sorunları `--fix` bayrağı ile tek adımda yerinde onarır.

## Hızlı Başlangıç

İlk PyPI sürümü yayımlanana kadar depoyu klonlayıp kök dizininde `pip install -e .` çalıştırarak kurun.

İlk PyPI sürümünden sonra pip ile kurun:

```bash
# Paketi kurun
pip install subtitle-tools

# Altyazı dosyası meta verilerini ve kodlamasını inceleyin
subtool info film.srt

# Zamanlama ve etiket hatalarını denetleyip otomatik onarın
subtool lint film.srt --fix

# SRT formatını WebVTT'ye dönüştürün
subtool convert film.srt film.vtt
```

Yerel geliştirme ve test çalıştırma:

```bash
git clone https://github.com/YusufBeratZengin/subtitle-tools.git
cd subtitle-tools
pip install -e ".[dev]"
pytest
```

## Kullanım Örnekleri

Örnekler: küçük SRT dosyası ve dönüştürülmüş WebVTT karşılığı için [examples/](examples/) dizinine bakın.
Windows üzerinde gerçek çıktı (dönüştürme başarıyla tamamlandığında çıktı vermez):

```console
$ subtool lint examples/sample.srt

examples\sample.srt:
  No issues found.
$ subtool convert examples/sample.srt examples/sample.vtt
```

### CLI Kullanım Kılavuzu (`subtool`)

#### Format dönüştürme
```bash
# Dosya uzantısına göre otomatik dönüştürme
subtool convert giris.srt cikis.vtt
subtool convert giris.vtt cikis.ass

# Formatı açıkça belirterek dönüştürme
subtool convert giris.txt cikis.vtt --from-format srt --to-format vtt
```

#### Zaman kaydırma
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

#### Kare hızı / zaman ölçekleme
```bash
# 23.976 fps'ten 25 fps'e dönüştürme (PAL hızlandırması)
subtool scale giris.srt -o olcekli.srt --from-fps 23.976 --to-fps 25

# 25 fps'ten 23.976 fps'e dönüştürme
subtool scale giris.srt -o olcekli.srt --from-fps 25 --to-fps 23.976

# Doğrudan zaman çarpanı uygulama
subtool scale giris.srt -o olcekli.srt --factor 1.05
```

#### Çift dilli altyazı birleştirme
```bash
# İngilizce ve Türkçe altyazıları üst üste bindirilmiş çift dil olarak birleştirme
subtool merge ingilizce.srt turkce.srt -o cift_dil.srt

# Özel satır ayırıcı belirleme
subtool merge ingilizce.srt turkce.srt -o cift_dil.srt --separator " | "
```

#### Süreye göre bölme
```bash
# 20 dakikalık parçalara bölme
subtool split giris.srt --duration 20m -o parca

# 1200 saniyelik parçalara bölme
subtool split giris.srt --duration 1200s
```

#### Dosyaları birleştirme
```bash
# Dosyalar arasına 1 saniye boşluk koyarak sıralı birleştirme
subtool join parca1.srt parca2.srt parca3.srt -o tam.srt --gap 1000ms
```

#### Yeniden numaralandırma
```bash
subtool renumber giris.srt -o numarali.srt --start 1
```

#### Biçimlendirme etiketlerini temizleme
```bash
# <i>, <b>, <font> ve ASS stil geçersiz kılma etiketlerini kaldırma
subtool strip-tags giris.srt -o temiz.srt
```

#### Lint ve otomatik onarım
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

#### Altyazı dosyası bilgilerini inceleme
```bash
subtool info *.srt *.vtt *.ass
```

### Python Kütüphane API'si

`subtitle-tools`, Python projelerinde doğrudan içe aktarılarak kullanılabilir:

```python
from subtitle_tools import parse, write, shift, merge, lint_document, LintConfig

# Altyazı dosyasını ayrıştırma
with open("giris.srt", "r", encoding="utf-8") as f:
    doc = parse(f.read(), fmt="srt")

# İpuçlarını 1.5 saniye ileri kaydırma
kaydirilmis = shift(doc, by_ms=1500)

# Özel eşik değerleriyle belgeyi denetleme
config = LintConfig(max_cps=17.0, max_line_length=42)
sorunlar = lint_document(kaydirilmis, config=config)

for sorun in sorunlar:
    print(f"[{sorun.severity.upper()}] {sorun.rule_id}: {sorun.message}")

# WebVTT formatında serileştirme
vtt_metin = write(kaydirilmis, fmt="vtt")
```

## Yapılandırma

### Lint Parametreleri ve Eşik Değerleri

`subtool lint` komutu çalıştırılırken aşağıdaki parametrelerle denetim eşikleri ayarlanabilir:

| CLI Parametresi | Varsayılan | Açıklama |
| --------------- | ---------- | -------- |
| `--max-cps` | `17.0` | Saniyedeki azami karakter okuma hızı eşiği (CPS). |
| `--max-line-length` | `42` | Tek bir satırdaki azami karakter sayısı. |
| `--max-lines` | `2` | Bir ipucunda izin verilen azami satır sayısı. |
| `--min-duration` | `500` | Asgari ipucu süresi (milisaniye cinsinden). |
| `--max-duration` | `7000` | Azami ipucu süresi (milisaniye cinsinden). |
| `--fix` | `False` | Güvenli hataları dosya üzerinde otomatik olarak düzeltir. |
| `--strict` | `False` | Uyarılarda da hata çıkış kodu (exit code 1) döndürür. |
| `--format` | `text` | Çıktı formatı (terminal için `text`, otomasyon/CI için `json`). |

### Lint Kuralları

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

### Kodlama Algılama Sırası

Açık bir `--encoding` parametresi verilmediğinde, `subtitle-tools` aşağıdaki sırayı takip eder:

1. **`utf-8-sig`**: 3 baytlık UTF-8 BOM (`0xEF, 0xBB, 0xBF`) denetlenir.
2. **`utf-8`**: Katı UTF-8 çözme denenir.
3. **`cp1254` / `cp1252`**: UTF-8 dışındaki baytlarda Windows-1254 Türkçe karakterleri (`ş`, `ğ`, `ı`, `Ş`, `Ğ`, `İ`) bulunursa `cp1254` seçilir. Aksi halde Windows-1252 (Batı Avrupa ANSI) kullanılır.
4. **`cp1254`**: CP1252 tanımsız baytlar nedeniyle başarısız olursa Windows-1254 denenir.
5. **`latin-1`**: Tüm baytları (0x00 - 0xFF) hatasız eşleyen ISO-8859-1 son çare olarak kullanılır.

## SSS ve Kısıtlamalar

**S: Hangi altyazı formatları desteklenmektedir?**  
C: `subtitle-tools`, metin tabanlı SubRip (`.srt`), WebVTT (`.vtt`) ve SubStation Alpha / Advanced SubStation Alpha (`.ass`, `.ssa`) formatlarını destekler.

**S: Bitmap veya resim tabanlı altyazılar (PGS / SUP, VobSub `.sub`/`.idx`) destekleniyor mu?**  
C: Hayır. `subtitle-tools` yalnızca metin tabanlı altyazılara odaklanmıştır. Blu-ray PGS veya DVD VobSub gibi raster görüntüler için öncelikle Subtitle Edit veya Tesseract gibi OCR araçlarıyla metne dönüştürme yapılmalıdır.

**S: Otomatik onarım motoru neleri güvenli olarak değiştirir?**  
C: `--fix`, yalnızca belirsizlik içermeyen durumları onarır: tamamen boş ipuçlarını siler, kapatılmamış veya bozuk HTML/ASS etiketlerini kapatır, satır sonlarını normalize eder, küçük zamanlama çakışmalarını düzeltir ve negatif/sıfır süreleri tamir eder. Metin kısaltma veya okuma hızı gibi yoruma dayalı durumlar ise kullanıcının kararına bırakılır.

**S: Harici paket kurmadan sunucusuz (serverless) veya hafif ortamlarda çalışabilir mi?**  
C: Evet. `subtitle-tools`, hiçbir üçüncü taraf çalışma zamanı kütüphanesine ihtiyaç duymaz. Yalnızca standart bir Python 3.10+ ortamı yeterlidir.

## Katkıda Bulunma

Katkılarınızı memnuniyetle kabul ediyoruz! Geliştirme iş akışı, kodlama standartları ve detaylar için lütfen [CONTRIBUTING.md](CONTRIBUTING.md) belgesini inceleyin.

### Testleri ve Kalite Denetimlerini Çalıştırma

Kapsam raporu ile testleri çalıştırma:

```bash
pytest
```

Linter ve statik tip denetleyicisini çalıştırma:

```bash
ruff check .
mypy src
```

Testler standart Python `unittest` ile hiçbir harici paket olmadan da çalıştırılabilir:

```bash
python -m unittest discover -s tests
```

## Lisans

Bu proje MIT Lisansı altında lisanslanmıştır. Ayrıntılar için [LICENSE](LICENSE) dosyasına bakın.

Copyright (c) 2026 Yusuf Berat Zengin.
