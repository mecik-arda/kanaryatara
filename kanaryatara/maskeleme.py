from urllib.parse import urlsplit


def maskele(deger: str) -> str:
    """Kanıt metnini kısmen görünür bırakır; ham değer rapora yazılmaz."""
    if not deger:
        return "—"
    if len(deger) <= 8:
        return deger[:2] + "***"
    if len(deger) <= 16:
        return deger[:4] + "***"
    return deger[:6] + "***" + deger[-3:]


def url_maskele(url: str) -> str:
    """URL'de yalnızca şema ve alan adını bırakır; yol ve sorgu gizlenir."""
    try:
        parca = urlsplit(url)
    except ValueError:
        return maskele(url)
    if parca.scheme == "data":
        return "data:***"
    if not parca.scheme or not parca.netloc:
        return maskele(url)
    return f"{parca.scheme}://{parca.netloc}/***"
