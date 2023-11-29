from django.urls import path

from gdrive.view.gdrive_views import ExtractionView

urlpatterns = [
    path("extract", ExtractionView.as_view()),
]
