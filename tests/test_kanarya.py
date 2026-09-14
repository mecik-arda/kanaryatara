import json
import tempfile
import unittest
from pathlib import Path

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

    def test_model_degisti_uyari(self):
        bulgular, uyarilar = karsilastir(
            [kanarya()], "m1", {"kan-1": (1.0, 0.0)}, [kayit(model="m2")]
        )
        self.assertEqual(bulgular, [])
        self.assertTrue(any("parmak izi" in u for u in uyarilar))

    def test_kanarya_bulunamadi_yuksek(self):
        bulgular, _ = karsilastir([kanarya()], "m1", {"kan-1": (1.0, 0.0)}, [])
        self.assertEqual(len(bulgular), 1)
        self.assertEqual(bulgular[0].sinyal, "kanarya_bulunamadi")
        self.assertEqual(bulgular[0].seviye, "yuksek")

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
        self.assertEqual(bulgular, [])
        self.assertTrue(any("boyutu uyuşmuyor" in u for u in uyarilar))

    def test_esik_alti_sapma_sessiz(self):
        bulgular, _ = karsilastir(
            [kanarya()], "m1", {"kan-1": (1.0, 0.0)}, [kayit("kan-1", (0.999, 0.001))]
        )
        self.assertEqual(bulgular, [])


if __name__ == "__main__":
    unittest.main()
