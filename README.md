# Dining Week Map

Interactive map of Dining Week 2026 restaurants (uge 42, 9–18 October) with Google ratings,
review summaries, menus, bookable days and party sizes.

- **Map:** `index.html`, published with GitHub Pages.
- **Availability:** every hour, GitHub Actions runs `scripts/update_availability.py`, which reads
  https://diningweek.dk/restaurants and publishes `availability.json` next to the map.
  The map loads it on open and when you press **Refresh availability**.
- **Update right now:** Actions tab → *Update availability and publish map* → *Run workflow*.
- The hourly job stops by itself after 19 October 2026.

Map data © OpenStreetMap contributors · Tiles © Esri · Ratings from Google Maps (fetched 30 Sep 2026).
Review summaries were written by Claude from recent Google reviews.
