from django.urls import include, path


urlpatterns = [
    path("review/", include("review.urls")),
]
