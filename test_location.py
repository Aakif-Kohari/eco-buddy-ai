import datetime
import pytest
from location_parser import parse_gpx, segment_trips, process_segment

GPX_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
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


def test_parse_gpx_returns_correct_waypoint_count():
    waypoints = parse_gpx(GPX_CONTENT)
    assert len(waypoints) == 3


def test_parse_gpx_waypoint_structure():
    waypoints = parse_gpx(GPX_CONTENT)
    for wp in waypoints:
        assert "lat" in wp
        assert "lon" in wp
        assert "timestamp" in wp
        assert isinstance(wp["lat"], float)
        assert isinstance(wp["lon"], float)
        assert isinstance(wp["timestamp"], datetime.datetime)


def test_segment_trips_single_continuous_segment():
    waypoints = parse_gpx(GPX_CONTENT)
    segments = segment_trips(waypoints, time_threshold_minutes=30)
    assert len(segments) == 1


def test_segment_trips_detects_mode():
    waypoints = parse_gpx(GPX_CONTENT)
    segments = segment_trips(waypoints, time_threshold_minutes=30)
    assert len(segments) > 0
    mode = segments[0]["mode"]
    assert mode in ["Walking", "Bike", "Public Transport", "Car"]


def test_segment_trips_distance_positive():
    waypoints = parse_gpx(GPX_CONTENT)
    segments = segment_trips(waypoints, time_threshold_minutes=30)
    assert len(segments) > 0
    assert segments[0]["distance_km"] > 0


def test_segment_trips_splits_on_time_gap():
    wpts = [
        {"lat": 47.644, "lon": -122.326, "timestamp": datetime.datetime(2023, 10, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)},
        {"lat": 47.645, "lon": -122.327, "timestamp": datetime.datetime(2023, 10, 1, 10, 2, 0, tzinfo=datetime.timezone.utc)},
        {"lat": 47.648, "lon": -122.330, "timestamp": datetime.datetime(2023, 10, 1, 11, 0, 0, tzinfo=datetime.timezone.utc)},
    ]
    segments = segment_trips(wpts, time_threshold_minutes=30)
    assert len(segments) == 1


def test_detect_transport_mode_speed_ranges():
    from location_parser import detect_transport_mode
    assert detect_transport_mode(5.0) == "Walking"
    assert detect_transport_mode(15.0) == "Bike"
    assert detect_transport_mode(35.0) == "Public Transport"
    assert detect_transport_mode(60.0) == "Car"


def test_process_segment_returns_required_keys():
    wpts = [
        {"lat": 47.644, "lon": -122.326, "timestamp": datetime.datetime(2023, 10, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)},
        {"lat": 47.645, "lon": -122.327, "timestamp": datetime.datetime(2023, 10, 1, 10, 2, 0, tzinfo=datetime.timezone.utc)},
    ]
    result = process_segment(wpts)
    assert "start_time" in result
    assert "end_time" in result
    assert "distance_km" in result
    assert "mode" in result
    assert "avg_speed_kmh" in result
    assert "waypoints" in result
