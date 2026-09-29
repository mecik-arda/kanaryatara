import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kanaryatara.cli import ana

ORNEKLER = Path(__file__).resolve().parent.parent / "ornekler"


class CliTesti(unittest.TestCase):
    def test_tara_temiz_sifir(self):
        with contextlib.redirect_stdout(io.StringIO()):
            kod = ana(["tara", str(ORNEKLER / "temiz.jsonl")])
        self.assertEqual(kod, 0)

    def test_tara_riskli_bir(self):
        with contextlib.redirect_stdout(io.StringIO()):
            kod = ana(["tara", str(ORNEKLER / "riskli.jsonl")])
        self.assertEqual(kod, 1)

    def test_tara_riskli_esik_kritik_sifir(self):
        with contextlib.redirect_stdout(io.StringIO()):
            kod = ana(["tara", str(ORNEKLER / "riskli.jsonl"), "--esik", "kritik"])
        self.assertEqual(kod, 0)

    def test_tara_json_semasi(self):
        tampon = io.StringIO()
        with contextlib.redirect_stdout(tampon):
            ana(["tara", str(ORNEKLER / "riskli.jsonl"), "--bicim", "json"])
        veri = json.loads(tampon.getvalue())
        self.assertEqual(veri["arac"], "KanaryaTara")
        self.assertIn("bulgular", veri)
        self.assertIn("uyarilar", veri)
        self.assertEqual(veri["esik"], "yuksek")

    def test_tara_md_riskli(self):
        with contextlib.redirect_stdout(io.StringIO()):
            kod = ana(["tara", str(ORNEKLER / "riskli.md")])
        self.assertEqual(kod, 1)

    def test_tara_yol_yok_iki(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with contextlib.redirect_stdout(io.StringIO()):
                kod = ana(["tara", "bu/yol/yok"])
        self.assertEqual(kod, 2)

    def test_tara_atlanan_dosya_iki(self):
        with tempfile.TemporaryDirectory() as dizin:
            kok = Path(dizin)
            (kok / "iyi.jsonl").write_text(
                '{"belge_id": "b1", "metin": "temiz", "kaynak": "ic"}\n',
                encoding="utf-8",
            )
            (kok / "bozuk.jsonl").write_text("bozuk\n", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                with contextlib.redirect_stdout(io.StringIO()):
                    kod = ana(["tara", str(kok)])
        self.assertEqual(kod, 2)

    def test_tara_knt06_kipatilmasi_sifir(self):
        with tempfile.TemporaryDirectory() as dizin:
            kok = Path(dizin)
            for i in range(501):
                (kok / f"d{i}.jsonl").write_text(
                    f'{{"belge_id": "d{i}", "metin": "kısa metin", "kaynak": "ic"}}\n',
                    encoding="utf-8",
                )
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                with contextlib.redirect_stdout(io.StringIO()):
                    kod = ana(["tara", str(kok)])
        self.assertEqual(kod, 0)
        self.assertIn("KNT06 atlandı", stderr.getvalue())

    def test_karsilastir_kritik_bir(self):
        with contextlib.redirect_stdout(io.StringIO()):
            kod = ana(
                [
                    "karsilastir",
                    "--kanarya",
                    str(ORNEKLER / "kanarya.json"),
                    "--baseline",
                    str(ORNEKLER / "baseline.json"),
                    "--kayit",
                    str(ORNEKLER / "kayit.jsonl"),
                ]
            )
        self.assertEqual(kod, 1)

    def test_karsilastir_model_farki_bir(self):
        with tempfile.TemporaryDirectory() as dizin:
            kayit_yolu = Path(dizin) / "kayit.jsonl"
            kayit_yolu.write_text(
                '{"kanarya_id": "kan-1", "model_parmagi": "yeni-model", "top_k": ["d1"], "vektor": [1, 0, 0, 0]}\n',
                encoding="utf-8",
            )
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                with contextlib.redirect_stdout(io.StringIO()):
                    kod = ana(
                        [
                            "karsilastir",
                            "--kanarya",
                            str(ORNEKLER / "kanarya.json"),
                            "--baseline",
                            str(ORNEKLER / "baseline.json"),
                            "--kayit",
                            str(kayit_yolu),
                        ]
                    )
        self.assertEqual(kod, 1)
        self.assertIn("parmak izi", stderr.getvalue())

    def test_karsilastir_tum_boyut_uyusmazligi_bir(self):
        with tempfile.TemporaryDirectory() as dizin:
            kayit_yolu = Path(dizin) / "kayit.jsonl"
            kayit_yolu.write_text(
                '{"kanarya_id": "kan-1", "model_parmagi": "tr-embed-v1", "top_k": ["d1"], "vektor": [1, 0]}\n',
                encoding="utf-8",
            )
            with contextlib.redirect_stderr(io.StringIO()):
                with contextlib.redirect_stdout(io.StringIO()):
                    kod = ana(
                        [
                            "karsilastir",
                            "--kanarya",
                            str(ORNEKLER / "kanarya.json"),
                            "--baseline",
                            str(ORNEKLER / "baseline.json"),
                            "--kayit",
                            str(kayit_yolu),
                        ]
                    )
        self.assertEqual(kod, 1)

    def test_gecersiz_secenek_iki(self):
        with self.assertRaises(SystemExit) as cikis:
            with contextlib.redirect_stderr(io.StringIO()):
                ana(["tara", "--boyle-bir-secenek-yok"])
        self.assertEqual(cikis.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
