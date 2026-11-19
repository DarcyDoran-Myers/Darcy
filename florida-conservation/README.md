# Florida Lands Conserved

Animated map of Florida's conservation lands accumulating by acquisition year (1845 to today),
split into government-owned land, conservation easements, and nonprofit/private preserves.

- `index.html` – the page (canvas map + cumulative chart; loads d3 and topojson-client from CDNs)
- `lands.json` – TopoJSON in Florida Albers (EPSG:3086) meters: dated land pieces, counties, state outline
- `meta.json` – managed-area names and acres added per year by category

Footprint: FNAI Florida Conservation Lands. Dates: FL DEP FL-SOLARIS deed dates, Florida Forever
closing dates, USGS PAD-US 4.1 establishment dates; establishment years of large federal units
fill gaps and are marked as estimated. Serve the folder over HTTP (`python3 -m http.server`) to view.
