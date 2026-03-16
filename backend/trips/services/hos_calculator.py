"""
hos_calculator.py
~~~~~~~~~~~~~~~~~
FMCSA HOS (Hours of Service) calculator for property-carrying drivers under
the 70-hour / 8-day cycle.

Rules implemented (49 CFR Part 395):
  • 11-Hour Driving Limit   — max 11 hours driving after 10 consecutive off-duty.
  • 14-Hour Window          — cannot drive beyond 14th consecutive hour on-duty.
  • 30-Minute Break         — must rest 30 min after 8 cumulative driving hours.
  • 70-Hour / 8-Day Cycle   — cannot drive after 70 total on-duty hours in 8 days.
  • 10-Hour Off-Duty Reset  — 10 consecutive off-duty hours resets driving/window.

No adverse-condition extensions are modelled.

The simulator uses a *constraint-driven* approach: rather than checking every
hour, it advances the clock to the nearest constraint boundary.  This handles
fractional-hour stops correctly and avoids floating-point drift.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# ── FMCSA Constants ────────────────────────────────────────────────────────────

MAX_DRIVING_HOURS: float = 11.0         # Max driving before mandatory 10hr off
MAX_ON_DUTY_WINDOW: float = 14.0        # Window from first on-duty to last drive
BREAK_TRIGGER_HOURS: float = 8.0        # Drive hours before mandatory 30-min break
BREAK_DURATION: float = 0.5             # 30-minute break (hours)
OFF_DUTY_RESET: float = 10.0            # Hours off-duty for full reset
CYCLE_LIMIT: float = 70.0              # 70-hour / 8-day on-duty cap

PICKUP_DURATION: float = 1.0           # On-duty time at pickup (hours)
DROPOFF_DURATION: float = 1.0          # On-duty time at dropoff (hours)
FUEL_DURATION: float = 0.5             # Fuel stop (hours)
FUEL_INTERVAL_MILES: float = 1000.0    # Max miles between fuel stops

AVERAGE_SPEED_MPH: float = 55.0        # Default if route API gives no duration

# Trip start anchor — all absolute hours are offset from this
TRIP_START = datetime(2025, 1, 1, 6, 0, 0, tzinfo=timezone.utc)  # 06:00 UTC Day 1


# ── Dataclasses ────────────────────────────────────────────────────────────────

@dataclass
class Stop:
    """A single planned stop along the trip."""
    type: str           # 'pickup' | 'dropoff' | 'rest' | 'break' | 'fuel'
    location: str       # Human-readable location / city description
    lat: float
    lon: float
    arrival_hours: float    # Absolute hours from trip start
    departure_hours: float  # Absolute hours from trip start

    @property
    def duration_hours(self) -> float:
        return self.departure_hours - self.arrival_hours

    @property
    def arrival_iso(self) -> str:
        dt = TRIP_START + timedelta(hours=self.arrival_hours)
        return dt.isoformat()

    @property
    def departure_iso(self) -> str:
        dt = TRIP_START + timedelta(hours=self.departure_hours)
        return dt.isoformat()


@dataclass
class TimelineEvent:
    """
    A continuous period of a single HOS status.
    Used by ELDGenerator to build daily log grids.
    """
    status: str         # 'D' | 'ON' | 'SB' | 'OFF'
    start_abs: float    # Absolute hours from trip start
    end_abs: float      # Absolute hours from trip start
    location: str       # Description for the ELD log

    @property
    def duration(self) -> float:
        return self.end_abs - self.start_abs


@dataclass
class HOSState:
    """
    Mutable simulator state.  All time values are in hours.
    """
    clock: float = 0.0                  # Hours elapsed since trip start
    driving_since_reset: float = 0.0    # Resets after 10hr off-duty (11hr limit)
    on_duty_since_reset: float = 0.0    # Resets after 10hr off-duty (14hr window)
    cycle_hours: float = 0.0            # Rolling 70hr/8day accumulator
    miles_since_fuel: float = 0.0       # Miles driven since last fuel stop
    driving_since_break: float = 0.0    # Driving since last 30-min break

    def reset_after_off_duty(self):
        """Apply the 10-hour off-duty reset to driving/window counters."""
        self.driving_since_reset = 0.0
        self.on_duty_since_reset = 0.0
        self.driving_since_break = 0.0


@dataclass
class TripSimulationResult:
    stops: list[Stop]
    timeline: list[TimelineEvent]
    total_driving_hours: float
    total_trip_hours: float


# ── Custom Exceptions ──────────────────────────────────────────────────────────

class HOSCycleExhaustedError(Exception):
    """Raised when the driver's 70hr cycle is exhausted before trip completion."""


# ── Calculator ─────────────────────────────────────────────────────────────────

class HOSCalculator:
    """
    Simulates an ELD trip against FMCSA HOS rules.

    Usage:
        calc = HOSCalculator(current_cycle_used=20.0)
        result = calc.simulate(route_data)

    `route_data` is the dict returned by RouteService.get_route(), which must
    contain a 'segments' list of RouteSegment objects.
    """

    def __init__(self, current_cycle_used: float = 0.0):
        if current_cycle_used < 0 or current_cycle_used > CYCLE_LIMIT:
            raise ValueError(
                f"current_cycle_used must be between 0 and {CYCLE_LIMIT}."
            )
        self._initial_cycle = current_cycle_used

    def simulate(self, route_data: dict) -> TripSimulationResult:
        """
        Run the full trip simulation.  Returns a TripSimulationResult with all
        stops and a flat timeline of status events.
        """
        segments = route_data['segments']
        coords = route_data.get('coords', [])

        # Derive location names from coords (fall back to generic names)
        def loc_name(idx: int, default: str) -> str:
            if coords and idx < len(coords):
                name = coords[idx].display_name
                # Trim very long Nominatim display names to the first two parts
                parts = name.split(',')
                return ', '.join(p.strip() for p in parts[:2])
            return default

        current_loc = loc_name(0, 'Current Location')
        pickup_loc  = loc_name(1, 'Pickup Location')
        dropoff_loc = loc_name(2, 'Dropoff Location')

        # Coordinate helpers for stops (lat/lon at each waypoint)
        def coord_lat(idx: int) -> float:
            return coords[idx].lat if coords and idx < len(coords) else 0.0
        def coord_lon(idx: int) -> float:
            return coords[idx].lon if coords and idx < len(coords) else 0.0

        state = HOSState(cycle_hours=self._initial_cycle)
        stops: list[Stop] = []
        timeline: list[TimelineEvent] = []

        # ── Phase 0: Pre-trip / start at current location (brief ON duty) ──────
        # The driver is already on-duty (assumed starting a new shift).
        # We begin the clock at 0 and immediately enter driving toward pickup.

        # ── Phase 1: Drive current → pickup ───────────────────────────────────
        seg0 = segments[0]
        self._drive_segment(
            state=state,
            segment=seg0,
            origin_name=current_loc,
            dest_name=pickup_loc,
            stops=stops,
            timeline=timeline,
        )

        # ── Phase 2: On-duty (not driving) — pickup activity ──────────────────
        self._on_duty_activity(
            state=state,
            duration=PICKUP_DURATION,
            stop_type='pickup',
            location=pickup_loc,
            lat=coord_lat(1),
            lon=coord_lon(1),
            stops=stops,
            timeline=timeline,
        )

        # ── Phase 3: Drive pickup → dropoff ───────────────────────────────────
        seg1 = segments[1] if len(segments) > 1 else segments[0]
        self._drive_segment(
            state=state,
            segment=seg1,
            origin_name=pickup_loc,
            dest_name=dropoff_loc,
            stops=stops,
            timeline=timeline,
        )

        # ── Phase 4: On-duty (not driving) — dropoff activity ─────────────────
        self._on_duty_activity(
            state=state,
            duration=DROPOFF_DURATION,
            stop_type='dropoff',
            location=dropoff_loc,
            lat=coord_lat(2) if len(coords) > 2 else coord_lat(1),
            lon=coord_lon(2) if len(coords) > 2 else coord_lon(1),
            stops=stops,
            timeline=timeline,
        )

        # ── Phase 5: Post-trip off-duty ────────────────────────────────────────
        # Add a trailing OFF period so the ELD grid ends cleanly.
        off_start = state.clock
        off_end = off_start + OFF_DUTY_RESET
        timeline.append(TimelineEvent(
            status='OFF',
            start_abs=off_start,
            end_abs=off_end,
            location=dropoff_loc,
        ))

        total_driving = sum(
            e.duration for e in timeline if e.status == 'D'
        )

        return TripSimulationResult(
            stops=stops,
            timeline=timeline,
            total_driving_hours=round(total_driving, 2),
            total_trip_hours=round(state.clock, 2),
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _drive_segment(
        self,
        state: HOSState,
        segment,
        origin_name: str,
        dest_name: str,
        stops: list,
        timeline: list,
    ):
        """
        Simulate driving a single route segment.  Inserts mandatory stops at
        the correct constraint boundaries (break, 11hr limit, 14hr window,
        fuel interval).

        The segment's distance_miles determines how many hours of driving are
        needed; we use AVERAGE_SPEED_MPH as the fallback speed, but prefer the
        segment's own duration_hours (which comes from the routing API).

        We interpolate location names between origin and destination based on
        the fraction of distance completed.
        """
        total_drive_hours = segment.duration_hours  # From routing API
        if total_drive_hours <= 0:
            total_drive_hours = segment.distance_miles / AVERAGE_SPEED_MPH

        remaining_drive = total_drive_hours
        remaining_miles = segment.distance_miles
        speed = segment.distance_miles / total_drive_hours if total_drive_hours > 0 else AVERAGE_SPEED_MPH

        while remaining_drive > 1e-6:
            # ── Check 70-hour cycle ──────────────────────────────────────────
            cycle_remaining = CYCLE_LIMIT - state.cycle_hours
            if cycle_remaining <= 1e-6:
                raise HOSCycleExhaustedError(
                    f"Driver's 70-hour cycle is exhausted (used: "
                    f"{state.cycle_hours:.1f} hrs). The trip cannot be "
                    "completed without a 34-hour restart, which is outside "
                    "the scope of this simulation."
                )

            # ── Compute time until each constraint fires ──────────────────────
            time_to_break = BREAK_TRIGGER_HOURS - state.driving_since_break
            time_to_11hr  = MAX_DRIVING_HOURS - state.driving_since_reset
            time_to_14hr  = MAX_ON_DUTY_WINDOW - state.on_duty_since_reset
            time_to_fuel  = (FUEL_INTERVAL_MILES - state.miles_since_fuel) / speed
            time_to_cycle = cycle_remaining  # hours of driving available

            # Clamp negatives to zero (constraint already hit)
            time_to_break = max(time_to_break, 0.0)
            time_to_11hr  = max(time_to_11hr, 0.0)
            time_to_14hr  = max(time_to_14hr, 0.0)
            time_to_fuel  = max(time_to_fuel, 0.0)

            # Drive chunk = minimum of all constraints and remaining distance
            chunk = min(
                time_to_break,
                time_to_11hr,
                time_to_14hr,
                time_to_fuel,
                time_to_cycle,
                remaining_drive,
            )

            if chunk <= 1e-6:
                # A constraint fires immediately — determine which one and
                # handle it without advancing the driving clock.
                constraint = self._which_constraint(
                    time_to_break, time_to_11hr, time_to_14hr, time_to_fuel,
                    remaining_drive, cycle_remaining
                )
                loc = self._interpolate_location(
                    origin_name, dest_name,
                    1.0 - (remaining_drive / total_drive_hours)
                )
                self._handle_constraint(
                    state=state,
                    constraint=constraint,
                    location=loc,
                    lat=0.0,
                    lon=0.0,
                    stops=stops,
                    timeline=timeline,
                )
                continue

            # ── Advance driving state by chunk ───────────────────────────────
            drive_start = state.clock
            miles_chunk = chunk * speed
            progress_frac = 1.0 - (remaining_drive / total_drive_hours)
            loc = self._interpolate_location(origin_name, dest_name, progress_frac)

            state.clock                += chunk
            state.driving_since_reset  += chunk
            state.on_duty_since_reset  += chunk
            state.cycle_hours          += chunk
            state.miles_since_fuel     += miles_chunk
            state.driving_since_break  += chunk
            remaining_drive            -= chunk
            remaining_miles            -= miles_chunk

            timeline.append(TimelineEvent(
                status='D',
                start_abs=drive_start,
                end_abs=state.clock,
                location=loc,
            ))

            logger.debug(
                "Drove %.2fh → clock=%.2f | driving=%.2f/11 | "
                "window=%.2f/14 | cycle=%.2f/70 | miles_fuel=%.0f",
                chunk, state.clock,
                state.driving_since_reset, state.on_duty_since_reset,
                state.cycle_hours, state.miles_since_fuel,
            )

    def _which_constraint(
        self,
        t_break: float,
        t_11: float,
        t_14: float,
        t_fuel: float,
        remaining: float,
        cycle_rem: float,
    ) -> str:
        """Return the name of the constraint that fired (all ≈ 0)."""
        # Priority order: fuel > break > 11hr > 14hr
        # (break is less disruptive than a full reset, so check it before limits)
        if t_fuel <= 1e-6:
            return 'fuel'
        if t_break <= 1e-6:
            return 'break'
        if t_11 <= 1e-6:
            return 'rest_11'
        if t_14 <= 1e-6:
            return 'rest_14'
        if cycle_rem <= 1e-6:
            return 'cycle'
        return 'rest_11'  # fallback

    def _handle_constraint(
        self,
        state: HOSState,
        constraint: str,
        location: str,
        lat: float,
        lon: float,
        stops: list,
        timeline: list,
    ):
        """Insert the appropriate stop and update state for a fired constraint."""
        if constraint == 'fuel':
            self._insert_fuel_stop(state, location, lat, lon, stops, timeline)
        elif constraint == 'break':
            self._insert_break(state, location, lat, lon, stops, timeline)
        elif constraint in ('rest_11', 'rest_14', 'cycle'):
            self._insert_rest(state, location, lat, lon, stops, timeline)

    def _insert_break(self, state, location, lat, lon, stops, timeline):
        """Insert a mandatory 30-minute sleeper-berth break."""
        arr = state.clock
        dep = arr + BREAK_DURATION
        stops.append(Stop(
            type='break',
            location=location,
            lat=lat, lon=lon,
            arrival_hours=arr,
            departure_hours=dep,
        ))
        timeline.append(TimelineEvent(
            status='SB',
            start_abs=arr, end_abs=dep,
            location=location,
        ))
        state.clock += BREAK_DURATION
        state.on_duty_since_reset += BREAK_DURATION
        state.driving_since_break = 0.0  # Break resets the 8-hr counter
        logger.debug("Break inserted at clock=%.2f", arr)

    def _insert_rest(self, state, location, lat, lon, stops, timeline):
        """Insert a mandatory 10-hour off-duty rest period."""
        arr = state.clock
        dep = arr + OFF_DUTY_RESET
        stops.append(Stop(
            type='rest',
            location=location,
            lat=lat, lon=lon,
            arrival_hours=arr,
            departure_hours=dep,
        ))
        timeline.append(TimelineEvent(
            status='OFF',
            start_abs=arr, end_abs=dep,
            location=location,
        ))
        state.clock += OFF_DUTY_RESET
        state.reset_after_off_duty()
        logger.debug("10hr rest inserted at clock=%.2f", arr)

    def _insert_fuel_stop(self, state, location, lat, lon, stops, timeline):
        """Insert a 30-minute fuel stop (on-duty, not driving)."""
        arr = state.clock
        dep = arr + FUEL_DURATION
        stops.append(Stop(
            type='fuel',
            location=location,
            lat=lat, lon=lon,
            arrival_hours=arr,
            departure_hours=dep,
        ))
        timeline.append(TimelineEvent(
            status='ON',
            start_abs=arr, end_abs=dep,
            location=location,
        ))
        state.clock += FUEL_DURATION
        state.on_duty_since_reset += FUEL_DURATION
        state.cycle_hours += FUEL_DURATION
        state.miles_since_fuel = 0.0
        logger.debug("Fuel stop inserted at clock=%.2f", arr)

    def _on_duty_activity(
        self,
        state: HOSState,
        duration: float,
        stop_type: str,
        location: str,
        lat: float,
        lon: float,
        stops: list,
        timeline: list,
    ):
        """Record an on-duty (not driving) activity such as pickup or dropoff."""
        # Check 14-hour window: if the activity would push us past the window,
        # insert a rest first.
        remaining_window = MAX_ON_DUTY_WINDOW - state.on_duty_since_reset
        if remaining_window < duration:
            self._insert_rest(state, location, lat, lon, stops, timeline)

        arr = state.clock
        dep = arr + duration
        stops.append(Stop(
            type=stop_type,
            location=location,
            lat=lat, lon=lon,
            arrival_hours=arr,
            departure_hours=dep,
        ))
        timeline.append(TimelineEvent(
            status='ON',
            start_abs=arr, end_abs=dep,
            location=location,
        ))
        state.clock += duration
        state.on_duty_since_reset += duration
        state.cycle_hours += duration

    @staticmethod
    def _interpolate_location(origin: str, dest: str, frac: float) -> str:
        """Return a blended location description based on progress fraction."""
        if frac < 0.15:
            return f"En route from {origin}"
        if frac > 0.85:
            return f"Approaching {dest}"
        return f"En route ({origin} → {dest})"
