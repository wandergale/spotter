from rest_framework import serializers


class TripRequestSerializer(serializers.Serializer):
    current_location = serializers.CharField(max_length=500)
    pickup_location = serializers.CharField(max_length=500)
    dropoff_location = serializers.CharField(max_length=500)
    current_cycle_used = serializers.FloatField(min_value=0.0, max_value=70.0)

    def validate(self, data):
        # Ensure locations are not blank after stripping
        for field in ('current_location', 'pickup_location', 'dropoff_location'):
            if not data[field].strip():
                raise serializers.ValidationError({field: 'Location cannot be blank.'})
        return data
