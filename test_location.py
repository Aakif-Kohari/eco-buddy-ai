import datetime
from location_parser import parse_gpx, segment_trips, process_segment

gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Mock">
  <trk>
    <trkseg>
      <trkpt lat="47.644548" lon="-122.326897">
        <time>2023-10-01T10:00:00Z</time>
      </trkpt>
      <trkpt lat="47.645000" lon="-122.327000">
        <time>2023-10-01T10:02:00Z</time>
      </trkpt>
      <trkpt lat="47.648000" lon="-122.330000">
        <time>2023-10-01T10:05:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>
"""

waypoints = parse_gpx(gpx_content)
print(f"Waypoints count: {len(waypoints)}")

segments = segment_trips(waypoints)
print(f"Segments count: {len(segments)}")
for seg in segments:
    print(seg["mode"], seg["distance_km"], seg["avg_speed_kmh"])
