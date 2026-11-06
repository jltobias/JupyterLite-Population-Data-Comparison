"""Explicit native-window preparation. Never called by normal site builds.

Install requirements-raster.txt, then run this script using the verified cache.
--download allows HTTPS acquisition of missing national/tile sources. LandScan's
pinned mirror may also be downloaded in full; its published hash is identified
as a mirror assertion, not independent ORNL full-file verification.
"""
import argparse
from datetime import date
import hashlib
import json
import math
import shutil
import tempfile
import re
import urllib.request
import zipfile
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import Window, from_bounds

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache/population"
OUT = ROOT / "data/real"
BOUNDS = [3.2, 6.35, 3.6, 6.7]
WP = "https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2025/NGA/v1/100m/constrained/nga_pop_2025_CN_100m_R2025A_v1.tif"
G3 = "https://data.worldpop.org/repo/wopr/NGA/population/v3.0/NGA_population_v3_0_gridded.zip"
LS = "https://huggingface.co/datasets/Daksh17440/global_population_data/resolve/404bde4c5b56347cbce2e1824890246872a89aef/landscan-global-2020.tif"
GHS = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/GHS_POP_E2025_GLOBE_R2023A_4326_30ss/V1-0/tiles/GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0_R9_C19.zip"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")


def acquire(name, url, expected, download):
    path = CACHE / name
    valid = path.exists() and (not expected or sha(path) == expected)
    if valid and path.suffix == ".json":
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError):
            valid = False
    if valid:
        return path
    if not download:
        raise ValueError(f"Missing or checksum-mismatched source {path}; --download is required to acquire/repair it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    # A failed/interrupted transfer never occupies the final cache name.
    with tempfile.TemporaryDirectory(prefix="download-", dir=path.parent) as directory:
        temporary = Path(directory) / path.name
        urllib.request.urlretrieve(url, temporary)
        if not temporary.stat().st_size or expected and sha(temporary) != expected:
            raise ValueError(f"Downloaded source checksum mismatch: {name}")
        if path.suffix == ".json":
            json.loads(temporary.read_text(encoding="utf-8"))
        receipt = temporary.with_suffix(temporary.suffix + ".retrieval.json")
        write(receipt, {"url": url, "retrieval_date": date.today().isoformat(), "tls_verification": "Certificate chain and hostname verification enabled."})
        temporary.replace(path)
        receipt.replace(path.with_suffix(path.suffix + ".retrieval.json"))
    return path


def iso_date(value):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Retrieval date must be YYYY-MM-DD.")
    return date.fromisoformat(value).isoformat()


def retrieval_date(path, declared=None):
    receipt = path.with_suffix(path.suffix + ".retrieval.json")
    if receipt.exists():
        return iso_date(json.loads(receipt.read_text(encoding="utf-8"))["retrieval_date"])
    if declared:
        return iso_date(declared)
    raise ValueError(f"No acquisition receipt for {path.name}; supply its actual --retrieval-date YYYY-MM-DD.")


def extract(archive, member, target, expected, declared):
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="extract-", dir=target.parent) as directory:
        temporary = Path(directory) / target.name
        with zipfile.ZipFile(archive) as z:
            temporary.write_bytes(z.read(member))
        if sha(temporary) != expected:
            raise ValueError(f"Extracted source checksum mismatch: {target.name}")
        acquired = retrieval_date(archive, declared)
        temporary.replace(target)
        write(target.with_suffix(target.suffix + ".retrieval.json"), {"retrieval_date": acquired, "archive": archive.name})


def preserved_receipts():
    values = {}
    names = ("independent_oracle.json", "comparison_source_provenance.json", "worldpop-stac-item.json", "landscan2020_official_stats.json", "landscan2020_greater_lagos_official_stats.json", "ghsl_copyright.txt")
    for name in names:
        # Preserve enriched producer-request evidence instead of stale research copies.
        choices = (OUT / name, CACHE / name) if name.startswith("landscan2020_") else (CACHE / name, OUT / name)
        path = next((p for p in choices if p.exists()), None)
        if path is None:
            raise ValueError(f"Missing preserved provenance receipt {name}")
        value = path.read_bytes()
        if name.endswith(".json"):
            parsed = json.loads(value)
            if name.startswith("landscan2020_"):
                records = parsed if isinstance(parsed, list) else [parsed]
                for index, record in enumerate(records):
                    if not isinstance(record.get("payload"), dict):
                        raise ValueError("ORNL validation receipt lacks its request payload.")
                    record["request_provenance"] = {"endpoint": "https://hm52ct46i7.execute-api.us-east-1.amazonaws.com/prod/stats", "method": "POST", "content_type": "application/json", "retrieval_date": "2026-11-06", "original_request_time_utc": None, "time_note": "Original request time was not retained; no timestamp is inferred."}
                    select = f"r=r[{index}]; " if isinstance(parsed, list) else ""
                    record["reproduce_command"] = f"python -c \"import json,urllib.request; r=json.load(open('data/real/{name}',encoding='utf-8')); {select}q=urllib.request.Request('https://hm52ct46i7.execute-api.us-east-1.amazonaws.com/prod/stats',data=json.dumps(r['payload']).encode(),headers={{'Content-Type':'application/json'}},method='POST'); print(urllib.request.urlopen(q).read().decode())\""
                value = (json.dumps(parsed, ensure_ascii=False, indent=2) + "\n").encode()
        values[name] = value
    return values



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--retrieval-date", type=iso_date, help="Actual acquisition date for manually supplied inputs without receipts")
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    wp = acquire("nga_pop_2025_CN_100m_R2025A_v1.tif", WP, "abc7e897aff7de024d851a24613eebf28e710dbfe4dea9c3e02ee285d75d4f8b", args.download)
    g3 = CACHE / "NGA_population_v3_0_gridded.tif"
    g3_hash = "b9d72f2d7f538c69daca8ce68008bfdc07aa848b1885544af4ae77428ffbbe5e"
    if not g3.exists() or sha(g3) != g3_hash:
        if g3.exists() and not args.download:
            raise ValueError("GRID3 checksum mismatch; --download required for repair.")
        archive = acquire(g3.with_suffix(".zip").name, G3, "12a45438c233bbfa52d120001eca20660cff86e715a91b3cfd66c94fc31aee42", args.download)
        extract(archive, "NGA_population_v3_0_gridded/NGA_population_v3_0_gridded.tif", g3, g3_hash, args.retrieval_date)
    ls = CACHE / "landscan2020_greater_lagos.tif"
    if ls.exists() and sha(ls) != "486eda4d2d0ac4e92fded4acc7dd8a9a2467bfd403b3659cfe6dba2f2a908f26":
        if not args.download:
            raise ValueError("LandScan excerpt checksum mismatch; --download required for repair.")
        ls = CACHE / "landscan-global-2020.tif"
    if not ls.exists() or ls.name == "landscan-global-2020.tif":
        ls = acquire("landscan-global-2020.tif", LS, "9f71990ec4ef6208ccdc25b75ba6a395f99dc367261f60c2cbca153023271e33", args.download)
    ghs = CACHE / "ghsl2025/GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0_R9_C19.tif"
    ghs_hash = "ff4c7e9ffe026143904d939cf0884edef967e799a5590dc4a71a7e682550f1e2"
    if not ghs.exists() or sha(ghs) != ghs_hash:
        if ghs.exists() and not args.download:
            raise ValueError("GHSL checksum mismatch; --download required for repair.")
        archive = acquire(ghs.with_suffix(".zip").name, GHS, "1762b067b5c807dbe340b523c943d21003810018b34c00138c1ffac48e455f8b", args.download)
        extract(archive, ghs.name, ghs, ghs_hash, args.retrieval_date)
    stac = acquire("worldpop-stac-item.json", "https://api.stac.worldpop.org/collections/NGA/items/nga_pop_2025_CN_100m_R2025A_v1", None, args.download)
    wp_item = json.loads(stac.read_text(encoding="utf-8"))
    common = dict(license="CC BY 4.0", license_url="https://creativecommons.org/licenses/by/4.0/", synthetic=False, units="people/cell", crs="EPSG:4326", prepared_extent=BOUNDS, modification="Spatial subset and lossless count/null serialization; no resampling. No producer endorsement.")
    records = [
        ("worldpop-2025", wp, dict(title="WorldPop Global2 2025", source="WorldPop, University of Southampton", citation=wp_item["properties"]["coordinate_reference_system:citation"], year=2025, version="R2025A v1 (alpha public release)", resolution="Native 3 arcseconds (~100 m)", population_concept="Residential population estimate", reference_date="2025-01-01", allocation="Constrained Random Forest dasymetric redistribution", census_vintage="Multiple national census inputs; see release", source_asset=WP, stac_item=wp_item["id"], stac_collection="NGA", stac_asset="data", nodata_semantics="-99999 denotes NoData, distinct from numeric zero", notices="WorldPop / University of Southampton. Gates Foundation INV-045237.")),
        ("grid3-2025", g3, dict(title="GRID3 Nigeria 2025", source="GRID3 Inc.; WorldPop; CIESIN, Columbia Climate School", citation="Nnanatu C.C., Gadiaga A., Abbott T.J., Chamberlain H., Lazar A.N., Tatem A.J. (2025). Modelled gridded population estimates for Nigeria 2025 version 3.0. WorldPop, University of Southampton. https://doi.org/10.5258/SOTON/WP00782", year=2025, version="Nigeria v3.0", resolution="Native ~3 arcseconds (~100 m)", population_concept="Residential modelled population estimate", reference_date="2025-07", allocation="Bayesian model, settlement and covariates; scaled to UN WPP national projection", census_vintage="NMEP 2022–23 household listing and other covariates", source_asset=G3, archive_member="NGA_population_v3_0_gridded/NGA_population_v3_0_gridded.tif", nodata_semantics="NaN: mapped unsettled within Nigeria; outside national boundary: outside coverage. Not zero.", notices="GRID3 Inc.; WorldPop; CIESIN / Columbia Climate School. Gates Foundation INV-044979. Operational estimates, not official government statistics; no warranties.")),
        ("landscan-2020", ls, dict(title="LandScan Global 2020", source="Oak Ridge National Laboratory (pixels retrieved from pinned Hugging Face mirror)", citation="Rose A., McKee J., Sims K., Bright E., Reith A., Urban M. (2021). LandScan Global 2020. Oak Ridge National Laboratory. https://doi.org/10.48690/1523378", year=2020, version="LandScan Global 2020", resolution="Native 30 arcseconds (~1 km)", population_concept="Ambient population (24-hour average)", reference_date="2020", allocation="Multivariable dasymetric ambient population modelling", census_vintage="Input census vintages vary; see provider", source_asset=LS, mirror_commit="404bde4c5b56347cbce2e1824890246872a89aef", source_asset_sha256_published_by_mirror="9f71990ec4ef6208ccdc25b75ba6a395f99dc367261f60c2cbca153023271e33", source_asset_sha256_locally_verified=False, nodata_semantics="-2147483647 denotes NoData; numeric zero valid", notices="Oak Ridge National Laboratory. https://landscan.ornl.gov/licensing", validation="Independent ORNL public statistics: one cell 73830; snapped excerpt sum 18551545, 1478 numeric cells, max 109265. Does not prove full mirror bit identity.")),
        ("ghspop-2025", ghs, dict(title="GHS-POP 2025", source="European Commission, Joint Research Centre", citation="Schiavina M., Freire S., Carioli A., MacManus K. (2023). GHS-POP R2023A: GHS population grid multitemporal (1975–2030). European Commission/JRC. https://doi.org/10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE; Pesaresi et al. (2024). https://doi.org/10.1080/17538947.2024.2390454", year=2025, version="R2023A E2025 WGS84 30ss V1.0", resolution="Native 30 arcseconds (~1 km), distinct grid offset", population_concept="Residential population projection", reference_date="2025 projection", allocation="GPWv4.11 demographic inputs allocated using GHSL built-up distribution, volume and class", census_vintage="GPWv4.11 source census vintages vary", source_asset=GHS, archive_member=ghs.name, nodata_semantics="No declared NoData; zero remains valid, including water", notices="(c) European Union, 1995-2026. CC BY 4.0. Spatial subset / serialization; no endorsement."))
    ]
    with tempfile.TemporaryDirectory(prefix="prepare-", dir=CACHE) as directory:
        stage = Path(directory)
        stage_real = stage / "real"
        stage_real.mkdir()
        layers, receipts = [], {}
        preserved = preserved_receipts()
        oracle = json.loads(preserved["independent_oracle.json"])
        dates = {id_: retrieval_date(path, args.retrieval_date) for id_, path, _ in records}
        for id_, path, metadata in records:
            with rasterio.open(path) as src:
                # LandScan cached excerpt already uses independently validated boundary snapping.
                if id_ == "landscan-2020" and path.name.endswith("greater_lagos.tif"):
                    window = Window(0, 0, src.width, src.height)
                else:
                    raw = from_bounds(*BOUNDS, src.transform)
                    edges = [raw.col_off, raw.row_off, raw.col_off+raw.width, raw.row_off+raw.height]
                    if id_ == "landscan-2020":
                        # Preserve the independently validated producer-aligned window.
                        edges = [round(v) if abs(v-round(v)) < 1e-7 else v for v in edges]
                    window = Window(math.floor(edges[0]), math.floor(edges[1]), math.ceil(edges[2])-math.floor(edges[0]), math.ceil(edges[3])-math.floor(edges[1]))
                data = src.read(1, window=window, masked=True)
                transform = src.window_transform(window)
                valid = ~np.ma.getmaskarray(data)
                values = data.data
                if np.any(~np.isfinite(values[valid])) or np.any(values[valid] < 0):
                    raise ValueError(f"Invalid native counts in {id_}")
                g = dict(width=data.shape[1], height=data.shape[0], west=transform.c, north=transform.f, dx=transform.a, dy=-transform.e, values=[float(v) if ok else None for v, ok in zip(values.flat, valid.flat)])
                output = stage_real / f"{id_}.tif"
                profile = dict(driver="GTiff", width=g["width"], height=g["height"], count=1, dtype=src.dtypes[0], crs=src.crs, transform=transform, nodata=src.nodata, compress="lzw" if id_ == "worldpop-2025" else "deflate")
                receipt = dict(source_file=path.name, source_file_sha256=sha(path), source_dimensions=[src.width, src.height], source_transform=list(src.transform)[:6], window=[int(window.col_off), int(window.row_off), int(window.width), int(window.height)], output_transform=list(transform)[:6], output_file=output.name, source_dtype=src.dtypes[0], nodata="NaN" if src.nodata is not None and math.isnan(src.nodata) else src.nodata, valid_cells=int(valid.sum()), nodata_cells=int((~valid).sum()), native_sum=float(values[valid].astype("float64").sum()), processing="rasterio native read window; no warp, resample, scale or rounding", retrieval_date=dates[id_])
                credits = dict(common, id=id_, **metadata, retrieval_date=dates[id_])
                tags = dict(src.tags(), SOURCE_CITATION=credits["citation"], LICENSE=credits["license"], LICENSE_URL=credits["license_url"], PRODUCER_NOTICES=credits["notices"], SOURCE_ASSET=credits["source_asset"], RETRIEVAL_DATE=credits["retrieval_date"], MODIFICATION=credits["modification"], NATIVE_PROVENANCE=json.dumps(receipt, allow_nan=False), SOURCE_TITLE=credits["title"], SOURCE_VERSION=credits["version"], POPULATION_CONCEPT=credits["population_concept"], REFERENCE_DATE=credits["reference_date"])
                with rasterio.open(output, "w", **profile) as dst:
                    dst.write(values, 1)
                    dst.update_tags(**tags)
                receipt["output_sha256"] = sha(output)
                reference = oracle["sources"][id_]
                if receipt["valid_cells"] != reference["valid_cells"] or not math.isclose(receipt["native_sum"], reference["native_sum"], abs_tol=1e-6):
                    raise ValueError(f"Independent source oracle mismatch for {id_}")
                receipt["retrieval_date"] = dates[id_]
                if id_ in ("grid3-2025", "ghspop-2025"):
                    receipt["source_archive_sha256"] = "12a45438c233bbfa52d120001eca20660cff86e715a91b3cfd66c94fc31aee42" if id_ == "grid3-2025" else "1762b067b5c807dbe340b523c943d21003810018b34c00138c1ffac48e455f8b"
                metadata = dict(common, id=id_, **metadata, processing_receipt=receipt)
                metadata["retrieval_date"] = receipt["retrieval_date"]
                layers.append(dict(metadata=metadata, grid=g))
                receipts[id_] = receipt
        write(stage / "population.json", dict(schema_version="2.0", description="Real native-pixel Greater Lagos population excerpts. Counts and masks preserved. Regional, not global streaming.", bounds=BOUNDS, default_aoi=oracle["default_aoi"], layers=layers))
        write(stage_real / "preparation.json", dict(source_retrieval_dates=dates, method="Native windows; no resampling; JSON null preserves source NoData; no endorsement", requested_extent=BOUNDS, receipts=receipts, software={"rasterio": rasterio.__version__, "numpy": np.__version__}))
        for name, value in preserved.items():
            (stage_real / name).write_bytes(value)
        published_oracle = json.loads(preserved["independent_oracle.json"])
        for expected in published_oracle["sources"].values():
            if expected["aoi_coverage"] > 1:
                expected["aoi_coverage_unclamped"] = expected["aoi_coverage"]
                expected["aoi_coverage"] = 1
        published_oracle["coverage_roundoff_policy"] = "Clamp tiny coverage excess to one; retain original independent value in aoi_coverage_unclamped."
        write(stage_real / "independent_oracle.json", published_oracle)
        # Generate metadata-only catalog in the same staging transaction.
        from create_population_catalog import serialized
        (stage / "population-catalog.json").write_text(serialized(stage), encoding="utf-8", newline="\n")
        # Every source, oracle, catalog and preserved receipt passed before canonical mutation.
        for path in stage_real.iterdir():
            path.replace(OUT / path.name)
        (stage / "population.json").replace(ROOT / "data/population.json")
        (stage / "population-catalog.json").replace(ROOT / "data/population-catalog.json")
    print("Prepared four native-pixel grids; verified masks and native sums against independent source oracle.")


if __name__ == "__main__":
    main()
