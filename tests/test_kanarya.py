import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kanaryatara.kanarya import (
    baseline_yukle,
    kanarya_yukle,
    karsilastir,
    kayit_yukle,
    kosinus,
)


def kanarya(kanarya_id="kan-1", vektor=(1.0, 0.0), probe="soru?"):
    from kanaryatara.modeller import KanaryaTanimi

    return KanaryaTanimi(kanarya_id=kanarya_id, vektor=vektor, probe=probe, konu="konu")


def kayit(kanarya_id="kan-1", vektor=(1.0, 0.0), model="m1", top_k=("d1",)):
    from kanaryatara.modeller import KayitSatiri

    return KayitSatiri(
        kanarya_id=kanarya_id, vektor=vektor, model_parmagi=model, top_k=top_k
    )


class KanaryaTesti(unittest.TestCase):
    def test_kanarya_yukle_gecerli(self):
        with tempfile.TemporaryDirectory() as dizin:
            yol = Path(dizin) / "k.json"
            yol.write_text(
                json.dumps(
                    {
                        "kanaryalar": [
                            {"kanarya_id": "k1", "probe": "p", "vektor": [1, 0]}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            kanaryalar = kanarya_yukle(str(yol))
            self.assertEqual(len(kanaryalar), 1)
            self.assertEqual(kanaryalar[0].kanarya_id, "k1")

    def test_kanarya_eksik_probe_hata(self):
        with tempfile.TemporaryDirectory() as dizin:
            yol = Path(dizin) / "k.json"
            yol.write_text(
                json.dumps({"kanaryalar": [{"kanarya_id": "k1", "vektor": [1]}]}),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                kanarya_yukle(str(yol))

    def test_kanarya_yinelenen_kimlik_hata(self):
        with tempfile.TemporaryDirectory() as dizin:
            yol = Path(dizin) / "k.json"
            yol.write_text(
                json.dumps(
                    {
                        "kanaryalar": [
                            {"kanarya_id": "K1", "probe": "p", "vektor": [1]},
                            {"kanarya_id": "k1", "probe": "q", "vektor": [1]},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                kanarya_yukle(str(yol))

    def test_baseline_yukle(self):
        with tempfile.TemporaryDirectory() as dizin:
            yol = Path(dizin) / "b.json"
            yol.write_text(
                json.dumps({"model_parmagi": "m1", "vektorler": {"k1": [1, 0]}}),
                encoding="utf-8",
            )
            model, vektorler = baseline_yukle(str(yol))
            self.assertEqual(model, "m1")
            self.assertEqual(vektorler["k1"], (1.0, 0.0))

    def test_baseline_eksik_parmagi_hata(self):
        with tempfile.TemporaryDirectory() as dizin:
            yol = Path(dizin) / "b.json"
            yol.write_text(json.dumps({"vektorler": {"k1": [1]}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                baseline_yukle(str(yol))

    def test_baseline_vektor_eksik_kritik_bulgu(self):
        bulgular, _ = karsilastir([kanarya()], "m1", {"başka": (1.0, 0.0)}, [kayit()])
        self.assertEqual(len(bulgular), 1)
        self.assertEqual(bulgular[0].sinyal, "temel_vektor_eksik")
        self.assertEqual(bulgular[0].seviye, "kritik")

    def test_kimlik_eslesmesi_buyuk_kucuk_harf_duyarsiz(self):
        bulgular, _ = karsilastir(
            [kanarya("Kan-1")], "m1", {"kan-1": (1.0, 0.0)}, [kayit("KAN-1")]
        )
        self.assertEqual(bulgular, [])

    def test_kayit_bozuk_satir_hata(self):
        with tempfile.TemporaryDirectory() as dizin:
            yol = Path(dizin) / "kayit.jsonl"
            yol.write_text("bozuk satır\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                kayit_yukle(str(yol))

    def test_kosinus_birim(self):
        self.assertAlmostEqual(kosinus((1.0, 0.0), (1.0, 0.0)), 1.0)

    def test_kosinus_dik(self):
        self.assertEqual(kosinus((1.0, 0.0), (0.0, 1.0)), 0.0)

    def test_sapma_kritik(self):
        kanaryalar = [
            kanarya(f"kan-{i}", (float(i == 3), float(i != 3))) for i in range(1, 6)
        ]
        vektorler = {k.kanarya_id: k.vektor for k in kanaryalar}
        kayitlar = [
            kayit("kan-3", (0.6, 0.8)),
            kayit("kan-1"),
            kayit("kan-2"),
            kayit("kan-4"),
            kayit("kan-5"),
        ]
        bulgular, _ = karsilastir(kanaryalar, "m1", vektorler, kayitlar)
        eslesen = [b for b in bulgular if b.belge == "kan-3"]
        self.assertEqual(len(eslesen), 1)
        self.assertEqual(eslesen[0].seviye, "kritik")

    def test_model_degisti_bulgu(self):
        bulgular, uyarilar = karsilastir(
            [kanarya()], "m1", {"kan-1": (1.0, 0.0)}, [kayit(model="m2")]
        )
        self.assertEqual(len(bulgular), 1)
        self.assertEqual(bulgular[0].sinyal, "model_parmagi_degisti")
        self.assertEqual(bulgular[0].seviye, "kritik")
        self.assertTrue(any("parmak izi" in u for u in uyarilar))

    def test_kanarya_bulunamadi_az_ornek_orta(self):
        bulgular, _ = karsilastir([kanarya()], "m1", {"kan-1": (1.0, 0.0)}, [])
        self.assertEqual(len(bulgular), 1)
        self.assertEqual(bulgular[0].sinyal, "kanarya_bulunamadi")
        self.assertEqual(bulgular[0].seviye, "orta")
        self.assertEqual(bulgular[0].guven, "dusuk")

    def test_kanarya_bulunamadi_yeterli_ornek_yuksek(self):
        kanaryalar = [
            kanarya(f"kan-{i}", (float(i == 1), float(i != 1))) for i in range(1, 6)
        ]
        vektorler = {k.kanarya_id: k.vektor for k in kanaryalar}
        kayitlar = [
            kayit(f"kan-{i}", (float(i == 1), float(i != 1))) for i in range(2, 6)
        ]
        bulgular, _ = karsilastir(kanaryalar, "m1", vektorler, kayitlar)
        eslesen = [b for b in bulgular if b.sinyal == "kanarya_bulunamadi"]
        self.assertEqual(len(eslesen), 1)
        self.assertEqual(eslesen[0].seviye, "yuksek")

    def test_nan_vektor_reddedilir(self):
        with tempfile.TemporaryDirectory() as dizin:
            yol = Path(dizin) / "k.json"
            yol.write_text(
                '{"kanaryalar": [{"kanarya_id": "k1", "probe": "p", "vektor": [NaN]}]}',
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                kanarya_yukle(str(yol))

    def test_bool_vektor_reddedilir(self):
        with tempfile.TemporaryDirectory() as dizin:
            yol = Path(dizin) / "k.json"
            yol.write_text(
                '{"kanaryalar": [{"kanarya_id": "k1", "probe": "p", "vektor": [true]}]}',
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                kanarya_yukle(str(yol))

    def test_sapmali_oncesi_kayit_gizlenmez(self):
        kanaryalar = [
            kanarya(f"kan-{i}", (float(i == 3), float(i != 3))) for i in range(1, 6)
        ]
        vektorler = {k.kanarya_id: k.vektor for k in kanaryalar}
        kayitlar = [
            kayit("kan-3", (0.6, 0.8)),
            kayit("kan-3"),
            kayit("kan-1"),
            kayit("kan-2"),
            kayit("kan-4"),
            kayit("kan-5"),
        ]
        bulgular, _ = karsilastir(kanaryalar, "m1", vektorler, kayitlar)
        eslesen = [b for b in bulgular if b.belge == "kan-3"]
        self.assertEqual(len(eslesen), 1)
        self.assertEqual(eslesen[0].seviye, "kritik")

    def test_kayit_buyuk_dosya_reddedilir(self):
        with mock.patch("kanaryatara.kanarya.MAKS_KAYIT_BOYUT", 20):
            with tempfile.TemporaryDirectory() as dizin:
                yol = Path(dizin) / "kayit.jsonl"
                yol.write_text(
                    '{"kanarya_id": "k1", "model_parmagi": "m1", "vektor": [1, 0]}\n',
                    encoding="utf-8",
                )
                with self.assertRaises(ValueError):
                    kayit_yukle(str(yol))

    def test_az_ornek_guven_dusuk(self):
        bulgular, uyarilar = karsilastir(
            [kanarya("kan-1", (0.0, 1.0))],
            "m1",
            {"kan-1": (0.0, 1.0)},
            [kayit("kan-1", (1.0, 0.0))],
        )
        self.assertTrue(any("örnek" in u for u in uyarilar))
        self.assertEqual(len(bulgular), 1)
        self.assertEqual(bulgular[0].guven, "dusuk")
        self.assertEqual(bulgular[0].seviye, "orta")

    def test_boyut_uyusmazligi_uyari(self):
        bulgular, uyarilar = karsilastir(
            [kanarya("kan-1", (0.0, 1.0, 0.0))],
            "m1",
            {"kan-1": (0.0, 1.0, 0.0)},
            [kayit("kan-1", (0.0, 1.0))],
        )
        self.assertEqual(len(bulgular), 1)
        self.assertEqual(bulgular[0].sinyal, "vektor_boyutu_uyusmazligi")
        self.assertEqual(bulgular[0].seviye, "kritik")
        self.assertTrue(any("boyutu uyuşmuyor" in u for u in uyarilar))

    def test_kanarya_temel_boyutu_uyusmazligi(self):
        bulgular, _ = karsilastir(
            [kanarya("kan-1", (1.0, 0.0))],
            "m1",
            {"kan-1": (1.0,)},
            [kayit("kan-1", (1.0, 0.0))],
        )
        self.assertEqual(len(bulgular), 1)
        self.assertEqual(bulgular[0].sinyal, "kanarya_temel_boyutu_uyusmazligi")
        self.assertEqual(bulgular[0].seviye, "kritik")

    def test_top_k_bozuk_hata(self):
        with tempfile.TemporaryDirectory() as dizin:
            yol = Path(dizin) / "kayit.jsonl"
            yol.write_text(
                '{"kanarya_id": "k1", "model_parmagi": "m1", "vektor": [1, 0], "top_k": [1]}\n',
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                kayit_yukle(str(yol))

    def test_esik_alti_sapma_sessiz(self):
        bulgular, _ = karsilastir(
            [kanarya()], "m1", {"kan-1": (1.0, 0.0)}, [kayit("kan-1", (0.999, 0.001))]
        )
        self.assertEqual(bulgular, [])


if __name__ == "__main__":
    unittest.main()
