from django.db import models


class TripRequest(models.Model):
    """Stores an incoming trip calculation request for optional caching/auditing."""
    current_location = models.CharField(max_length=500)
    pickup_location = models.CharField(max_length=500)
    dropoff_location = models.CharField(max_length=500)
    current_cycle_used = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.current_location} → {self.pickup_location} → {self.dropoff_location}"


class TripResult(models.Model):
    """Caches the full computed response for a trip request."""
    trip_request = models.OneToOneField(
        TripRequest, on_delete=models.CASCADE, related_name='result'
    )
    response_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result for trip #{self.trip_request_id}"
