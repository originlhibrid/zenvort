import io
import zipfile
from pathlib import Path
from typing import Any

import fitz
import pikepdf
from pikepdf import Pdf, Name, Dictionary


def merge_pdfs(input_paths: list[str], output_path: str) -> None:
    dst = Pdf.new()
    for path in input_paths:
        src = Pdf.open(path)
        dst.pages.extend(src.pages)
        src.close()
    dst.save(output_path, compress_streams=True, object_stream_mode=pikepdf.Save.OBJECT_STREAM_VERSION_4)


def split_pdf(input_path: str, output_path: str, pages: str) -> None:
    pdf = Pdf.open(input_path)
    total = len(pdf.pages)

    ranges = _parse_page_ranges(pages, total)
    if len(ranges) == 1:
        start, end = ranges[0]
        _extract_range(pdf, output_path, start, end)
    else:
        import tempfile
        import shutil
        tmp_dir = Path(tempfile.mkdtemp())
        try:
            for i, (start, end) in enumerate(ranges):
                out = tmp_dir / f"part_{i+1}.pdf"
                _extract_range(pdf, str(out), start, end)
            zip_path = output_path.replace(".pdf", ".zip")
            with zipfile.ZipFile(zip_path, "w") as zf:
                for p in tmp_dir.glob("part_*.pdf"):
                    zf.write(p, p.name)
            if Path(zip_path).stat().st_size == 0:
                raise RuntimeError("zip creation failed")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def _extract_range(pdf: Pdf, output_path: str, start: int, end: int) -> None:
    dst = Pdf.new()
    for idx in range(start - 1, end):
        dst.pages.append(pdf.pages[idx])
    dst.save(output_path, compress_streams=True, object_stream_mode=pikepdf.Save.OBJECT_STREAM_VERSION_4)


def _parse_page_ranges(pages: str, total: int) -> list[tuple[int, int]]:
    result = []
    for part in pages.split(","):
        part = part.strip()
        try:
            if "-" in part:
                start, end = part.split("-", 1)
                start, end = int(start.strip()), int(end.strip())
                if end == -1 or end > total:
                    end = total
            else:
                start = int(part)
                end = start
        except ValueError:
            raise ValueError("Invalid page range format. Use format like: 1-3,5,7-9")
        if start < 1:
            start = 1
        if end > total:
            end = total
        result.append((start, end))
    return result


def rotate_pdf(input_path: str, output_path: str, degrees: int, pages: str | None = None) -> None:
    doc = fitz.open(input_path)
    total = len(doc)

    if pages:
        targets = _parse_page_targets(pages, total)
    else:
        targets = list(range(total))

    rotation_map = {90: 90, 180: 180, 270: 270}
    rotation = rotation_map.get(degrees, 90)

    for idx in targets:
        page = doc[idx]
        page.set_rotation(rotation)

    doc.save(output_path, deflate=True, garbage=4, clean=True)
    doc.close()


def _parse_page_targets(pages: str, total: int) -> list[int]:
    result = []
    for part in pages.split(","):
        part = part.strip()
        try:
            if "-" in part:
                start, end = part.split("-", 1)
                start, end = int(start.strip()), int(end.strip())
                if end == -1 or end > total:
                    end = total
                for p in range(start, end + 1):
                    result.append(p - 1)
            else:
                result.append(int(part) - 1)
        except ValueError:
            raise ValueError("Invalid page range format. Use format like: 1-3,5,7-9")
    return [p for p in result if 0 <= p < total]


def watermark_pdf(
    input_path: str,
    output_path: str,
    text: str,
    opacity: float = 0.3,
    font_size: int = 48,
    color: str = "#FF0000",
    angle: int = 45,
) -> None:
    doc = fitz.open(input_path)

    rgb_color = _hex_to_rgb(color)

    for page in doc:
        w = page.rect.width
        h = page.rect.height

        text_point = fitz.Point(50, h / 2)

        page.insert_text(
            text_point,
            text,
            font_size=font_size,
            color=rgb_color,
            opacity=opacity,
            rotate=angle,
        )

    doc.save(output_path, deflate=True, garbage=4, clean=True)
    doc.close()


def _hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        return (r, g, b)
    return (1.0, 0.0, 0.0)


def stamp_pdf(
    input_path: str,
    output_path: str,
    stamp_path: str,
    position: str = "bottom-right",
    scale: float = 0.2,
) -> None:
    doc = fitz.open(input_path)
    stamp_img = fitz.open(stamp_path)

    stamp_page = stamp_img[0]
    stamp_w = stamp_page.rect.width
    stamp_h = stamp_page.rect.height

    for page in doc:
        pw, ph = page.rect.width, page.rect.height

        s_w = pw * scale
        s_h = ph * scale
        ratio = min(s_w / stamp_w, s_h / stamp_h)
        s_w = stamp_w * ratio
        s_h = stamp_h * ratio

        positions = {
            "top-left": fitz.Point(10, 10),
            "top-right": fitz.Point(pw - s_w - 10, 10),
            "bottom-left": fitz.Point(10, ph - s_h - 10),
            "bottom-right": fitz.Point(pw - s_w - 10, ph - s_h - 10),
            "center": fitz.Point((pw - s_w) / 2, (ph - s_h) / 2),
        }
        pos = positions.get(position, positions["bottom-right"])

        img_rect = fitz.Rect(pos.x, pos.y, pos.x + s_w, pos.y + s_h)
        page.insert_image(img_rect, filename=stamp_path)

    doc.save(output_path, deflate=True, garbage=4, clean=True)
    doc.close()


def encrypt_pdf(
    input_path: str,
    output_path: str,
    password: str,
    owner_password: str | None = None,
    permissions: str | None = None,
) -> None:
    pdf = Pdf.open(input_path)

    if pdf.is_encrypted:
        try:
            pdf.remove_password(password)
        except Exception:
            pass

    if owner_password is None:
        owner_password = password

    perm = pikepdf.Permissions.all
    if permissions:
        perm = _parse_permissions(permissions)

    pdf.save(
        output_path,
        encryption=pikepdf.Encryption(user=password, owner=owner_password, R=6, allow=perm),
        compress_streams=True,
        object_stream_mode=pikepdf.Save.OBJECT_STREAM_VERSION_4,
    )


def _parse_permissions(perm_str: str) -> pikepdf.Permissions:
    perms = set()
    for p in perm_str.split(","):
        p = p.strip().lower()
        if p == "print":
            perms.add(pikepdf.Permissions.print)
        elif p == "copy":
            perms.add(pikepdf.Permissions.copy)
        elif p == "edit":
            perms.add(pikepdf.Permissions.modify)
    if not perms:
        return pikepdf.Permissions.all
    return pikepdf.Permissions(*perms)


def decrypt_pdf(input_path: str, output_path: str, password: str) -> None:
    pdf = Pdf.open(input_path)

    if not pdf.is_encrypted:
        Path(output_path).write_bytes(Path(input_path).read_bytes())
        return

    try:
        pdf.remove_password(password)
    except pikepdf.PasswordError:
        raise ValueError("Incorrect password")
    except Exception as e:
        raise RuntimeError(f"Decryption failed: {e}")

    pdf.save(
        output_path,
        compress_streams=True,
        object_stream_mode=pikepdf.Save.OBJECT_STREAM_VERSION_4,
    )


def compress_pdf(input_path: str, output_path: str, quality: str = "medium") -> None:
    dpi_map = {"low": 72, "medium": 150, "high": 300}
    dpi = dpi_map.get(quality, 150)

    doc = fitz.open(input_path)
    for page in doc:
        for annot in page.annot_xrefs():
            page.delete_annot(annot)

    doc.save(output_path, deflate=True, garbage=4, clean=True)
    doc.close()


def read_metadata(input_path: str) -> dict[str, Any]:
    doc = fitz.open(input_path)
    meta = doc.metadata
    doc.close()
    return {
        "title": meta.get("title", ""),
        "author": meta.get("author", ""),
        "subject": meta.get("subject", ""),
        "keywords": meta.get("keywords", ""),
        "creator": meta.get("creator", ""),
    }


def write_metadata(input_path: str, output_path: str, metadata: dict[str, Any]) -> dict[str, Any]:
    doc = fitz.open(input_path)
    meta = doc.metadata

    for key in ("title", "author", "subject", "keywords", "creator"):
        if key in metadata:
            meta[key] = metadata[key]

    doc.set_metadata(meta)
    doc.save(output_path, deflate=True, garbage=4, clean=True)
    doc.close()
    return read_metadata(output_path)


def get_bookmarks(input_path: str) -> list[dict[str, Any]]:
    doc = fitz.open(input_path)
    toc = doc.get_toc()
    doc.close()

    bookmarks = []
    for item in toc:
        if len(item) >= 2:
            title = item[1] if isinstance(item[1], str) else ""
            page_num = item[0] if isinstance(item[0], int) else 1
            bookmarks.append({"title": title, "page": page_num})
    return bookmarks


def write_bookmarks(input_path: str, output_path: str, bookmarks: list[dict[str, Any]]) -> None:
    doc = fitz.open(input_path)

    toc = []
    for bm in bookmarks:
        page = bm.get("page", 1)
        title = bm.get("title", "")
        toc.append([1, title, page])

    doc.set_toc(toc)
    doc.save(output_path, deflate=True, garbage=4, clean=True)
    doc.close()


def flatten_pdf(input_path: str, output_path: str) -> None:
    doc = fitz.open(input_path)

    for page in doc:
        for annot in list(page.annots() or []):
            page.delete_annot(annot)

        for widget in list(page.widgets() or []):
            widget.field_name = ""

    doc.save(output_path, deflate=True, garbage=4, clean=True)
    doc.close()


def convert_to_pdfa(input_path: str, output_path: str, standard: str = "PDF/A-2b") -> None:
    import httpx
    from app.config import get_settings

    with open(input_path, "rb") as f:
        file_bytes = f.read()

    with httpx.Client(timeout=httpx.Timeout(120.0, connect=5.0)) as client:
        response = client.post(
            f"{get_settings().GOTENBERG_URL}/forms/pdfengines/convert",
            files=[("files", ("input.pdf", file_bytes, "application/pdf"))],
            data={"standard": standard},
        )

    if response.status_code != 200:
        raise RuntimeError(f"Gotenberg PDF/A conversion failed: {response.text[:500]}")

    with open(output_path, "wb") as f:
        for chunk in response.iter_bytes(chunk_size=8192):
            f.write(chunk)
