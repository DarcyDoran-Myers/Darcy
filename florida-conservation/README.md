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
