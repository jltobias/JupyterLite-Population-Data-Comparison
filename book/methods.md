# Method and import contract

## Native counts and spherical overlap

All accepted data store **people per cell**, never density. A rectangular comparison allocates `native_count × spherical_overlap_area / spherical_native_cell_area`, assuming uniform population within each cell. Spherical rectangle area is proportional to longitude width times the difference of sine latitude. The stable implementation also handles tiny polar rectangles. This assumption cannot recover within-cell settlement patterns.

Regular grids store north-up row-major values, native origin, spacing and dimensions. Only intersecting native rows/columns are visited. Grids retain their different offsets; no common-grid resampling occurs. Each grid has at most 262,144 cells, with at most 32,767 pixels on either display axis. The original nonoverlapping rectangular-cell API remains available with a 2,000-cell limit. Every accepted cell must have representable positive bounds and area.

Coverage is the spherical fraction of the analysis rectangle containing numeric source cells. Numeric zero counts contribute coverage. Null is NoData and contributes neither population nor numeric-cell coverage. No numeric overlap returns `None` / `null`, displayed as “No coverage.” `prepared_coverage` separately reports geometric overlap with the available grid rectangle, so an area extending outside the excerpt is explicit. Tiny floating-point coverage excess is clamped to one.

## Interpreting the four products

WorldPop Global2 is a January 1, 2025 residential estimate and R2025A v1 is an alpha public release. GRID3 Nigeria is scaled to July 2025 and uses a different model and inputs. Within Nigeria its NaN means mapped unsettled; outside the national boundary it denotes outside coverage. These remain nulls rather than zero counts. LandScan Global 2020 describes ambient population averaged over 24 hours. GHS-POP 2025 is a residential projection using GPWv4.11 demographics and GHSL built-up information; it declares no NoData, so zero, including water, is numeric coverage.

WorldPop and GRID3 share producers/inputs. GHS-POP shares GPW demographic inputs. Product agreement is not independent accuracy validation. The same nominal year does not imply equal reference dates, concepts, inputs or uncertainty. Coverage is not a confidence measure.

## Import contract

The viewer's local GeoTIFF import runs in a cancellable Web Worker. Edit and confirm source metadata for your chosen file. Templates provide citations; they do not independently identify the uploaded file. Bundled excerpt receipts and verification claims are removed from user imports. Fresh declarations retain filename, file size, modification time, source geometry, selected native window, TIFF metadata and the reader/method. The browser reads file slices and intersecting native decode blocks; no server receives the file.

Accepted TIFFs are little-endian, single-band, PixelIsArea, explicitly EPSG:4326 and north-up with positive pixel scale and one tiepoint. Counts must be stored directly, with finite nonnegative values or a declared NoData sentinel (including NaN). Unsupported CRS, rotation/shear, PixelIsPoint, scale/offset, internal masks, alpha/extra samples, SubIFDs, multiple primary images and unsupported sample encodings are rejected. External `.msk` sidecars cannot be read; declare that the file has none. Overviews in the main IFD chain are inspected but never used for calculations. Sparse blocks retain declared NoData, including NaN.

Limits: file 2 GiB; native output 262,144 cells, with at most 32,767 pixels on either display axis; metadata 8 MiB, 1,024 entries per directory and 32 directories; each decode block 16 million pixels; selected compressed blocks 64 MiB; selected decoded blocks 128 MiB. Only uncompressed, LZW and Deflate counts are accepted, with bounded decompression. Choose a smaller area or prepare a tiled excerpt when a file exceeds these limits. No resampling is used to fit a limit. Cancellation terminates the worker; errors retain valid layers and analysis.

Small rectangular GeoJSON imports remain supported: WGS84 FeatureCollection without a CRS override, one closed axis-aligned Polygon ring per feature, numeric `properties.population`, required metadata, at most 2 MB and 2,000 nonoverlapping cells, each no more than 5° wide/high. A labelled synthetic fixture is supplied only for this lesson/test contract.

## Reproducibility and exports

`data/population.json` contains canonical lossless count/null arrays. `data/real/` contains TIFF excerpts, acquisition receipts, native transforms, source/output hashes, STAC metadata, independent source expectations and ORNL validation receipts. `scripts/prepare_population.py` explicitly acquires/extracts sources with optional NumPy/rasterio dependencies; normal builds never refresh sources. Input cache files stay outside publication.

JSON and CSV retain full metadata, grid identity, active bounds, counts, coverage, native cell count and method. CSV's `metadata_json` preserves extra notices. SVG embeds complete results in its description and displays source credits, license, dates/concepts and coverage. Display rounding does not affect export precision. NoData remains distinct from zero in all formats.
