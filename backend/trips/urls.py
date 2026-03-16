from django.urls import path
from .views import TripCalculateView

urlpatterns = [
    path('trip/calculate/', TripCalculateView.as_view(), name='trip-calculate'),
]
