import json

from . import __version__
from .modeller import SEVIYELER, Bulgu


def esik_asildi(bulgular: list[Bulgu], esik: str) -> bool:
    sinir = SEVIYELER[esik]
    return any(SEVIYELER[b.seviye] >= sinir for b in bulgular)


def raporla(
    bulgular: list[Bulgu],
    bicim: str,
    sayi_etiket: str,
    esik: str,
    uyarilar: tuple[str, ...] = (),
) -> str:
    if bicim == "json":
        return json.dumps(
            {
                "arac": "KanaryaTara",
                "surum": __version__,
                "esik": esik,
                "bulgu_sayisi": len(bulgular),
                "uyarilar": list(uyarilar),
                "bulgular": [
                    {
                        "kural": b.kural,
                        "seviye": b.seviye,
                        "belge": b.belge,
                        "dosya": b.dosya,
                        "satir": b.satir,
                        "sinyal": b.sinyal,
                        "guven": b.guven,
                        "kanit": b.kanit,
                        "aciklama": b.aciklama,
                        "oneri": b.oneri,
                    }
                    for b in bulgular
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    satirlar = [f"KanaryaTara: {sayi_etiket}, {len(bulgular)} bulgu."]
    for bulgu in bulgular:
        yer = bulgu.dosya if bulgu.dosya else bulgu.belge
        if bulgu.satir:
            yer = f"{yer}:{bulgu.satir}"
        if bulgu.dosya:
            yer = f"{yer} ({bulgu.belge})"
        satirlar.append(
            f"[{bulgu.seviye.capitalize()}] {bulgu.kural} {yer}: {bulgu.aciklama}"
        )
        if bulgu.kanit:
            satirlar.append(f"  Kanıt: {bulgu.kanit}")
        satirlar.append(f"  Güven: {bulgu.guven}")
        satirlar.append(f"  Öneri: {bulgu.oneri}")
    if esik_asildi(bulgular, esik):
        satirlar.append("Risk eşiğine ulaşıldı.")
    return "\n".join(satirlar)
