# Raster reader notices

GeoTIFF.js **3.0.5** classic distribution, SHA-256 `8cfc01ffc945904766d8fb89f19da7afb799e342834454f5592fbcf0bcfe2db5`.
Copied from `jltobias/JupyterLite-STAC-Browser` revision `945d8b31c59e2cf93f9e51e855eb062fb1b4321c`, `web/vendor/geotiff-3.0.5.js`.
Upstream GeoTIFF.js revision `4a296052fb90aa2cc673f573d6f95d14167a8fbc`.

Retain `LICENSE-geotiff`, `RASTER-DEPENDENCY-LICENSES.txt` and `RASTER-DEPENDENCIES.json`. The dependency inventory also describes Proj4 from the companion application; Proj4 is not shipped or used here. The companion MIT notice is retained in `LICENSE-companion` for this reuse and its raster-worker approach. Our worker accepts only north-up WGS84 count files, reads a bounded native window with `fromBlob`, and never uses a network raster service.
