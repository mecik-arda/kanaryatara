import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kanaryatara import belge


class BelgeTesti(unittest.TestCase):
    def test_jsonl_okunur(self):
        with tempfile.TemporaryDirectory() as dizin:
            yol = Path(dizin) / "ornek.jsonl"
            yol.write_text(
                json.dumps(
                    {"belge_id": "a1", "metin": "merhaba", "kaynak": "ic"},
                    ensure_ascii=False,
                )
                + "\n"
                + json.dumps({"belge_id": "a2", "metin": "dünya"}, ensure_ascii=False)
                + "\n",
                encoding="utf-8",
            )
            belgeler, uyarilar = belge.oku_yol(str(yol))
            self.assertEqual(len(belgeler), 2)
            self.assertEqual(belgeler[0].belge_id, "a1")
            self.assertTrue(belgeler[0].yapilandirilmis)
            self.assertEqual(uyarilar, [])

    def test_tek_dosya_bozuk_satir_hata(self):
        with tempfile.TemporaryDirectory() as dizin:
            yol = Path(dizin) / "bozuk.jsonl"
            yol.write_text("bu json değil\n", encoding="utf-8")
            with self.assertRaises(belge.OkumaHatasi):
                belge.oku_yol(str(yol))

    def test_dizin_bozuk_dosya_uyari(self):
        with tempfile.TemporaryDirectory() as dizin:
            kok = Path(dizin)
            (kok / "iyi.jsonl").write_text(
                json.dumps({"belge_id": "b1", "metin": "iyi"}, ensure_ascii=False),
                encoding="utf-8",
            )
            (kok / "bozuk.jsonl").write_text("çöp satır\n", encoding="utf-8")
            belgeler, uyarilar = belge.oku_yol(dizin)
            self.assertEqual(len(belgeler), 1)
            self.assertTrue(any("bozuk.jsonl" in u for u in uyarilar))

    def test_desteklenmeyen_uzanti(self):
        with tempfile.TemporaryDirectory() as dizin:
            (Path(dizin) / "a.py").write_text("print(1)", encoding="utf-8")
            belgeler, uyarilar = belge.oku_yol(dizin)
            self.assertEqual(belgeler, [])
            self.assertTrue(uyarilar)

    def test_yol_yok(self):
        with self.assertRaises(belge.OkumaHatasi):
            belge.oku_yol("bu/yol/yok")

    def test_buyuk_dosya_atlanir(self):
        with mock.patch.object(belge, "MAKS_BOYUT", 10):
            with tempfile.TemporaryDirectory() as dizin:
                (Path(dizin) / "buyuk.jsonl").write_text(
                    json.dumps(
                        {"belge_id": "x", "metin": "uzun uzun uzun"}, ensure_ascii=False
                    ),
                    encoding="utf-8",
                )
                belgeler, uyarilar = belge.oku_yol(dizin)
                self.assertEqual(belgeler, [])
                self.assertTrue(any("buyuk.jsonl" in u for u in uyarilar))

    def test_md_duz_metin(self):
        with tempfile.TemporaryDirectory() as dizin:
            yol = Path(dizin) / "not.md"
            yol.write_text("# Başlık\nmetin", encoding="utf-8")
            belgeler, _ = belge.oku_yol(str(yol))
            self.assertEqual(len(belgeler), 1)
            self.assertFalse(belgeler[0].yapilandirilmis)

    def test_bomlu_md_sessiz(self):
        with tempfile.TemporaryDirectory() as dizin:
            yol = Path(dizin) / "bomlu.md"
            yol.write_bytes(b"\xef\xbb\xbf# Baslik\nnormal metin")
            belgeler, uyarilar = belge.oku_yol(str(yol))
            self.assertEqual(len(belgeler), 1)
            self.assertNotIn("\ufeff", belgeler[0].metin)
            self.assertEqual(uyarilar, [])

    def test_eksik_metin_alani_hata(self):
        with tempfile.TemporaryDirectory() as dizin:
            yol = Path(dizin) / "eksik.jsonl"
            yol.write_text('{"belge_id": "x"}\n', encoding="utf-8")
            with self.assertRaises(belge.OkumaHatasi):
                belge.oku_yol(str(yol))

    def test_kontrol_karakterli_kimlik_hata(self):
        with tempfile.TemporaryDirectory() as dizin:
            yol = Path(dizin) / "kontrol.jsonl"
            yol.write_text(
                '{"belge_id": "kötü\nkimlik", "metin": "x"}\n', encoding="utf-8"
            )
            with self.assertRaises(belge.OkumaHatasi):
                belge.oku_yol(str(yol))

    def test_json_dizisi_okunur(self):
        with tempfile.TemporaryDirectory() as dizin:
            yol = Path(dizin) / "ornek.json"
            yol.write_text(
                json.dumps(
                    [
                        {"belge_id": "j1", "metin": "ilk"},
                        {"belge_id": "j2", "metin": "iki"},
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            belgeler, _ = belge.oku_yol(str(yol))
            self.assertEqual([b.belge_id for b in belgeler], ["j1", "j2"])

    def test_bom_jsonl_okunur(self):
        with tempfile.TemporaryDirectory() as dizin:
            yol = Path(dizin) / "bom.jsonl"
            yol.write_bytes(
                b"\xef\xbb\xbf"
                + json.dumps(
                    {"belge_id": "b1", "metin": "metin"}, ensure_ascii=False
                ).encode("utf-8")
            )
            belgeler, uyarilar = belge.oku_yol(str(yol))
            self.assertEqual(len(belgeler), 1)
            self.assertEqual(uyarilar, [])

    def test_bos_jsonl_hata(self):
        with tempfile.TemporaryDirectory() as dizin:
            yol = Path(dizin) / "bos.jsonl"
            yol.write_text("", encoding="utf-8")
            with self.assertRaises(belge.OkumaHatasi):
                belge.oku_yol(str(yol))

    def test_bos_json_dizin_uyarisi(self):
        with tempfile.TemporaryDirectory() as dizin:
            (Path(dizin) / "bos.json").write_text("[]", encoding="utf-8")
            belgeler, uyarilar = belge.oku_yol(dizin)
            self.assertEqual(belgeler, [])
            self.assertTrue(any("bos.json" in u for u in uyarilar))

    def test_dizin_bos_jsonl_uyarisi(self):
        with tempfile.TemporaryDirectory() as dizin:
            (Path(dizin) / "bos.jsonl").write_text("", encoding="utf-8")
            belgeler, uyarilar = belge.oku_yol(dizin)
            self.assertEqual(belgeler, [])
            self.assertTrue(any("bos.jsonl" in u for u in uyarilar))


if __name__ == "__main__":
    unittest.main()
