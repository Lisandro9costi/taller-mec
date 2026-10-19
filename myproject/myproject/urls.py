from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render

from . import views

def home(request):
    return render(request, "home.html")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("admin-login/", views.admin_login_view, name="admin_login"),
    path("logout/", views.logout_view, name="logout"),
    path("taller/", include("taller.urls")),
]
