"""Create the value-free viewer catalog from canonical JSON and prepared TIFFs.

Uses only the standard library. Normal publication builds validate/copy the
checked-in catalog; regeneration belongs to explicit source preparation.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tiff_layout(path):
    content = path.read_bytes()
    if content[:4] != b"II*\0":
        raise ValueError("Catalog preparation requires a little-endian classic TIFF")
    offset = struct.unpack_from("<I", content, 4)[0]
    count = struct.unpack_from("<H", content, offset)[0]
    tags = {}
    formats = {3: "H", 4: "I", 11: "f", 12: "d"}
    for index in range(count):
        tag, kind, size, pointer = struct.unpack_from("<HHII", content, offset+2+index*12)
        if kind not in formats:
            continue
        fmt = "<" + formats[kind]*size
        length = struct.calcsize(fmt)
        start = offset+2+index*12+8 if length <= 4 else pointer
        tags[tag] = list(struct.unpack_from(fmt, content, start))
    width, height = tags[256][0], tags[257][0]
    tiled = 324 in tags
    offsets, counts = tags[324 if tiled else 273], tags[325 if tiled else 279]
    bw, bh = (tags[322][0], tags[323][0]) if tiled else (width, tags.get(278, [height])[0])
    if len(offsets) != len(counts) or any(o+c > len(content) for o, c in zip(offsets, counts)):
        raise ValueError("Invalid prepared TIFF block layout")
    return dict(width=width, height=height, block_width=bw, block_height=bh,
                tiled=tiled, bits_per_sample=tags[258][0], sample_format=tags.get(339, [1])[0],
                compression=tags.get(259, [1])[0], predictor=tags.get(317, [1])[0],
                block_offsets=offsets, block_byte_counts=counts,
                pixel_scale=tags[33550], tiepoint=tags[33922])


def create_catalog(data_root):
    data = json.loads((data_root / "population.json").read_text(encoding="utf-8"))
    sources = []
    for layer in data["layers"]:
        identity = layer["metadata"]["id"]
        asset = data_root / "real" / (identity+".tif")
        layout = tiff_layout(asset)
        grid = {key: value for key, value in layer["grid"].items() if key != "values"}
        sx, sy, _ = layout.pop("pixel_scale")
        i, j, _, x, y, _ = layout.pop("tiepoint")
        if (layout["width"], layout["height"]) != (grid["width"], grid["height"]) or any(abs(a-b)>1e-12 for a,b in zip((sx, sy, x-i*sx, y+j*sy), (grid["dx"], grid["dy"], grid["west"], grid["north"]))):
            raise ValueError("Canonical JSON/TIFF geometry mismatch: " + identity)
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        if digest != layer["metadata"]["processing_receipt"]["output_sha256"]:
            raise ValueError("Prepared TIFF receipt mismatch: " + identity)
        sources.append(dict(metadata=layer["metadata"], grid=grid, asset="real/"+asset.name,
                            asset_size=asset.stat().st_size, asset_sha256=digest, layout=layout))
    return dict(schema_version="1.0", description="Native TIFF metadata and block layout only; no pixel counts", bounds=data["bounds"], default_aoi=data["default_aoi"], sources=sources)


def serialized(data_root):
    return json.dumps(create_catalog(data_root), indent=2, ensure_ascii=False, allow_nan=False)+"\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = ROOT / "data/population-catalog.json"
    expected = serialized(ROOT / "data")
    if args.check:
        if path.read_text(encoding="utf-8") != expected:
            raise ValueError("Population catalog is stale; regenerate during explicit preparation")
        print("Value-free population catalog matches canonical grids, TIFF layouts and hashes.")
    else:
        path.write_text(expected, encoding="utf-8", newline="\n")
        print("Created value-free population catalog.")


if __name__ == "__main__":
    main()
