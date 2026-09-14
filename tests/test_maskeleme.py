import unittest

from kanaryatara.maskeleme import maskele, url_maskele


class MaskelemeTesti(unittest.TestCase):
    def test_kisa_deger(self):
        self.assertEqual(maskele("abc"), "ab***")

    def test_cok_kisa_deger_tam_maskeli(self):
        self.assertEqual(maskele("m1"), "***")

    def test_orta_deger(self):
        self.assertEqual(maskele("abcdefghijkl"), "abcd***")

    def test_uzun_deger(self):
        self.assertEqual(maskele("abcdefghijklmnopqrst"), "abcdef***rst")

    def test_bos_deger(self):
        self.assertEqual(maskele(""), "—")

    def test_url_yolu_gizlenir(self):
        self.assertEqual(
            url_maskele("https://izleme.example.com/istatistik?id=abc123"),
            "https://izleme.example.com/***",
        )

    def test_url_kimlik_bilgileri_gizlenir(self):
        self.assertEqual(
            url_maskele("https://kullanici:sifre@example.com/ozel"),
            "https://example.com/***",
        )

    def test_tehlikeli_url_gizlenir(self):
        self.assertEqual(url_maskele("javascript:alert('gizli')"), "javascript:***")

    def test_data_uri(self):
        self.assertEqual(url_maskele("data:text/plain;base64,AAA"), "data:***")

    def test_basit_metin(self):
        self.assertEqual(url_maskele("düz metin"), "düz ***")


if __name__ == "__main__":
    unittest.main()
