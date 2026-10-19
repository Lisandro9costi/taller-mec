from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection
from taller.forms import LoginForm


def admin_login_view(request):
    form = LoginForm()
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, rol, username, nombre FROM personas "
                    "WHERE username = %s AND password = %s AND rol = 'admin'",
                    [form.cleaned_data["username"], form.cleaned_data["password"]],
                )
                row = cursor.fetchone()
            if row is None:
                messages.error(request, "Usuario o contrasena incorrectos")
            else:
                persona_id, rol, username, nombre = row
                request.session["persona_id"] = persona_id
                request.session["rol"] = rol
                request.session["username"] = username
                request.session["nombre"] = nombre
                return redirect("taller:dashboard")
    return render(request, "login_admin.html", {"form": form})


def logout_view(request):
    request.session.flush()
    return redirect("admin_login")
