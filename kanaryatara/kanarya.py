import json
import math
import pathlib

from .maskeleme import maskele
from .modeller import Bulgu, KanaryaTanimi, KayitSatiri


AZ_ORNEK_SINIRI = 5
MAKS_KAYIT_BOYUT = 10_000_000


def _sayi(x) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise ValueError
    try:
        deger = float(x)
    except (OverflowError, ValueError):
        raise ValueError
    if not math.isfinite(deger):
        raise ValueError
    return deger


def _okunan_metin(yol: str, ad: str) -> str:
    try:
        dosya = pathlib.Path(yol)
        if dosya.stat().st_size > MAKS_KAYIT_BOYUT:
            raise ValueError(f"{ad} çok büyük (10 MB üstü)")
        return dosya.read_text(encoding="utf-8-sig")
    except OSError as hata:
        raise ValueError(f"{ad} okunamadı: {hata}") from hata


def kanarya_yukle(yol: str) -> list[KanaryaTanimi]:
    try:
        veri = json.loads(_okunan_metin(yol, "kanarya dosyası"))
    except json.JSONDecodeError as hata:
        raise ValueError(f"kanarya dosyası ayrıştırılamadı: {hata}") from hata
    liste = veri.get("kanaryalar") if isinstance(veri, dict) else veri
    if not isinstance(liste, list):
        raise ValueError("kanarya dosyası 'kanaryalar' listesi bekliyor")
    kanaryalar: list[KanaryaTanimi] = []
    for i, nesne in enumerate(liste, 1):
        if not isinstance(nesne, dict):
            raise ValueError(f"{i}. kanarya nesne değil")
        kanarya_id = nesne.get("kanarya_id")
        vektor = nesne.get("vektor")
        probe = nesne.get("probe")
        if not isinstance(kanarya_id, str) or not kanarya_id.strip():
            raise ValueError(f"{i}. kanaryada kanarya_id eksik")
        if not isinstance(vektor, list) or not vektor:
            raise ValueError(f"{i}. kanaryada vektor geçersiz")
        try:
            sayilar = tuple(_sayi(x) for x in vektor)
        except ValueError:
            raise ValueError(f"{i}. kanaryada vektor geçersiz")
        if not isinstance(probe, str) or not probe.strip():
            raise ValueError(f"{i}. kanaryada probe eksik")
        konu = nesne.get("konu")
        kanaryalar.append(
            KanaryaTanimi(
                kanarya_id=kanarya_id.strip(),
                vektor=sayilar,
                probe=probe.strip(),
                konu=konu.strip()
                if isinstance(konu, str) and konu.strip()
                else "belirsiz",
            )
        )
    if not kanaryalar:
        raise ValueError("kanarya dosyasında hiç kanarya yok")
    return kanaryalar


def baseline_yukle(yol: str) -> tuple[str, dict[str, tuple[float, ...]]]:
    try:
        veri = json.loads(_okunan_metin(yol, "temel çizgi dosyası"))
    except json.JSONDecodeError as hata:
        raise ValueError(f"temel çizgi dosyası ayrıştırılamadı: {hata}") from hata
    if not isinstance(veri, dict):
        raise ValueError("temel çizgi dosyası nesne bekliyor")
    model_parmagi = veri.get("model_parmagi")
    vektorler = veri.get("vektorler")
    if not isinstance(model_parmagi, str) or not model_parmagi.strip():
        raise ValueError("model_parmagi eksik")
    if not isinstance(vektorler, dict):
        raise ValueError("vektorler sözlüğü eksik")
    sonuc: dict[str, tuple[float, ...]] = {}
    for kimlik, vektor in vektorler.items():
        if not isinstance(vektor, list) or not vektor:
            raise ValueError(f"{kimlik} için vektör geçersiz")
        try:
            sonuc[kimlik] = tuple(_sayi(x) for x in vektor)
        except ValueError:
            raise ValueError(f"{kimlik} için vektör geçersiz")
    if not sonuc:
        raise ValueError("temel çizgide hiç vektör yok")
    return model_parmagi.strip(), sonuc


def kayit_yukle(yol: str) -> list[KayitSatiri]:
    satirlar = _okunan_metin(yol, "kayıt dosyası").splitlines()
    kayitlar: list[KayitSatiri] = []
    for no, satir in enumerate(satirlar, 1):
        if not satir.strip():
            continue
        try:
            nesne = json.loads(satir)
        except json.JSONDecodeError as hata:
            raise ValueError(
                f"kayıt dosyası {no}. satır ayrıştırılamadı: {hata}"
            ) from hata
        if not isinstance(nesne, dict):
            raise ValueError(f"kayıt dosyası {no}. satır nesne değil")
        kanarya_id = nesne.get("kanarya_id")
        vektor = nesne.get("vektor")
        model_parmagi = nesne.get("model_parmagi")
        if not isinstance(kanarya_id, str) or not kanarya_id.strip():
            raise ValueError(f"{no}. satırda kanarya_id eksik")
        if not isinstance(vektor, list) or not vektor:
            raise ValueError(f"{no}. satırda vektor geçersiz")
        try:
            sayilar = tuple(_sayi(x) for x in vektor)
        except ValueError:
            raise ValueError(f"{no}. satırda vektor geçersiz")
        if not isinstance(model_parmagi, str) or not model_parmagi.strip():
            raise ValueError(f"{no}. satırda model_parmagi eksik")
        top_k = nesne.get("top_k")
        top_k_listesi = (
            tuple(str(x) for x in top_k)
            if isinstance(top_k, list) and all(isinstance(x, str) for x in top_k)
            else ()
        )
        kayitlar.append(
            KayitSatiri(
                kanarya_id=kanarya_id.strip(),
                vektor=sayilar,
                model_parmagi=model_parmagi.strip(),
                top_k=top_k_listesi,
            )
        )
    if not kayitlar:
        raise ValueError("kayıt dosyasında hiç kayıt yok")
    return kayitlar


def kosinus(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def _sapma_seviyesi(sapma: float) -> str | None:
    if sapma > 0.10:
        return "kritik"
    if sapma > 0.05:
        return "yuksek"
    if sapma > 0.02:
        return "orta"
    if sapma > 0.005:
        return "dusuk"
    return None


def karsilastir(
    kanaryalar: list[KanaryaTanimi],
    model_parmagi: str,
    vektorler: dict[str, tuple[float, ...]],
    kayitlar: list[KayitSatiri],
) -> tuple[list[Bulgu], list[str]]:
    """Kanarya vektörlerini temel çizgiyle karşılaştırır.

    LLM çağırmaz, embedding üretmez; yalnızca kayıtlardaki vektörlerin
    kosinüs benzerliğine bakar. Model parmak izi değiştiyse otomatik
    yeniden temel çizgi ÇEKİLMEZ; bulgu üretilir (fail-safe).
    """
    uyarilar: list[str] = []
    kayit_haritasi: dict[str, list[KayitSatiri]] = {}
    for k in kayitlar:
        kayit_haritasi.setdefault(k.kanarya_id, []).append(k)
    farkli_modeller = sorted(
        {k.model_parmagi for k in kayitlar if k.model_parmagi != model_parmagi}
    )
    if farkli_modeller:
        uyarilar.append(
            "Model/embedding parmak izi değişti (kayıt: "
            + ", ".join(maskele(m) for m in farkli_modeller)
            + "; temel çizgi: "
            + maskele(model_parmagi)
            + "). Kosinüs karşılaştırması yapılmadı; yeniden temel çizgi "
            "çekilmeli (insan onayı)."
        )
        return [
            Bulgu(
                kural="KNT07",
                seviye="kritik",
                belge="—",
                dosya="",
                satir=0,
                sinyal="model_parmagi_degisti",
                guven="yuksek",
                kanit=maskele(", ".join(farkli_modeller)),
                aciklama="Model/embedding parmak izi değişti; temel çizgi geçersiz sayıldı.",
                oneri="İnsan onayıyla yeniden temel çizgi çekin; eski referansla karşılaştırma bilinçli olarak yapılmadı.",
            )
        ], uyarilar
    az_ornek = len(kanaryalar) < AZ_ORNEK_SINIRI
    if az_ornek:
        uyarilar.append(
            f"Kanarya sayısı {len(kanaryalar)} < {AZ_ORNEK_SINIRI}; sapma bulgularının "
            "güveni düşük örnek sayısı nedeniyle 'dusuk' işaretlenir ve seviye "
            "'orta'yı aşmaz."
        )
    bulgular: list[Bulgu] = []
    for kan in kanaryalar:
        temel = vektorler.get(kan.kanarya_id)
        if temel is None:
            uyarilar.append(f"{kan.kanarya_id}: temel çizgide vektör yok, atlandı.")
            continue
        esler = kayit_haritasi.get(kan.kanarya_id)
        if not esler:
            seviye = "yuksek"
            guven = "orta"
            if az_ornek:
                seviye = "orta"
                guven = "dusuk"
            bulgular.append(
                Bulgu(
                    kural="KNT07",
                    seviye=seviye,
                    belge=kan.kanarya_id,
                    dosya="",
                    satir=0,
                    sinyal="kanarya_bulunamadi",
                    guven=guven,
                    kanit=maskele(kan.kanarya_id),
                    aciklama="Kanarya kayıt dosyasında yok; retrieval'da kaybolmuş olabilir.",
                    oneri="Kanarya belgesinin hâlâ bilgi tabanında olduğunu doğrulayın.",
                )
            )
            continue
        uygunlar = [k for k in esler if len(k.vektor) == len(temel)]
        if not uygunlar:
            uyarilar.append(
                f"{kan.kanarya_id}: vektör boyutu uyuşmuyor "
                f"(temel {len(temel)}), atlandı."
            )
            continue
        if len(uygunlar) != len(esler):
            uyarilar.append(
                f"{kan.kanarya_id}: {len(esler) - len(uygunlar)} kayıt boyut uyuşmazlığıyla atlandı."
            )
        for k in uygunlar:
            if not k.top_k:
                uyarilar.append(
                    f"{kan.kanarya_id}: top_k boş; probe smoke testi (kanarya bulunmalı) yapılamadı."
                )
                break
        benzerlik = min(kosinus(temel, k.vektor) for k in uygunlar)
        sapma = 1.0 - benzerlik
        seviye = _sapma_seviyesi(sapma)
        if seviye is None:
            continue
        guven = "orta"
        if az_ornek:
            guven = "dusuk"
            if seviye in ("yuksek", "kritik"):
                seviye = "orta"
        bulgular.append(
            Bulgu(
                kural="KNT07",
                seviye=seviye,
                belge=kan.kanarya_id,
                dosya="",
                satir=0,
                sinyal="kose_benzerligi_sapmasi",
                guven=guven,
                kanit=f"cos={benzerlik:.4f}",
                aciklama=f"Kanarya vektörü temel çizgiden sapmış (kosinüs benzerliği {benzerlik:.4f}).",
                oneri="Sapmayı insan doğrulamasına götürün; zehirlenme şüphesi kesin kanıt değildir.",
            )
        )
    bulgular.sort(key=lambda x: x.belge)
    return bulgular, uyarilar
