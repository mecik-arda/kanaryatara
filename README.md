# kanaryatara

RAG bilgi tabanındaki belgeleri çalıştırmadan tarayan hafif, **çevrimdışı** bütünlük denetçisi.

JSONL/JSON/Markdown/düz metin belge koleksiyonlarını statik kurallarla tarar; kanarya belge vektörlerindeki kosinüs sapmasını temel çizgiyle karşılaştırır. LLM çağırmaz, embedding üretmez, ağa bağlanmaz, kodu çalıştırmaz. Çıktılar Türkçedir, CI'da kullanılabilir (`--bicim json`, çıkış kodları 0/1/2).

> **İlham:** PoisonedRAG, Phantom, MM-PoisonRAG ve One Shot Dominance — bilgi tabanına sızan az sayıda belgeyle cevabı ele geçiren, bazıları yalnızca tetikleyici kelimede aktifleşen zehirleme saldırıları. Saldırı tarafı araştırma makaleleriyle iyi belgelenmiş; defans tarafında "kendi bilgi tabanımı izlemek" için bağımsız ve Türkçe bir araç yoktu.

---

## Özellikler

- **Talimat benzeri içerik (KNT01)** — TR+EN "önceki talimatları yok say", "ignore previous instructions", rol değiştirme kalıpları; birden çok kalıp yüksek risk işaretler
- **Görünmez karakter ve gizli HTML (KNT02)** — sıfır genişlikli/denetim karakterleri, HTML yorumu, `display:none` ve benzeri gizleme kalıpları
- **İmza-otorite sahteciliği (KNT03)** — "resmî olarak onaylanmıştır" türü uydurma onay dili ve ileri tarihli damgalar; kaynak yoksa "doğrulanamadı" diye raporlar
- **Dış görsel/bağlantı (KNT04)** — Markdown görselleri, `data:` URI'leri ve dış bağlantılar; `--izinli-alan-adi` ile kurum alanları susturulur
- **Metadata anomalisi (KNT05)** — kaynak alanı boş, ileri tarihli zaman, koleksiyonda çakışan belge kimlikleri
- **Yakın-kopya kümeleri (KNT06)** — aynı iddiayı küçük farklarla yayan belgelerin 3-gram Jaccard kümelemesi
- **Kanarya sapması (KNT07)** — kanarya vektörlerinin temel çizgiyle kosinüs karşılaştırması; model/embedding parmak izi değişirse otomatik yeniden temel çizgi çekilmez, insan onayı istenir (fail-safe)
- **Çıkış kodları** — eşik ve üzeri bulgu varsa 1, temizse 0, girdi/kullanım hatasında 2
- **JSON çıktı** — `--bicim json` ile makine okunur sonuç; kanıtlar maskelenir

## Kurulum

```bash
git clone https://github.com/mecik-arda/kanaryatara
cd kanaryatara
pip install .
```

Kurulum olmadan da çalışır: `python -m kanaryatara.cli tara ...`

## Kullanım

```bash
# Belge koleksiyonunu tara
kanaryatara tara ./belgeler

# Tek dosya, JSON olarak (CI için)
kanaryatara tara ornekler/riskli.jsonl --bicim json --esik orta

# Kurumun kendi alan adını izin listesine al
kanaryatara tara ./belgeler --izinli-alan-adi kurum.example.com

# Kanarya vektörlerini temel çizgiyle karşılaştır
kanaryatara karsilastir --kanarya ornekler/kanarya.json --baseline ornekler/baseline.json --kayit ornekler/kayit.jsonl
```

Örnek çıktı (`tara ornekler/riskli.jsonl`):

```
KanaryaTara: 10 belge, 8 bulgu.
[Yuksek] KNT01 ornekler\riskli.jsonl:1 (belge-1): Belgede 3 talimat benzeri kalıp bulundu.
  Kanıt: Önceki***in.
  Güven: orta
  Öneri: Bilgi tabanına girecek belgelerde talimat dili arayın; bu tür içerik modeli ele geçirmek için kullanılır.
[Yuksek] KNT04 ornekler\riskli.jsonl:5 (belge-5): Dış kaynaklı Markdown görsel bulundu.
  Kanıt: https://izleme.example.com/***
  Güven: orta
  Öneri: Belge alındığında otomatik yüklenen dış görselleri engelleyin; izinli alanları --izinli-alan-adi ile bildirin.
[Yuksek] KNT05 ornekler\riskli.jsonl (tekrar-1): Aynı belge kimliği 2 kayıtta geçiyor.
  Kanıt: te***
  Güven: yuksek
  Öneri: Belge kimliklerini koleksiyonda benzersiz tutun.
Risk eşiğine ulaşıldı.
```

`karsilastir` çıktısı:

```
KanaryaTara: 5 kanarya, 1 bulgu.
[Kritik] KNT07 kan-3: Kanarya vektörü temel çizgiden sapmış (kosinüs benzerliği 0.8000).
  Kanıt: cos=0.8000
  Güven: orta
  Öneri: Sapmayı insan doğrulamasına götürün; zehirlenme şüphesi kesin kanıt değildir.
Risk eşiğine ulaşıldı.
```

## Girdi sözleşmesi

**Belgeler** — JSONL'de her satır bir belge: `belge_id` ve `metin` zorunlu, `kaynak`, `zaman`, `etiket` isteğe bağlı. JSON'da aynı nesnelerin dizisi. Markdown/düz metin dosyaları tek belge sayılır; metadata kuralları (KNT05) bunlarda çalışmaz.

**Kanarya** (`--kanarya`) — `{"kanaryalar": [{"kanarya_id", "probe", "vektor": [...], "konu"?}]}`. Vektörler kendi embedding boru hattınızdan gelir; bu araç embedding üretmez.

**Temel çizgi** (`--baseline`) — `{"model_parmagi": "...", "vektorler": {id: [...]}}`. Model/embedding değişiminde parmak izi eşleşmez ve karşılaştırma bilinçli olarak durur.

**Kayıt** (`--kayit`) — JSONL: `{"kanarya_id", "model_parmagi", "vektor": [...], "top_k": [...]}`. `top_k` boşsa probe smoke testi yapılamadı uyarısı verilir.

## Denetlenenler

| Kural | JSONL/JSON | MD/TXT | Açıklama |
|---|---|---|---|
| KNT01 talimat benzeri içerik | ✓ | ✓ | TR + EN kalıp seti |
| KNT02 görünmez karakter / gizli HTML | ✓ | ✓ | `Cf` kategorisi + gizleme kalıpları |
| KNT03 imza-otorite / tarih anomalisi | ✓ | ✓ | kaynak yoksa "doğrulanamadı" |
| KNT04 dış görsel / bağlantı | ✓ | ✓ | `--izinli-alan-adi` desteği |
| KNT05 metadata anomalisi | ✓ | — | düz metin dosyalarında metadata yoktur |
| KNT06 yakın-kopya kümeleri | ✓ | ✓ | 3-gram Jaccard ≥ 0.85 |
| KNT07 kanarya vektör sapması | ✓ | ✓ | `karsilastir` komutu ile |

`.git`, `__pycache__`, `.venv`, `node_modules` atlanır. 1 MB üstü dosyalar atlanır ve `Uyarı:` satırı basılır; bozuk dosyalar dizin modunda uyarıyla atlanır, tek dosya hedeflendiğinde hatadır (çıkış kodu 2).

## Rakipler ve fark

Bu alan dolu; işte dürüst konumlandırma. Aşağıdaki araçların hiçbiri awesome-ai-security-tr listesinde yer almıyor ve hiçbiri Türkçe değil; kanaryatara bu iki boşluğu birden hedefliyor:

- [ragaudit](https://github.com/kriskimmerle/ragaudit) — embedding öncesi statik belge taraması (OWASP Agentic ASI06). Fark: kanaryatara ingest **ve** retrieval bütünlüğünü birlikte izler, Türkçe kural seti taşır.
- [embedding-drift-watch](https://github.com/aks-builds/embedding-drift-watch) — kanarya + çevrimdışı drift izleme; yaklaşım olarak en yakın akraba. Fark: saldırı sınıflarına eşlenmiş tespit (PoisonedRAG/Phantom/One Shot Dominance), model parmak izi kontrolü, insan onaylı yeniden temel çizgi ve Türkçe raporlama.
- [rag-security-scanner](https://github.com/olegnazarov/rag-security-scanner) — genel RAG/LLM güvenlik tarayıcısı. Fark: sıfır bağımlılık, çevrimdışı öncelik, Türkçe çıktı.
- [ragshield](https://github.com/ksrpatil/ragshield) — provenance-doğrulamalı zehirlenme savunması. Fark: kanarya + kümelenme yöntemleri.
- [rag-sentinel](https://github.com/mizcausevic-dev/rag-sentinel) — retrieval drift ve chunk yönetişimi. Fark: kural aileleri ve Türkçe arayüz.
- [canary-doc-injector](https://github.com/zAx4hub/canary-doc-injector) — sızıntı yakalamak için kanarya enjeksiyonu. Fark: kanaryatara zehirlenme/bütünlük sinyaline odaklanır.

## Güvenlik modeli

- Araç **yalnızca okur**; belgeleri değiştirmez, kod çalıştırmaz, ağa bağlanmaz, LLM çağırmaz.
- Kanıtlar maskelenir; ham içerik rapora yazılmaz.
- Araç asla otomatik engelleme yapmaz; bulgu bir **risk göstergesidir**, kesin kanıt değildir. İnsan doğrulaması şarttır.
- Kanarya vektörlerini üreten embedding boru hattı araç dışıdır; araç yalnızca kayıtları karşılaştırır.

## Sınırlamalar

- Statik tarama yaklaşıktır: kodlanmış, parçalanmış veya bilinmeyen kalıplar kaçabilir.
- Yalnızca tetikleyici kelimede aktifleşen hedefli zehirleme, kanarya sorgularında sessiz kalabilir — bu yüzden kanarya sinyali asla tek başına karar kriteri olmamalıdır.
- Embedding modeli değişimi gerçek saldırı olmadan sapma üretir; bu yüzden model parmak izi değişince karşılaştırma durur ve insan onaylı yeniden temel çizgi beklenir.
- Küçük kanarya kümelerinde (<5) sapma bulguları düşük güvenle işaretlenir ve seviyesi orta ile sınırlanır.

## Geliştirme

```bash
python -m unittest discover -s tests -v
python -m ruff check .
```

## Yol haritası

- [x] MVP: 7 kural, metin/JSON rapor, maskeleme, eşik tabanlı çıkış kodları, kanarya kosinüs karşılaştırması
- [ ] `kanarya-olustur` komutu: konu-yoğun sentetik kanarya/probe üretici
- [ ] İki kademeli RBO sıralama karşılaştırması + k-NN komşuluk yoğunluğu drifti
- [ ] Opsiyonel canlı mod bağlayıcısı (varsayılan kapalı), SARIF çıktısı

## Lisans

[MIT](LICENSE) — [Arda Meçik](https://github.com/mecik-arda)

Bu proje, Türkçe yapay zeka güvenliği kaynak listesi
[awesome-ai-security-tr](https://github.com/fevziegeyurtsevenler/awesome-ai-security-tr)
ekosistemine katkı kapsamında geliştirilmiştir.

---

## Yazar

**[Arda Meçik](https://github.com/mecik-arda)** — siber güvenlik ve yapay zeka güvenliği üzerine çalışan geliştirici.

---

## Bu repoyu beğendiyseniz

KanaryaTara, **Arda Meçik** tarafından geliştirilmiştir. Türkçe yapay zeka güvenliği ekosistemine katkı sağlamak için yazılan bu projeyi beğendiyseniz:

- **Yıldızlamayı unutmayın** — açık kaynak projelere destek, görünürlük demektir.
- **Takip edin:** [github.com/mecik-arda](https://github.com/mecik-arda) — RAG güvenliği, LLM kod denetimi ve ajan güvenliği üzerine sürekli yeni araçlar ve Türkçe siber güvenlik yazıları yayımlıyorum.
- **Aynı ailenin diğer araçları:**
  - [vektortara](https://github.com/mecik-arda/vektortara) — ChromaDB/Qdrant/Weaviate güvenlik tarayıcısı
  - [kodtara](https://github.com/mecik-arda/kodtara) — LLM uygulama kodu statik tarayıcısı
  - [izkalkan](https://github.com/mecik-arda/izkalkan) — ajan çağrı izlerinde hassas veri ve dış iletişim risk analizi
- **İş birliği / proje teklifleri için:** GitHub üzerinden iletişime geçebilirsiniz.

Her yıldız, yeni bir Türkçe güvenlik aracının yazılmasına teşvik olur. Teşekkürler!
