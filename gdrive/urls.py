from django.urls import path

from gdrive.views.gdrive_views import ExtractionView

urlpatterns = [
    path("extract", ExtractionView.as_view()),
]
