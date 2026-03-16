"""
eld_generator.py
~~~~~~~~~~~~~~~~
Converts a flat list of TimelineEvent objects (from HOSCalculator) into
per-day ELD log entries suitable for rendering a 24-hour horizontal bar chart.

Key responsibilities:
  1. Group timeline events by calendar day.
  2. Split any event that spans midnight into two partial entries — one ending
     at 24.0 on day N, one starting at 0.0 on day N+1.
  3. Compute per-day summary totals (driving, on_duty, sleeper_berth, off_duty).
  4. Return ISO-formatted date strings anchored to a caller-supplied start date.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import date, timedelta

from .hos_calculator import TimelineEvent, TripSimulationResult

logger = logging.getLogger(__name__)

# Map HOS status codes to human-readable summary keys
STATUS_TO_KEY = {
    'D':   'driving_hours',
    'ON':  'on_duty_hours',
    'SB':  'sleeper_berth_hours',
    'OFF': 'off_duty_hours',
}


@dataclass
class ELDEntry:
    """A single status block within a 24-hour ELD log grid."""
    status: str         # 'D' | 'ON' | 'SB' | 'OFF'
    start_hour: float   # 0.0 – 24.0 within this calendar day
    end_hour: float     # 0.0 – 24.0 within this calendar day
    location: str       # Location description shown on the log

    @property
    def duration(self) -> float:
        return round(self.end_hour - self.start_hour, 4)


class ELDGenerator:
    """
    Transforms a TripSimulationResult timeline into a list of per-day ELD logs.

    Each log entry has:
      - date: ISO date string (e.g. "2025-01-01")
      - entries: list of ELDEntry dicts (status, start_hour, end_hour, location)
      - summary: {driving_hours, on_duty_hours, sleeper_berth_hours, off_duty_hours}
    """

    def generate(
        self,
        trip_result: TripSimulationResult,
        trip_start_date: date | None = None,
    ) -> list[dict]:
        """
        Generate per-day ELD logs from a simulation result.

        Args:
            trip_result: Output of HOSCalculator.simulate().
            trip_start_date: The calendar date of trip start (day 0).
                             Defaults to today if not provided.

        Returns:
            List of dicts, one per calendar day, ordered chronologically.
        """
        if trip_start_date is None:
            trip_start_date = date.today()

        # day_index → list of ELDEntry
        days: dict[int, list[ELDEntry]] = defaultdict(list)

        for event in trip_result.timeline:
            self._assign_event(event, days)

        # Build the final output list
        result = []
        for day_idx in sorted(days.keys()):
            entries = days[day_idx]
            log_date = trip_start_date + timedelta(days=day_idx)

            # Fill any uncovered time at the start/end of the day with OFF-duty
            entries = self._fill_gaps(entries)

            summary = self._compute_summary(entries)

            result.append({
                'date': log_date.isoformat(),
                'entries': [self._entry_to_dict(e) for e in entries],
                'summary': summary,
            })

        logger.info("ELD generator produced %d day(s) of logs.", len(result))
        return result

    # ── Core splitting logic ───────────────────────────────────────────────────

    def _assign_event(self, event: TimelineEvent, days: dict):
        """
        Assign a TimelineEvent to one or more calendar days.
        Splits events that cross midnight boundaries.
        """
        start_abs = event.start_abs
        end_abs   = event.end_abs

        if end_abs <= start_abs:
            return  # Zero-duration event; skip.

        current_start = start_abs
        while current_start < end_abs - 1e-9:
            day_idx   = int(current_start // 24)
            day_start = day_idx * 24.0          # absolute hour at midnight of this day
            day_end   = day_start + 24.0        # absolute hour at next midnight

            # Clamp end to this day's boundary
            current_end = min(end_abs, day_end)

            # Convert absolute hours to within-day hours (0.0 – 24.0)
            within_start = current_start - day_start
            within_end   = current_end   - day_start

            if within_end - within_start > 1e-6:
                days[day_idx].append(ELDEntry(
                    status=event.status,
                    start_hour=round(within_start, 4),
                    end_hour=round(within_end, 4),
                    location=event.location,
                ))

            current_start = current_end

    # ── Gap filling ────────────────────────────────────────────────────────────

    def _fill_gaps(self, entries: list[ELDEntry]) -> list[ELDEntry]:
        """
        Ensure the 24-hour log is contiguous.  Any gap not covered by an entry
        is filled with an OFF-duty entry (e.g., the portion before the first
        event if the trip started mid-day).
        """
        if not entries:
            return [ELDEntry(status='OFF', start_hour=0.0, end_hour=24.0, location='')]

        # Sort by start_hour
        sorted_entries = sorted(entries, key=lambda e: e.start_hour)
        filled: list[ELDEntry] = []

        # Gap before first entry — use empty location so callers can distinguish
        # gap-fill padding from real event entries when summing durations.
        if sorted_entries[0].start_hour > 1e-6:
            filled.append(ELDEntry(
                status='OFF',
                start_hour=0.0,
                end_hour=sorted_entries[0].start_hour,
                location='',
            ))

        filled.extend(sorted_entries)
        return filled

    # ── Summary ────────────────────────────────────────────────────────────────

    def _compute_summary(self, entries: list[ELDEntry]) -> dict:
        totals = {
            'off_duty_hours': 0.0,
            'sleeper_berth_hours': 0.0,
            'driving_hours': 0.0,
            'on_duty_hours': 0.0,
        }
        for entry in entries:
            key = STATUS_TO_KEY.get(entry.status)
            if key:
                totals[key] = round(totals[key] + entry.duration, 4)
        return totals

    # ── Serialization ──────────────────────────────────────────────────────────

    @staticmethod
    def _entry_to_dict(entry: ELDEntry) -> dict:
        return {
            'status': entry.status,
            'start_hour': entry.start_hour,
            'end_hour': entry.end_hour,
            'location': entry.location,
        }
