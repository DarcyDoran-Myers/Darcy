# Florida Lands Conserved

Animated map of Florida's conservation lands accumulating by acquisition year (1845 to today),
split into government-owned land, conservation easements, and nonprofit/private preserves.

- `index.html` – the page (canvas map + cumulative chart; loads d3 and topojson-client from CDNs)
- `lands.json` – TopoJSON in Florida Albers (EPSG:3086) meters: dated land pieces, counties, state outline
- `meta.json` – managed-area names and acres added per year by category

Footprint: FNAI Florida Conservation Lands. Dates: FL DEP FL-SOLARIS deed dates, Florida Forever
closing dates, USGS PAD-US 4.1 establishment dates; establishment years of large federal units
fill gaps and are marked as estimated. Serve the folder over HTTP (`python3 -m http.server`) to view.

## Water

Pieces are clipped to land: FDEP Florida Counties with Shoreline (1:12,000), minus Lake Okeechobee and
lakes/rivers ≥ ~1,000 acres from Esri USA Detailed Water Bodies (`tools/landclip.py`). Marshes and swamps stay.

## Social video

`video/florida-lands-conserved-vertical.mp4` (1080×1920, 9:16) and `video/florida-lands-conserved-square.mp4`
(1080×1080), 31 s at 30 fps, 1900–2026 with a 5 s hold on the final map. Rendered from `video/render.html` frame by frame with Playwright + ffmpeg
(`tools/video.js <vertical|square> out.mp4`).

## Developed land

`developed.bin` / `developed_meta.json`: 250 m cells (EPSG:3086) with the share of ground ≥ 20 % impervious in
NLCD 2021 and the years when 25/50/75/100 % of that share was reached. Post-2001 timing from NLCD impervious
2001/2006/2011/2016/2021 (MRLC WCS, `tools/nlcd.py`); pre-2001 timing from HISDAC-US Version II built-up
property records and first-built year (`tools/devmodel.py`). Cells without building records take the mean
timing of dated neighbours (17 % of 2021 developed area). Binary format: varint index delta, then 5 bytes.
