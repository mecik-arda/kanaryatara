import json
import pathlib
from dataclasses import dataclass


DESTEKLENEN_UZANTILAR = {".jsonl", ".json", ".md", ".txt"}
YAPILANDIRILMIS_UZANTILAR = {".jsonl", ".json"}
ATLANAN_DIZINLER = {
    ".git",
    "__pycache__",
    ".venv",
    "node_modules",
    ".pytest_cache",
    ".ruff_cache",
}
MAKS_BOYUT = 1_000_000


class OkumaHatasi(ValueError):
    pass


@dataclass(frozen=True)
class Belge:
    belge_id: str
    metin: str
    dosya: str
    satir: int
    kaynak: str | None = None
    zaman: str | None = None
    etiket: str | None = None
    yapilandirilmis: bool = True


def _alan(nesne: dict, anahtar: str) -> str | None:
    deger = nesne.get(anahtar)
    return deger.strip() if isinstance(deger, str) and deger.strip() else None


def _belge_ayristir(
    nesne: dict, dosya: str, satir: int, yapilandirilmis: bool
) -> Belge:
    belge_id = nesne.get("belge_id")
    metin = nesne.get("metin")
    if not isinstance(belge_id, str) or not belge_id.strip():
        raise OkumaHatasi("belge_id eksik veya boş")
    if not isinstance(metin, str):
        raise OkumaHatasi("metin eksik veya metin değil")
    return Belge(
        belge_id=belge_id.strip(),
        metin=metin,
        dosya=dosya,
        satir=satir,
        kaynak=_alan(nesne, "kaynak"),
        zaman=_alan(nesne, "zaman"),
        etiket=_alan(nesne, "etiket"),
        yapilandirilmis=yapilandirilmis,
    )


def _dosya_belgeleri(dosya: pathlib.Path) -> list[Belge]:
    if dosya.stat().st_size > MAKS_BOYUT:
        raise OkumaHatasi("çok büyük (1 MB üstü)")
    metin = dosya.read_text(encoding="utf-8")
    uzanti = dosya.suffix.lower()
    if uzanti == ".jsonl":
        belgeler = []
        for no, satir in enumerate(metin.splitlines(), 1):
            if not satir.strip():
                continue
            try:
                nesne = json.loads(satir)
            except json.JSONDecodeError as hata:
                raise OkumaHatasi(f"{no}. satır ayrıştırılamadı: {hata}") from hata
            if not isinstance(nesne, dict):
                raise OkumaHatasi(f"{no}. satır nesne değil")
            belgeler.append(_belge_ayristir(nesne, str(dosya), no, True))
        return belgeler
    if uzanti == ".json":
        try:
            nesne = json.loads(metin)
        except json.JSONDecodeError as hata:
            raise OkumaHatasi(f"JSON ayrıştırılamadı: {hata}") from hata
        if not isinstance(nesne, list):
            raise OkumaHatasi("JSON dizisi bekleniyor")
        for i, o in enumerate(nesne, 1):
            if not isinstance(o, dict):
                raise OkumaHatasi(f"{i}. öğe nesne değil")
        return [
            _belge_ayristir(o, str(dosya), i + 1, True) for i, o in enumerate(nesne)
        ]
    return [
        Belge(
            belge_id=dosya.stem,
            metin=metin,
            dosya=str(dosya),
            satir=1,
            yapilandirilmis=False,
        )
    ]


def oku_yol(yol: str) -> tuple[list[Belge], list[str]]:
    """Dosya veya dizini okur; (belgeler, uyarılar) döndürür.

    Tek dosya hedeflenmişse okuma/ayrıştırma hatası OkumaHatasi olarak
    yükselir (çıkış kodu 2). Dizin modunda bozuk dosyalar uyarıyla atlanır.
    """
    hedef = pathlib.Path(yol)
    if not hedef.exists():
        raise OkumaHatasi(f"yol bulunamadı: {yol}")
    belgeler: list[Belge] = []
    uyarilar: list[str] = []
    if hedef.is_file():
        if hedef.suffix.lower() not in DESTEKLENEN_UZANTILAR:
            raise OkumaHatasi(f"desteklenmeyen uzantı: {hedef.suffix}")
        try:
            belgeler = _dosya_belgeleri(hedef)
        except OkumaHatasi:
            raise
        except (OSError, UnicodeDecodeError) as hata:
            raise OkumaHatasi(f"dosya okunamadı: {hata}") from hata
    else:
        dosyalar = sorted(
            p
            for p in hedef.rglob("*")
            if p.is_file()
            and p.suffix.lower() in DESTEKLENEN_UZANTILAR
            and not any(parca in ATLANAN_DIZINLER for parca in p.parts)
        )
        for dosya in dosyalar:
            try:
                belgeler.extend(_dosya_belgeleri(dosya))
            except OkumaHatasi as hata:
                uyarilar.append(f"{dosya.name} atlandı: {hata}")
            except (OSError, UnicodeDecodeError) as hata:
                uyarilar.append(f"{dosya.name} atlandı (okunamadı: {hata})")
        if not belgeler and not uyarilar:
            uyarilar.append(
                "desteklenen uzantıda (.jsonl/.json/.md/.txt) dosya bulunamadı"
            )
    return belgeler, uyarilar
