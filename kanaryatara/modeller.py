from dataclasses import dataclass


SEVIYELER = {"dusuk": 1, "orta": 2, "yuksek": 3, "kritik": 4}

KURALLAR = {
    "KNT01": ("dusuk", "Belgede talimat benzeri içerik bulundu."),
    "KNT02": ("orta", "Görünmez Unicode karakteri veya gizlenmiş HTML bulundu."),
    "KNT03": ("orta", "Doğrulanamayan otorite imzası veya tarih anomalisi."),
    "KNT04": ("dusuk", "Dış kaynaklı Markdown görseli veya bağlantısı."),
    "KNT05": ("dusuk", "Metadata eksikliği veya kimlik çakışması."),
    "KNT06": ("orta", "Yakın-kopya belge kümesi."),
    "KNT07": ("orta", "Kanarya vektöründe anlamlı sapma."),
}


@dataclass(frozen=True)
class Bulgu:
    kural: str
    seviye: str
    belge: str
    dosya: str
    satir: int
    sinyal: str
    guven: str
    kanit: str
    aciklama: str
    oneri: str


@dataclass(frozen=True)
class KanaryaTanimi:
    kanarya_id: str
    vektor: tuple[float, ...]
    probe: str
    konu: str


@dataclass(frozen=True)
class KayitSatiri:
    kanarya_id: str
    vektor: tuple[float, ...]
    model_parmagi: str
    top_k: tuple[str, ...]
