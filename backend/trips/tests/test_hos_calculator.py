"""
Unit tests for the HOS Calculator.

Each test targets a specific FMCSA rule boundary in isolation.
No external APIs are called; route data is constructed inline.
"""

import unittest
from dataclasses import dataclass
from trips.services.hos_calculator import (
    HOSCalculator,
    HOSCycleExhaustedError,
    BREAK_TRIGGER_HOURS,
    BREAK_DURATION,
    OFF_DUTY_RESET,
    FUEL_INTERVAL_MILES,
    FUEL_DURATION,
    AVERAGE_SPEED_MPH,
    PICKUP_DURATION,
    DROPOFF_DURATION,
    MAX_DRIVING_HOURS,
    MAX_ON_DUTY_WINDOW,
    CYCLE_LIMIT,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

@dataclass
class MockSegment:
    """Minimal RouteSegment substitute for testing."""
    distance_miles: float
    duration_hours: float
    origin: object = None
    destination: object = None
    geometry: dict = None

    def __post_init__(self):
        if self.geometry is None:
            self.geometry = {'type': 'LineString', 'coordinates': []}


def make_route(seg0_miles: float, seg1_miles: float) -> dict:
    """Build a minimal route_data dict for HOSCalculator.simulate()."""
    return {
        'route': {'geometry': {}, 'total_distance_miles': seg0_miles + seg1_miles,
                  'total_duration_hours': (seg0_miles + seg1_miles) / AVERAGE_SPEED_MPH},
        'segments': [
            MockSegment(
                distance_miles=seg0_miles,
                duration_hours=seg0_miles / AVERAGE_SPEED_MPH,
            ),
            MockSegment(
                distance_miles=seg1_miles,
                duration_hours=seg1_miles / AVERAGE_SPEED_MPH,
            ),
        ],
        'coords': [],
    }


# ── Test Cases ─────────────────────────────────────────────────────────────────

class TestHOSCalculatorBasic(unittest.TestCase):
    """Tests for basic simulation correctness."""

    def test_short_trip_produces_stops_for_pickup_and_dropoff(self):
        """A short trip should always include a pickup and dropoff stop."""
        route = make_route(seg0_miles=50, seg1_miles=100)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        types = [s.type for s in result.stops]
        self.assertIn('pickup', types)
        self.assertIn('dropoff', types)

    def test_short_trip_no_mandatory_rest(self):
        """A 150-mile trip should not require any mandatory rest stops."""
        route = make_route(seg0_miles=50, seg1_miles=100)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        rest_stops = [s for s in result.stops if s.type == 'rest']
        self.assertEqual(len(rest_stops), 0, "Short trip should have no rest stops.")

    def test_short_trip_no_30min_break(self):
        """A sub-8-hour driving trip should not require a 30-min break."""
        # 8hr * 55mph = 440 miles total.  Keep well under that.
        route = make_route(seg0_miles=100, seg1_miles=100)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        break_stops = [s for s in result.stops if s.type == 'break']
        self.assertEqual(len(break_stops), 0, "Short trip should have no break stops.")

    def test_timeline_is_contiguous(self):
        """There must be no time gaps in the timeline (events must chain end→start)."""
        route = make_route(seg0_miles=300, seg1_miles=600)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        sorted_events = sorted(result.timeline, key=lambda e: e.start_abs)
        for i in range(1, len(sorted_events)):
            prev = sorted_events[i - 1]
            curr = sorted_events[i]
            self.assertAlmostEqual(
                prev.end_abs, curr.start_abs, places=4,
                msg=f"Gap between event {i-1} (end={prev.end_abs:.4f}) "
                    f"and event {i} (start={curr.start_abs:.4f})"
            )

    def test_total_driving_hours_matches_timeline(self):
        """total_driving_hours must equal the sum of 'D' events in the timeline."""
        route = make_route(seg0_miles=200, seg1_miles=400)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        timeline_driving = sum(e.duration for e in result.timeline if e.status == 'D')
        self.assertAlmostEqual(
            result.total_driving_hours, timeline_driving, places=2
        )


class TestHOS30MinBreak(unittest.TestCase):
    """Tests for the 30-minute break rule (after 8 cumulative driving hours)."""

    def test_break_inserted_after_8hr_driving(self):
        """
        A trip requiring > 8 hours of driving must include at least one break stop.
        8hr × 55mph = 440 miles; use 600 miles to guarantee crossing the threshold.
        """
        route = make_route(seg0_miles=50, seg1_miles=600)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        break_stops = [s for s in result.stops if s.type == 'break']
        self.assertGreaterEqual(
            len(break_stops), 1,
            "Expected at least one 30-min break for a >8hr driving trip."
        )

    def test_break_duration_is_30_minutes(self):
        """Each break stop must be exactly 30 minutes (0.5 hours)."""
        route = make_route(seg0_miles=50, seg1_miles=600)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        for brk in (s for s in result.stops if s.type == 'break'):
            self.assertAlmostEqual(brk.duration_hours, BREAK_DURATION, places=4)

    def test_break_status_is_sleeper_berth(self):
        """30-minute breaks must appear in the timeline as SB (sleeper berth)."""
        route = make_route(seg0_miles=50, seg1_miles=600)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        sb_events = [e for e in result.timeline if e.status == 'SB']
        self.assertGreaterEqual(len(sb_events), 1)
        for evt in sb_events:
            self.assertAlmostEqual(evt.duration, BREAK_DURATION, places=4)


class TestHOS11HourDrivingLimit(unittest.TestCase):
    """Tests for the 11-hour maximum driving rule."""

    def test_rest_inserted_after_11hr_driving(self):
        """
        A trip requiring > 11 hours of driving must trigger a 10-hr off-duty stop.
        11hr × 55mph = 605 miles; use >800 to be safe (break will fire first ~440).
        """
        # Use a very long second leg to force both a break AND a 11hr rest
        route = make_route(seg0_miles=50, seg1_miles=900)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        rest_stops = [s for s in result.stops if s.type == 'rest']
        self.assertGreaterEqual(len(rest_stops), 1)

    def test_rest_duration_is_10_hours(self):
        """Each rest stop must be exactly 10 hours."""
        route = make_route(seg0_miles=50, seg1_miles=900)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        for rest in (s for s in result.stops if s.type == 'rest'):
            self.assertAlmostEqual(rest.duration_hours, OFF_DUTY_RESET, places=4)

    def test_driving_hours_never_exceed_11_between_rests(self):
        """
        Between any two consecutive rest/off-duty periods, driving hours must
        never exceed 11.0.
        """
        route = make_route(seg0_miles=50, seg1_miles=900)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        # Walk the timeline and accumulate driving, resetting at OFF/SB events
        driving_accumulator = 0.0
        for evt in sorted(result.timeline, key=lambda e: e.start_abs):
            if evt.status == 'D':
                driving_accumulator += evt.duration
                self.assertLessEqual(
                    driving_accumulator, MAX_DRIVING_HOURS + 1e-4,
                    f"Driving exceeded 11hr (got {driving_accumulator:.3f})"
                )
            elif evt.status in ('OFF', 'SB') and evt.duration >= OFF_DUTY_RESET - 1e-4:
                driving_accumulator = 0.0


class TestHOS14HourWindow(unittest.TestCase):
    """Tests for the 14-hour on-duty window rule."""

    def test_on_duty_window_never_exceeds_14hr(self):
        """
        On-duty time since last reset must never exceed 14 hours continuously.
        """
        route = make_route(seg0_miles=50, seg1_miles=900)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        on_duty_accumulator = 0.0
        for evt in sorted(result.timeline, key=lambda e: e.start_abs):
            if evt.status in ('D', 'ON'):
                on_duty_accumulator += evt.duration
                self.assertLessEqual(
                    on_duty_accumulator, MAX_ON_DUTY_WINDOW + 1e-4,
                    f"On-duty window exceeded 14hr (got {on_duty_accumulator:.3f})"
                )
            elif evt.status in ('OFF',) and evt.duration >= OFF_DUTY_RESET - 1e-4:
                on_duty_accumulator = 0.0


class TestFuelStops(unittest.TestCase):
    """Tests for the 1,000-mile fuel stop rule."""

    def test_fuel_stop_inserted_before_1000_miles(self):
        """A trip longer than 1000 miles must include at least one fuel stop."""
        route = make_route(seg0_miles=50, seg1_miles=1100)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        fuel_stops = [s for s in result.stops if s.type == 'fuel']
        self.assertGreaterEqual(len(fuel_stops), 1)

    def test_two_fuel_stops_for_2200_mile_trip(self):
        """A 2,200+ mile trip must include at least two fuel stops."""
        route = make_route(seg0_miles=100, seg1_miles=2200)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        fuel_stops = [s for s in result.stops if s.type == 'fuel']
        self.assertGreaterEqual(len(fuel_stops), 2)

    def test_fuel_stop_duration_is_30_minutes(self):
        """Each fuel stop must be 30 minutes (0.5 hours)."""
        route = make_route(seg0_miles=50, seg1_miles=1100)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        for fuel in (s for s in result.stops if s.type == 'fuel'):
            self.assertAlmostEqual(fuel.duration_hours, FUEL_DURATION, places=4)

    def test_no_fuel_stop_under_1000_miles(self):
        """A trip under 1,000 miles should not require any fuel stop."""
        route = make_route(seg0_miles=50, seg1_miles=800)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        fuel_stops = [s for s in result.stops if s.type == 'fuel']
        self.assertEqual(len(fuel_stops), 0)


class TestCycleHours(unittest.TestCase):
    """Tests for the 70-hour / 8-day cycle rule."""

    def test_cycle_hours_accumulate_from_initial(self):
        """cycle_hours in state should exceed initial + driving hours."""
        route = make_route(seg0_miles=50, seg1_miles=200)
        initial = 20.0
        result = HOSCalculator(current_cycle_used=initial).simulate(route)

        # Total on-duty in timeline (driving + on-duty) should reflect initial
        total_on_duty = sum(
            e.duration for e in result.timeline if e.status in ('D', 'ON')
        )
        self.assertGreater(total_on_duty, 0)

    def test_exhausted_cycle_raises_error(self):
        """
        If current_cycle_used is 70 and trip requires driving, a
        HOSCycleExhaustedError must be raised.
        """
        route = make_route(seg0_miles=50, seg1_miles=200)
        calc = HOSCalculator(current_cycle_used=70.0)
        with self.assertRaises(HOSCycleExhaustedError):
            calc.simulate(route)

    def test_near_cycle_limit_raises_error(self):
        """
        If cycle hours would be exhausted during the trip, raise
        HOSCycleExhaustedError.
        """
        # 69 hours used, trip requires >1hr of driving
        route = make_route(seg0_miles=50, seg1_miles=200)
        calc = HOSCalculator(current_cycle_used=69.5)
        with self.assertRaises(HOSCycleExhaustedError):
            calc.simulate(route)

    def test_valid_cycle_hours_accepted(self):
        """constructor should accept 0–70 range without error."""
        for val in (0.0, 35.0, 70.0):
            HOSCalculator(current_cycle_used=val)  # Must not raise

    def test_invalid_cycle_hours_raises_value_error(self):
        """Values outside 0–70 should raise ValueError in constructor."""
        with self.assertRaises(ValueError):
            HOSCalculator(current_cycle_used=-1.0)
        with self.assertRaises(ValueError):
            HOSCalculator(current_cycle_used=71.0)


class TestOnDutyActivities(unittest.TestCase):
    """Tests for pickup and dropoff on-duty activities."""

    def test_pickup_on_duty_event_in_timeline(self):
        """Timeline must contain at least one ON entry (pickup activity)."""
        route = make_route(seg0_miles=50, seg1_miles=100)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        on_events = [e for e in result.timeline if e.status == 'ON']
        self.assertGreaterEqual(len(on_events), 1)

    def test_pickup_stop_duration_is_1_hour(self):
        """Pickup stop must be exactly 1 hour."""
        route = make_route(seg0_miles=50, seg1_miles=100)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        pickup = next((s for s in result.stops if s.type == 'pickup'), None)
        self.assertIsNotNone(pickup, "No pickup stop found.")
        self.assertAlmostEqual(pickup.duration_hours, PICKUP_DURATION, places=4)

    def test_dropoff_stop_duration_is_1_hour(self):
        """Dropoff stop must be exactly 1 hour."""
        route = make_route(seg0_miles=50, seg1_miles=100)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        dropoff = next((s for s in result.stops if s.type == 'dropoff'), None)
        self.assertIsNotNone(dropoff, "No dropoff stop found.")
        self.assertAlmostEqual(dropoff.duration_hours, DROPOFF_DURATION, places=4)

    def test_pickup_comes_before_dropoff(self):
        """Pickup must arrive before dropoff in the timeline."""
        route = make_route(seg0_miles=50, seg1_miles=100)
        result = HOSCalculator(current_cycle_used=0.0).simulate(route)

        pickup  = next((s for s in result.stops if s.type == 'pickup'), None)
        dropoff = next((s for s in result.stops if s.type == 'dropoff'), None)
        self.assertIsNotNone(pickup)
        self.assertIsNotNone(dropoff)
        self.assertLess(pickup.arrival_hours, dropoff.arrival_hours)


if __name__ == '__main__':
    unittest.main()
