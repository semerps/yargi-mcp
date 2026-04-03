# Yargı MCP

SEM-AI için yeniden düzenlenmiş, Türk hukuk kaynaklarına erişim sağlayan bir MCP sunucusu.

Bu repo, karar arama ve belge getirme işlemlerini tek bir MCP arayüzünde toplar. Hedef; SEM-AI tabanlı iş akışlarında mahkeme kararlarını, düzenleyici kurum kararlarını ve ilgili belgeleri hızlı şekilde aramak, filtrelemek ve Markdown olarak almak için temiz bir entegrasyon katmanı sunmaktır.

## Kapsam

Projede öne çıkan veri kaynakları şunlardır:

- Bedesten üzerinden Yargıtay, Danıştay, Yerel Hukuk, İstinaf Hukuk ve KYB
- Anayasa Mahkemesi
- Sayıştay
- KİK
- Rekabet Kurumu
- Emsal kararlar
- Uyuşmazlık Mahkemesi
- KVKK
- BDDK
- Sigorta Tahkim Komisyonu

## Yeni çalışma yapısı

Bu sürümde yapı, SEM-AI kullanımı için sadeleştirildi:

- Arama ve belge getirme mantığı kurum bazlı modüllere ayrıldı.
- Ortak akışlar mümkün olan yerlerde birleştirildi.
- Uzun belgeler sayfalanmış Markdown olarak döndürülüyor.
- Bedesten tarafında Yargıtay ve Danıştay aramaları tek birleşik akıştan yönetiliyor.
- Anayasa ve Sayıştay tarafında birleşik araçlar kullanılıyor.

### Temel giriş noktaları

- `mcp_server_main.py` - ana MCP sunucusu
- `asgi_app.py` - HTTP / ASGI katmanı
- `run_asgi.py` - yerel ASGI çalıştırıcısı
- `__main__.py` - paket giriş noktası

### Modül yapısı

Her kurum kendi klasöründe tutulur:

- `bedesten_mcp_module/`
- `anayasa_mcp_module/`
- `sayistay_mcp_module/`
- `kik_mcp_module/`
- `rekabet_mcp_module/`
- `emsal_mcp_module/`
- `uyusmazlik_mcp_module/`
- `kvkk_mcp_module/`
- `bddk_mcp_module/`
- `sigorta_tahkim_mcp_module/`
- `yargitay_mcp_module/`
- `danistay_mcp_module/`

## Kurulum

Python 3.11+ önerilir.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Ortam değişkenleri için:

```bash
cp .env.example .env
```

## Çalıştırma

### 1) MCP sunucusu olarak

```bash
yargi-mcp
```

veya:

```bash
python mcp_server_main.py
```

### 2) ASGI / HTTP sunucusu olarak

```bash
python run_asgi.py
```

Alternatif olarak doğrudan Uvicorn ile:

```bash
python -m uvicorn asgi_app:app --host 127.0.0.1 --port 8000
```

## Önemli ortam değişkenleri

`.env` dosyasında en sık kullanılan ayarlar:

- `HOST`
- `PORT`
- `LOG_LEVEL`
- `RELOAD`
- `ALLOWED_ORIGINS`
- `BASE_URL`

## Kullanım örnekleri

### Bedesten ile karar arama

```python
results = await search_bedesten_unified(
    phrase="mülkiyet hakkı",
    court_types=["YARGITAYKARARI"],
    birimAdi="1. Hukuk Dairesi",
    kararTarihiStart="2024-01-01T00:00:00.000Z",
    kararTarihiEnd="2024-12-31T23:59:59.999Z",
    pageSize=5,
)
```

### Bedesten ile belge getirme

```python
document = await get_bedesten_document_markdown(documentId="123456")
```

### Anayasa Mahkemesi birleşik arama

```python
results = await search_anayasa_unified(
    decision_type="norm_denetimi",
    keywords_all=["ifade özgürlüğü"],
    results_per_page=10,
)
```

### Sayıştay birleşik arama

```python
results = await search_sayistay_unified(
    decision_type="genel_kurul",
    karar_no="5415",
)
```

### KİK v2 arama

```python
results = await search_kik_decisions(
    karar_turu="uyusmazlik",
    keyword="ihale iptali",
    page=1,
)
```

## SEM-AI için önerilen akış

1. Önce ilgili kurum için arama aracı çalıştır.
2. Sonuçtan `documentId`, `id` veya `url` al.
3. Tam metin gerekiyorsa belge getirme aracını kullan.
4. Uzun kararlar için sayfalı Markdown çıktısını parça parça işle.

## Notlar

- Arama araçları yalnızca keşif içindir.
- Belge araçları tam metin ve analiz için tasarlanmıştır.
- Büyük metinler Markdown'a çevrilerek LLM işlemlerine uygun hale getirilir.
- Yerel çalıştırmada `uv` zorunlu değildir; `python -m pip` ve `python -m uvicorn` akışı yeterlidir.

## Kısa özet

Bu repo, SEM-AI kullanımına uygun şekilde yeniden düzenlenmiş bir Türk hukuk MCP sunucusudur. Amaç, farklı kurum kaynaklarını tek ve okunabilir bir arayüzde toplayıp karar arama, belge çekme ve metin işleme adımlarını sadeleştirmektir.
