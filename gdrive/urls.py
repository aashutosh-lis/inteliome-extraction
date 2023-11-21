from django.urls import path

from gdrive.views import gdrive_views

urlpatterns = [
    path("gettoken", gdrive_views.AuthenticationView.as_view()),
    path("oauth2callback", gdrive_views.OauthCallbackView.as_view()),
    path("extract", gdrive_views.ExtractionView.as_view()),
]
