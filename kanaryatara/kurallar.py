import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta
from urllib.parse import urlsplit

from .belge import Belge
from .maskeleme import maskele, url_maskele
from .modeller import Bulgu


_TALIMAT_TR = (
    "önceki talimatları yok say",
    "yukarıdaki talimatları",
    "önceki talimatlar",
    "sistem mesajı",
    "sistem talimatı",
    "sen artık",
    "yeni talimatları",
    "talimatları geçersiz",
    "gizli yanıt",
)
_TALIMAT_EN = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard prior",
    "you are now",
    "system prompt",
    "override your instructions",
    "as an ai",
)
_OTORITE_DESENLERI = (
    r"\bresm",
    "kurumsal onay",
    "onaylanmıştır",
    "politika gereği",
    "yetkili kurum",
    "zorunlu tutulmuş",
)
_TARIH_RE = re.compile(r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b")
_GORSEL_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
_LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)\)")
_SOZCUK_RE = re.compile(r"\w+")
_KNT06_SINIRI = 500
_KNT06_EN_AZ_SOZCUK = 30
_KNT06_BENZERLIK = 0.85


def _normalize(metin: str) -> str:
    return metin.casefold()


def _satir_bul(metin: str, kosul) -> tuple[int, str]:
    for no, satir in enumerate(metin.splitlines(), 1):
        if kosul(satir):
            return no, satir
    return 0, ""


def _knt01(belge: Belge) -> list[Bulgu]:
    norm = _normalize(belge.metin)
    eslesenler = [d for d in _TALIMAT_TR + _TALIMAT_EN if d in norm]
    if not eslesenler:
        return []
    seviye = "yuksek" if len(eslesenler) >= 2 else "dusuk"
    no, satir = _satir_bul(
        belge.metin, lambda s: any(d in _normalize(s) for d in eslesenler)
    )
    return [
        Bulgu(
            kural="KNT01",
            seviye=seviye,
            belge=belge.belge_id,
            dosya=belge.dosya,
            satir=no,
            sinyal="talimat_benzeri_icerik",
            guven="orta",
            kanit=maskele(satir.strip()),
            aciklama=f"Belgede {len(eslesenler)} talimat benzeri kalıp bulundu.",
            oneri="Bilgi tabanına girecek belgelerde talimat dili arayın; bu tür içerik modeli ele geçirmek için kullanılır.",
        )
    ]


def _knt02(belge: Belge) -> list[Bulgu]:
    gizli = sorted(
        {
            f"U+{ord(c):04X}"
            for c in belge.metin
            if unicodedata.category(c) == "Cf" and c != "\ufeff"
        }
    )
    kucuk = belge.metin.casefold()
    html_sinyalleri = [
        d
        for d in (
            "<!--",
            "display:none",
            "visibility:hidden",
            "font-size:0",
            "hidden=",
            "&#",
        )
        if d in kucuk
    ]
    if not gizli and not html_sinyalleri:
        return []
    norm = _normalize(belge.metin)
    talimat_var = any(d in norm for d in _TALIMAT_TR + _TALIMAT_EN)
    seviye = "yuksek" if (gizli and talimat_var) else "orta"
    parcalar = []
    if gizli:
        parcalar.append("görünmez: " + ", ".join(gizli))
    if html_sinyalleri:
        parcalar.append("html: " + ", ".join(html_sinyalleri))
    return [
        Bulgu(
            kural="KNT02",
            seviye=seviye,
            belge=belge.belge_id,
            dosya=belge.dosya,
            satir=0,
            sinyal="gizli_karakter_html",
            guven="yuksek",
            kanit="; ".join(parcalar),
            aciklama="Belgede görünmez karakter veya gizlenmiş HTML parçası var.",
            oneri="Görünmez karakterleri ayıklayın ve gizlenmiş HTML parçalarını belgeden çıkarın.",
        )
    ]


def _tarih_ayristir(metin: str) -> date | None:
    for bicim in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(metin, bicim).date()
        except ValueError:
            continue
    return None


def _tarih_gelecekte(metin: str, gun: int = 30) -> tuple[bool, str]:
    for m in _TARIH_RE.finditer(metin):
        d = _tarih_ayristir(m.group())
        if d and d > date.today() + timedelta(days=gun):
            return True, m.group()
    return False, ""


def _knt03(belge: Belge) -> list[Bulgu]:
    bulgular: list[Bulgu] = []
    norm = _normalize(belge.metin)
    gelecek, tarih = _tarih_gelecekte(belge.metin)
    if gelecek:
        no, satir = _satir_bul(belge.metin, lambda s: tarih in s)
        bulgular.append(
            Bulgu(
                kural="KNT03",
                seviye="orta",
                belge=belge.belge_id,
                dosya=belge.dosya,
                satir=no,
                sinyal="tarih_anomalisi",
                guven="yuksek",
                kanit=maskele(satir.strip()),
                aciklama=f"Belgede bugüne göre ileri tarih var ({tarih}).",
                oneri="Tarih iddialarını kaynakla doğrulayın; sahte tarih damgası zehirleme tekniğidir.",
            )
        )
    otorite = [d for d in _OTORITE_DESENLERI if re.search(d, norm)]
    if otorite:
        kuvvetli = any(
            k in norm
            for k in ("politika", "zorunl", "erişim", "gizlilik", "onaylanmıştır")
        )
        seviye = "yuksek" if kuvvetli else "orta"
        no, satir = _satir_bul(
            belge.metin, lambda s: any(re.search(d, _normalize(s)) for d in otorite)
        )
        guven = "yuksek" if belge.kaynak else "dusuk"
        ek = "" if belge.kaynak else " Kaynak alanı boş; iddia doğrulanamadı."
        bulgular.append(
            Bulgu(
                kural="KNT03",
                seviye=seviye,
                belge=belge.belge_id,
                dosya=belge.dosya,
                satir=no,
                sinyal="imza_otorite",
                guven=guven,
                kanit=maskele(satir.strip()),
                aciklama="Belgede doğrulanamayan otorite/onay dili bulundu." + ek,
                oneri="Onay ve politika iddialarını insan doğrulamasına tabi tutun.",
            )
        )
    return bulgular


def _alan_izinli(netloc: str, izinli: tuple[str, ...]) -> bool:
    netloc = netloc.casefold().rstrip(".")
    for alan in izinli:
        alan = alan.casefold().rstrip(".")
        if netloc == alan or netloc.endswith("." + alan):
            return True
    return False


def _knt04(belge: Belge, izinli: tuple[str, ...]) -> list[Bulgu]:
    bulgular: list[Bulgu] = []
    gorulenler: set[tuple[str, str]] = set()
    hedefler = [(m.group(1), True) for m in _GORSEL_RE.finditer(belge.metin)]
    hedefler += [(m.group(1), False) for m in _LINK_RE.finditer(belge.metin)]
    for url, gorsel in hedefler:
        try:
            parca = urlsplit(url)
        except ValueError:
            continue
        if parca.scheme not in ("http", "https", "data"):
            continue
        if parca.scheme == "data":
            sinyal, seviye = "data_uri", "yuksek"
        elif _alan_izinli(parca.netloc, izinli):
            continue
        elif gorsel:
            sinyal, seviye = "dis_gorsel", "yuksek"
        else:
            sinyal, seviye = "dis_baglanti", "dusuk"
        if (sinyal, url) in gorulenler:
            continue
        gorulenler.add((sinyal, url))
        no, satir = _satir_bul(belge.metin, lambda s: url in s)
        tur = "görsel" if gorsel else "bağlantı"
        bulgular.append(
            Bulgu(
                kural="KNT04",
                seviye=seviye,
                belge=belge.belge_id,
                dosya=belge.dosya,
                satir=no,
                sinyal=sinyal,
                guven="orta",
                kanit=url_maskele(url),
                aciklama=f"Dış kaynaklı Markdown {tur} bulundu.",
                oneri="Belge alındığında otomatik yüklenen dış görselleri engelleyin; izinli alanları --izinli-alan-adi ile bildirin.",
            )
        )
    return bulgular


def _knt05(belgeler: list[Belge]) -> list[Bulgu]:
    bulgular: list[Bulgu] = []
    idler: dict[str, list[Belge]] = defaultdict(list)
    for b in belgeler:
        idler[b.belge_id].append(b)
        if not b.yapilandirilmis:
            continue
        if not b.kaynak:
            bulgular.append(
                Bulgu(
                    kural="KNT05",
                    seviye="dusuk",
                    belge=b.belge_id,
                    dosya=b.dosya,
                    satir=b.satir,
                    sinyal="kaynak_eksik",
                    guven="yuksek",
                    kanit="—",
                    aciklama="Kaynak alanı boş; belgenin nereden geldiği doğrulanamıyor.",
                    oneri="Her belgeye kaynak ve sahibini ekleyin.",
                )
            )
        if b.zaman:
            gelecek, _ = _tarih_gelecekte(b.zaman)
            if gelecek:
                bulgular.append(
                    Bulgu(
                        kural="KNT05",
                        seviye="orta",
                        belge=b.belge_id,
                        dosya=b.dosya,
                        satir=b.satir,
                        sinyal="tarih_anomalisi",
                        guven="yuksek",
                        kanit=maskele(b.zaman),
                        aciklama="Metadata zaman alanı ileri tarihli.",
                        oneri="Zaman alanını kaynakla doğrulayın.",
                    )
                )
    for belge_id, kume in idler.items():
        if len(kume) > 1:
            dosyalar = sorted({b.dosya for b in kume})
            bulgular.append(
                Bulgu(
                    kural="KNT05",
                    seviye="yuksek",
                    belge=belge_id,
                    dosya=dosyalar[0],
                    satir=0,
                    sinyal="kimlik_cakismasi",
                    guven="yuksek",
                    kanit=maskele(belge_id),
                    aciklama=f"Aynı belge kimliği {len(kume)} kayıtta geçiyor.",
                    oneri="Belge kimliklerini koleksiyonda benzersiz tutun.",
                )
            )
    return bulgular


def _n_gramlar(sozcukler: list[str]) -> set[tuple[str, ...]]:
    return {tuple(sozcukler[i : i + 3]) for i in range(len(sozcukler) - 2)}


def _knt06(belgeler: list[Belge]) -> tuple[list[Bulgu], list[str]]:
    if len(belgeler) > _KNT06_SINIRI:
        return [], [
            f"{len(belgeler)} belge yakın-kopya taraması için fazla; "
            f"KNT06 atlandı (sınır {_KNT06_SINIRI})."
        ]
    adaylar = [
        b
        for b in belgeler
        if len(_SOZCUK_RE.findall(_normalize(b.metin))) >= _KNT06_EN_AZ_SOZCUK
    ]
    if len(adaylar) < 2:
        return [], []
    sozluk = {b.belge_id: b for b in adaylar}
    imzalar = {
        b.belge_id: _n_gramlar(_SOZCUK_RE.findall(_normalize(b.metin))) for b in adaylar
    }
    ebeveyn = {k: k for k in imzalar}

    def bul(x: str) -> str:
        while ebeveyn[x] != x:
            ebeveyn[x] = ebeveyn[ebeveyn[x]]
            x = ebeveyn[x]
        return x

    def birles(x: str, y: str) -> None:
        rx, ry = bul(x), bul(y)
        if rx != ry:
            ebeveyn[ry] = rx

    anahtarlar = list(imzalar)
    for i in range(len(anahtarlar)):
        for j in range(i + 1, len(anahtarlar)):
            a, b = imzalar[anahtarlar[i]], imzalar[anahtarlar[j]]
            birlesim = len(a | b)
            if birlesim and len(a & b) / birlesim >= _KNT06_BENZERLIK:
                birles(anahtarlar[i], anahtarlar[j])
    kumeler: dict[str, list[str]] = defaultdict(list)
    for k in imzalar:
        kumeler[bul(k)].append(k)
    bulgular: list[Bulgu] = []
    for kume in kumeler.values():
        if len(kume) < 2:
            continue
        talimat_var = any(
            any(d in _normalize(sozluk[k].metin) for d in _TALIMAT_TR + _TALIMAT_EN)
            for k in kume
        )
        seviye = "yuksek" if talimat_var else "orta"
        ilk = min(kume)
        bulgular.append(
            Bulgu(
                kural="KNT06",
                seviye=seviye,
                belge=ilk,
                dosya=sozluk[ilk].dosya,
                satir=0,
                sinyal="yakin_kopya_kumesi",
                guven="orta",
                kanit=f"{len(kume)} belge",
                aciklama=f"Birbirine çok benzeyen {len(kume)} belge kümelendi.",
                oneri="Aynı iddiayı yayan yakın kopyaları kaynakla doğrulayın; zehirleme çoğu kez tekrarla çalışır.",
            )
        )
    return bulgular, []


def tara_belgeler(
    belgeler: list[Belge], izinli_alanlar: tuple[str, ...] = ()
) -> tuple[list[Bulgu], list[str]]:
    bulgular: list[Bulgu] = []
    for b in belgeler:
        bulgular += _knt01(b)
        bulgular += _knt02(b)
        bulgular += _knt03(b)
        bulgular += _knt04(b, izinli_alanlar)
    bulgular += _knt05(belgeler)
    knt06_bulgular, uyarilar = _knt06(belgeler)
    bulgular += knt06_bulgular
    bulgular.sort(key=lambda x: (x.dosya, x.satir, x.kural))
    return bulgular, uyarilar
