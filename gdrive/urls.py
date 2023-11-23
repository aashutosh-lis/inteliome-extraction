from django.urls import path

from .views import AuthenticationView, OauthCallbackView, ExtractionView

urlpatterns = [
    path("gettoken", AuthenticationView.as_view()),
    path("oauth2callback", OauthCallbackView.as_view()),
    path("extract", ExtractionView.as_view()),
]
