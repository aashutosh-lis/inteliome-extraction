from django.urls import path

from .views import ExtractionView

urlpatterns = [
    path("extract", ExtractionView.as_view()),
]
