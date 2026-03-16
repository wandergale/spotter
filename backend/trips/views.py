import logging
from datetime import date

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import TripRequestSerializer
from .services.route_service import RouteService, RouteServiceError
from .services.hos_calculator import HOSCalculator, HOSCycleExhaustedError
from .services.eld_generator import ELDGenerator

logger = logging.getLogger(__name__)


class TripCalculateView(APIView):
    """
    POST /api/trip/calculate/

    Accepts a trip request (current location, pickup, dropoff, cycle hours used)
    and returns the full route geometry, HOS-compliant stop schedule, and daily
    ELD log entries.
    """

    def post(self, request):
        serializer = TripRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        trip_start_date = date.today()

        # ── 1. Geocode + routing ──────────────────────────────────────────────
        try:
            route_svc = RouteService()
            coords = route_svc.geocode_locations(
                data['current_location'],
                data['pickup_location'],
                data['dropoff_location'],
            )
            route_data = route_svc.get_route(coords)
        except RouteServiceError as exc:
            logger.error("Route service error: %s", exc)
            return Response(
                {'error': str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            logger.exception("Unexpected error in route service")
            return Response(
                {'error': 'Failed to retrieve route. Please try again.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # ── 2. HOS simulation ─────────────────────────────────────────────────
        try:
            hos_calc = HOSCalculator(current_cycle_used=data['current_cycle_used'])
            trip_result = hos_calc.simulate(route_data)
        except HOSCycleExhaustedError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception("Unexpected error in HOS calculator")
            return Response(
                {'error': 'Failed to calculate HOS schedule.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── 3. ELD log generation ─────────────────────────────────────────────
        try:
            eld_gen = ELDGenerator()
            daily_logs = eld_gen.generate(trip_result, trip_start_date=trip_start_date)
        except Exception as exc:
            logger.exception("Unexpected error in ELD generator")
            return Response(
                {'error': 'Failed to generate ELD logs.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── 4. Build response ─────────────────────────────────────────────────
        stops_serialized = [
            {
                'type': stop.type,
                'location': {
                    'lat': stop.lat,
                    'lng': stop.lon,
                    'name': stop.location,
                },
                'arrival_time': stop.arrival_iso,
                'departure_time': stop.departure_iso,
                'duration_hours': round(stop.duration_hours, 2),
            }
            for stop in trip_result.stops
        ]

        response_body = {
            'route': route_data['route'],
            'stops': stops_serialized,
            'daily_logs': daily_logs,
            'total_trip_days': len(daily_logs),
            'total_driving_hours': round(trip_result.total_driving_hours, 2),
        }

        return Response(response_body, status=status.HTTP_200_OK)
