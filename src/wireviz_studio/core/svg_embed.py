# -*- coding: utf-8 -*-

import base64
import re
from pathlib import Path
from typing import Union

mime_subtype_replacements = {"jpg": "jpeg", "tif": "tiff"}


# TODO: Share cache and code between data_URI_base64() and embed_svg_images()
def data_URI_base64(file: Union[str, Path], media: str = "image") -> str:
    """Return Base64-encoded data URI of input file."""
    file_path = Path(file)
    base64_data = base64.b64encode(file_path.read_bytes()).decode("utf-8")
    data_uri = f"data:{media}/{get_mime_subtype(file_path)};base64, {base64_data}"
    # print(f"data_URI_base64('{file}', '{media}') -> {len(uri)}-character URI")
    if len(data_uri) > 65535:
        print(
            "data_URI_base64(): Warning: Browsers might have different URI length limitations"
        )
    return data_uri


def embed_svg_images(svg_in: str, base_path: Union[str, Path] = Path.cwd()) -> str:
    image_cache = {}  # cache of base64-encoded images

    def image_tag(pre: str, url: str, post: str) -> str:
        return f'<image{pre} xlink:href="{url}"{post}>'

    def replace(match: re.Match) -> str:
        image_url = match["URL"]
        if image_url not in image_cache:  # only encode/cache every unique URL once
            absolute_image_path = (Path(base_path) / image_url).resolve()
            image_bytes = absolute_image_path.read_bytes()
            image_cache[image_url] = base64.b64encode(image_bytes).decode("utf-8")
        return image_tag(
            match["PRE"] or "",
            f"data:image/{get_mime_subtype(image_url)};base64, {image_cache[image_url]}",
            match["POST"] or "",
        )

    pattern = re.compile(
        image_tag(r"(?P<PRE> [^>]*?)?", r'(?P<URL>[^"]*?)', r"(?P<POST> [^>]*?)?"),
        re.IGNORECASE,
    )
    return pattern.sub(replace, svg_in)


def get_mime_subtype(filename: Union[str, Path]) -> str:
    mime_subtype = Path(filename).suffix.lstrip(".").lower()
    if mime_subtype in mime_subtype_replacements:
        mime_subtype = mime_subtype_replacements[mime_subtype]
    return mime_subtype


def embed_svg_images_file(
    filename_in: Union[str, Path], overwrite: bool = True
) -> None:
    filename_in = Path(filename_in).resolve()
    filename_out = filename_in.with_suffix(".b64.svg")
    filename_out.write_text(  # TODO?: Verify xml encoding="utf-8" in SVG?
        embed_svg_images(filename_in.read_text(), filename_in.parent)
    )  # TODO: Use encoding="utf-8" in both read_text() and write_text()
    if overwrite:
        filename_out.replace(filename_in)
