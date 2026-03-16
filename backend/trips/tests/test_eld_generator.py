"""
Unit tests for the ELD Generator.

Tests cover:
  - Midnight splitting (events that cross day boundaries)
  - Per-day summary totals
  - Day grouping and chronological ordering
  - Gap filling (OFF-duty before first event)
"""

import unittest
from datetime import date
from trips.services.hos_calculator import TimelineEvent, TripSimulationResult
from trips.services.eld_generator import ELDGenerator


def make_result(events: list[TimelineEvent]) -> TripSimulationResult:
    """Build a minimal TripSimulationResult from a list of events."""
    return TripSimulationResult(
        stops=[],
        timeline=events,
        total_driving_hours=sum(e.duration for e in events if e.status == 'D'),
        total_trip_hours=events[-1].end_abs if events else 0.0,
    )


START = date(2025, 1, 1)


class TestELDGeneratorBasic(unittest.TestCase):

    def test_single_day_event_in_correct_day(self):
        """An event within hours 0–24 should appear on day 0."""
        events = [
            TimelineEvent(status='D', start_abs=6.0, end_abs=10.0, location='Test'),
        ]
        result = make_result(events)
        logs = ELDGenerator().generate(result, trip_start_date=START)

        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]['date'], '2025-01-01')

    def test_entry_hours_are_within_day_bounds(self):
        """All start_hour and end_hour values must be in [0.0, 24.0]."""
        events = [
            TimelineEvent(status='D', start_abs=6.0, end_abs=10.0, location='Test'),
            TimelineEvent(status='OFF', start_abs=10.0, end_abs=20.0, location='Rest'),
        ]
        result = make_result(events)
        logs = ELDGenerator().generate(result, trip_start_date=START)

        for day in logs:
            for entry in day['entries']:
                self.assertGreaterEqual(entry['start_hour'], 0.0)
                self.assertLessEqual(entry['end_hour'], 24.0)
                self.assertGreater(entry['end_hour'], entry['start_hour'])


class TestMidnightSplit(unittest.TestCase):

    def test_event_spanning_midnight_is_split(self):
        """
        An event from hour 22.0 to 26.0 (spanning midnight) must be split into
        two entries: day 0 (22.0→24.0) and day 1 (0.0→2.0).
        """
        events = [
            TimelineEvent(status='OFF', start_abs=22.0, end_abs=26.0, location='Rest Stop'),
        ]
        result = make_result(events)
        logs = ELDGenerator().generate(result, trip_start_date=START)

        self.assertEqual(len(logs), 2, "Expected 2 days for midnight-spanning event.")

        day0 = logs[0]
        day1 = logs[1]

        # Find the relevant OFF entry in each day (not the gap-fill OFF entries)
        day0_offs = [e for e in day0['entries'] if e['status'] == 'OFF' and e['end_hour'] == 24.0]
        day1_offs = [e for e in day1['entries'] if e['status'] == 'OFF' and e['start_hour'] == 0.0]

        self.assertTrue(len(day0_offs) >= 1, "Day 0 should have OFF ending at 24.0")
        self.assertTrue(len(day1_offs) >= 1, "Day 1 should have OFF starting at 0.0")

    def test_day_dates_are_consecutive(self):
        """Days produced by a midnight-spanning event must have consecutive dates."""
        events = [
            TimelineEvent(status='D', start_abs=6.0, end_abs=11.0, location='Driving'),
            TimelineEvent(status='OFF', start_abs=23.0, end_abs=33.0, location='Rest'),
        ]
        result = make_result(events)
        logs = ELDGenerator().generate(result, trip_start_date=START)

        self.assertGreaterEqual(len(logs), 2)
        for i in range(1, len(logs)):
            d_prev = date.fromisoformat(logs[i - 1]['date'])
            d_curr = date.fromisoformat(logs[i]['date'])
            self.assertEqual((d_curr - d_prev).days, 1)

    def test_multi_day_event_spans_three_days(self):
        """An event from hour 23.0 to 49.0 must appear on days 0, 1, and 2."""
        events = [
            TimelineEvent(status='OFF', start_abs=23.0, end_abs=49.0, location='Long Rest'),
        ]
        result = make_result(events)
        logs = ELDGenerator().generate(result, trip_start_date=START)

        self.assertEqual(len(logs), 3)

    def test_entry_durations_sum_to_original(self):
        """
        After splitting, the sum of all entry durations across days must equal
        the original event duration.
        """
        events = [
            TimelineEvent(status='OFF', start_abs=22.0, end_abs=26.0, location='Rest'),
        ]
        result = make_result(events)
        logs = ELDGenerator().generate(result, trip_start_date=START)

        total = sum(
            e['end_hour'] - e['start_hour']
            for day in logs
            for e in day['entries']
            if e['status'] == 'OFF' and e['location'] == 'Rest'
        )
        self.assertAlmostEqual(total, 4.0, places=4)


class TestSummary(unittest.TestCase):

    def test_summary_driving_hours_correct(self):
        """Summary driving_hours must match total D-status entry durations for the day."""
        events = [
            TimelineEvent(status='D',   start_abs=6.0, end_abs=9.0,  location='Drive'),
            TimelineEvent(status='ON',  start_abs=9.0, end_abs=10.0, location='Pickup'),
            TimelineEvent(status='D',   start_abs=10.0, end_abs=14.0, location='Drive'),
            TimelineEvent(status='OFF', start_abs=14.0, end_abs=24.0, location='Rest'),
        ]
        result = make_result(events)
        logs = ELDGenerator().generate(result, trip_start_date=START)

        summary = logs[0]['summary']
        self.assertAlmostEqual(summary['driving_hours'], 7.0, places=4)

    def test_summary_on_duty_hours_correct(self):
        """Summary on_duty_hours must match total ON-status entry durations."""
        events = [
            TimelineEvent(status='ON',  start_abs=6.0, end_abs=7.0,  location='Pickup'),
            TimelineEvent(status='D',   start_abs=7.0, end_abs=10.0, location='Drive'),
            TimelineEvent(status='OFF', start_abs=10.0, end_abs=20.0, location='Rest'),
        ]
        result = make_result(events)
        logs = ELDGenerator().generate(result, trip_start_date=START)

        summary = logs[0]['summary']
        self.assertAlmostEqual(summary['on_duty_hours'], 1.0, places=4)

    def test_summary_all_keys_present(self):
        """Summary must include all four HOS status keys."""
        events = [
            TimelineEvent(status='D', start_abs=0.0, end_abs=5.0, location='Drive'),
        ]
        result = make_result(events)
        logs = ELDGenerator().generate(result, trip_start_date=START)

        summary = logs[0]['summary']
        self.assertIn('driving_hours', summary)
        self.assertIn('on_duty_hours', summary)
        self.assertIn('sleeper_berth_hours', summary)
        self.assertIn('off_duty_hours', summary)


class TestDayOrdering(unittest.TestCase):

    def test_days_are_in_chronological_order(self):
        """Days in the output must be ordered from earliest to latest date."""
        events = [
            TimelineEvent(status='D',   start_abs=6.0,  end_abs=11.0, location='Drive'),
            TimelineEvent(status='OFF', start_abs=11.0, end_abs=21.0, location='Rest'),
            TimelineEvent(status='D',   start_abs=21.0, end_abs=30.0, location='Drive'),
            TimelineEvent(status='OFF', start_abs=30.0, end_abs=40.0, location='Rest'),
        ]
        result = make_result(events)
        logs = ELDGenerator().generate(result, trip_start_date=START)

        dates = [date.fromisoformat(d['date']) for d in logs]
        self.assertEqual(dates, sorted(dates))

    def test_start_date_respected(self):
        """The first day's date must match the trip_start_date parameter."""
        events = [
            TimelineEvent(status='D', start_abs=0.0, end_abs=5.0, location='Drive'),
        ]
        result = make_result(events)
        start = date(2025, 6, 15)
        logs = ELDGenerator().generate(result, trip_start_date=start)

        self.assertEqual(logs[0]['date'], '2025-06-15')


if __name__ == '__main__':
    unittest.main()
