from django.urls import path
from . import views

urlpatterns = [
    path("", views.optimize_post, name="home"),
    path("optimize/", views.optimize_post, name="optimize_post"),
]
