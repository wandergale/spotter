"""
Integration tests for the TripCalculateView.

External APIs (Nominatim, OSRM) are mocked to keep tests fast and offline.
"""

import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse

from trips.services.route_service import Coordinates, RouteSegment


def _make_coords():
    return [
        Coordinates(lat=30.27, lon=-97.74, display_name='Austin, TX'),
        Coordinates(lat=32.78, lon=-96.80, display_name='Dallas, TX'),
        Coordinates(lat=34.05, lon=-118.24, display_name='Los Angeles, CA'),
    ]


def _make_segments():
    return [
        RouteSegment(
            origin=_make_coords()[0],
            destination=_make_coords()[1],
            distance_miles=195.0,
            duration_hours=3.5,
            geometry={'type': 'LineString', 'coordinates': [[-97.74, 30.27], [-96.80, 32.78]]},
        ),
        RouteSegment(
            origin=_make_coords()[1],
            destination=_make_coords()[2],
            distance_miles=1240.0,
            duration_hours=18.0,
            geometry={'type': 'LineString', 'coordinates': [[-96.80, 32.78], [-118.24, 34.05]]},
        ),
    ]


def _make_route_data():
    segs = _make_segments()
    return {
        'route': {
            'geometry': {'type': 'LineString', 'coordinates': []},
            'total_distance_miles': 1435.0,
            'total_duration_hours': 21.5,
        },
        'segments': segs,
        'coords': _make_coords(),
    }


class TripCalculateViewTest(TestCase):
    URL = '/api/trip/calculate/'

    def _valid_payload(self):
        return {
            'current_location': 'Austin, TX',
            'pickup_location': 'Dallas, TX',
            'dropoff_location': 'Los Angeles, CA',
            'current_cycle_used': 20.0,
        }

    # ── Happy path ────────────────────────────────────────────────────────────

    @patch('trips.views.RouteService')
    def test_success_returns_200(self, MockRouteService):
        svc = MockRouteService.return_value
        svc.geocode_locations.return_value = _make_coords()
        svc.get_route.return_value = _make_route_data()

        resp = self.client.post(
            self.URL,
            data=json.dumps(self._valid_payload()),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)

    @patch('trips.views.RouteService')
    def test_response_has_required_keys(self, MockRouteService):
        svc = MockRouteService.return_value
        svc.geocode_locations.return_value = _make_coords()
        svc.get_route.return_value = _make_route_data()

        resp = self.client.post(
            self.URL,
            data=json.dumps(self._valid_payload()),
            content_type='application/json',
        )
        body = resp.json()
        for key in ('route', 'stops', 'daily_logs', 'total_trip_days', 'total_driving_hours'):
            self.assertIn(key, body, f"Missing key '{key}' in response.")

    @patch('trips.views.RouteService')
    def test_stops_include_pickup_and_dropoff(self, MockRouteService):
        svc = MockRouteService.return_value
        svc.geocode_locations.return_value = _make_coords()
        svc.get_route.return_value = _make_route_data()

        resp = self.client.post(
            self.URL,
            data=json.dumps(self._valid_payload()),
            content_type='application/json',
        )
        stops = resp.json()['stops']
        types = {s['type'] for s in stops}
        self.assertIn('pickup', types)
        self.assertIn('dropoff', types)

    @patch('trips.views.RouteService')
    def test_daily_logs_have_required_structure(self, MockRouteService):
        svc = MockRouteService.return_value
        svc.geocode_locations.return_value = _make_coords()
        svc.get_route.return_value = _make_route_data()

        resp = self.client.post(
            self.URL,
            data=json.dumps(self._valid_payload()),
            content_type='application/json',
        )
        logs = resp.json()['daily_logs']
        self.assertGreater(len(logs), 0)
        for day in logs:
            self.assertIn('date', day)
            self.assertIn('entries', day)
            self.assertIn('summary', day)
            for entry in day['entries']:
                self.assertIn('status', entry)
                self.assertIn('start_hour', entry)
                self.assertIn('end_hour', entry)

    # ── Validation errors ─────────────────────────────────────────────────────

    def test_missing_field_returns_400(self):
        payload = self._valid_payload()
        del payload['pickup_location']
        resp = self.client.post(
            self.URL,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_cycle_hours_out_of_range_returns_400(self):
        payload = self._valid_payload()
        payload['current_cycle_used'] = 75.0  # > 70, invalid
        resp = self.client.post(
            self.URL,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_negative_cycle_hours_returns_400(self):
        payload = self._valid_payload()
        payload['current_cycle_used'] = -5.0
        resp = self.client.post(
            self.URL,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_empty_location_returns_400(self):
        payload = self._valid_payload()
        payload['current_location'] = '   '
        resp = self.client.post(
            self.URL,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    # ── External API failures ─────────────────────────────────────────────────

    @patch('trips.views.RouteService')
    def test_geocode_failure_returns_502(self, MockRouteService):
        from trips.services.route_service import RouteServiceError
        svc = MockRouteService.return_value
        svc.geocode_locations.side_effect = RouteServiceError("Nominatim down")

        resp = self.client.post(
            self.URL,
            data=json.dumps(self._valid_payload()),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 502)
        self.assertIn('error', resp.json())

    @patch('trips.views.RouteService')
    def test_routing_failure_returns_502(self, MockRouteService):
        from trips.services.route_service import RouteServiceError
        svc = MockRouteService.return_value
        svc.geocode_locations.return_value = _make_coords()
        svc.get_route.side_effect = RouteServiceError("OSRM unavailable")

        resp = self.client.post(
            self.URL,
            data=json.dumps(self._valid_payload()),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 502)
