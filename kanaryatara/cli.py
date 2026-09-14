import argparse
import sys

from .belge import oku_yol
from .kanarya import baseline_yukle, kanarya_yukle, karsilastir, kayit_yukle
from .kurallar import tara_belgeler
from .modeller import SEVIYELER
from .raporlama import esik_asildi, raporla


class TurkceAyrıştırıcı(argparse.ArgumentParser):
    def format_usage(self):
        return super().format_usage().replace("usage:", "Kullanım:", 1)

    def format_help(self):
        return super().format_help().replace("usage:", "Kullanım:", 1)

    def error(self, mesaj):
        self.print_usage(sys.stderr)
        self.exit(
            2, "Hata: Komut veya seçenekler geçersiz. Yardım için --help kullanın.\n"
        )


def _ortak_secenekler(ayrıştırıcı: argparse.ArgumentParser) -> None:
    ayrıştırıcı.add_argument(
        "--bicim", choices=["metin", "json"], default="metin", help="Rapor biçimi"
    )
    ayrıştırıcı.add_argument(
        "--esik",
        choices=list(SEVIYELER),
        default="yuksek",
        help="Başarısız çıkış için en düşük risk seviyesi",
    )


def ana(argumanlar: list[str] | None = None) -> int:
    ayrıştırıcı = TurkceAyrıştırıcı(
        prog="kanaryatara",
        description="KanaryaTara RAG bilgi tabanı bütünlük denetçisi",
        add_help=False,
    )
    ayrıştırıcı._positionals.title = "Komutlar"
    ayrıştırıcı._optionals.title = "Seçenekler"
    ayrıştırıcı.add_argument(
        "--help", "-h", action="help", help="Yardımı göster ve çık"
    )
    komutlar = ayrıştırıcı.add_subparsers(dest="komut", required=True)
    tara = komutlar.add_parser("tara", help="Belge koleksiyonunu tara", add_help=False)
    tara._positionals.title = "Girdiler"
    tara._optionals.title = "Seçenekler"
    tara.add_argument("--help", "-h", action="help", help="Yardımı göster ve çık")
    tara.add_argument("yol", metavar="YOL", help="Dosya veya dizin")
    _ortak_secenekler(tara)
    tara.add_argument(
        "--izinli-alan-adi",
        action="append",
        default=[],
        metavar="ALAN",
        help="KNT04'te bulgu üretmeyecek alan adı (tekrarlanabilir)",
    )
    karsilastir_komutu = komutlar.add_parser(
        "karsilastir",
        help="Kanarya vektörlerini temel çizgiyle karşılaştır",
        add_help=False,
    )
    karsilastir_komutu._positionals.title = "Seçenekler"
    karsilastir_komutu._optionals.title = "Seçenekler"
    karsilastir_komutu.add_argument(
        "--help", "-h", action="help", help="Yardımı göster ve çık"
    )
    karsilastir_komutu.add_argument(
        "--kanarya", required=True, metavar="DOSYA", help="Kanarya tanım dosyası (JSON)"
    )
    karsilastir_komutu.add_argument(
        "--baseline", required=True, metavar="DOSYA", help="Temel çizgi dosyası (JSON)"
    )
    karsilastir_komutu.add_argument(
        "--kayit", required=True, metavar="DOSYA", help="Ölçüm kayıt dosyası (JSONL)"
    )
    _ortak_secenekler(karsilastir_komutu)
    secenekler = ayrıştırıcı.parse_args(argumanlar)
    try:
        if secenekler.komut == "tara":
            belgeler, uyarilar = oku_yol(secenekler.yol)
            bulgular, ek_uyarilar = tara_belgeler(
                belgeler, tuple(secenekler.izinli_alan_adi)
            )
            uyarilar += ek_uyarilar
            sayi = f"{len(belgeler)} belge"
        else:
            kanaryalar = kanarya_yukle(secenekler.kanarya)
            model_parmagi, vektorler = baseline_yukle(secenekler.baseline)
            kayitlar = kayit_yukle(secenekler.kayit)
            bulgular, uyarilar = karsilastir(
                kanaryalar, model_parmagi, vektorler, kayitlar
            )
            sayi = f"{len(kanaryalar)} kanarya"
    except (ValueError, OSError) as hata:
        print(f"Hata: {hata}", file=sys.stderr)
        return 2
    for uyari in uyarilar:
        print(f"Uyarı: {uyari}", file=sys.stderr)
    print(raporla(bulgular, secenekler.bicim, sayi, secenekler.esik, tuple(uyarilar)))
    return int(esik_asildi(bulgular, secenekler.esik))


if __name__ == "__main__":
    sys.exit(ana())
