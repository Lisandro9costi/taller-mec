from django import forms


class LoginForm(forms.Form):
    username = forms.CharField(max_length=255)
    password = forms.CharField(widget=forms.PasswordInput)


class ClienteForm(forms.Form):
    nombre = forms.CharField(max_length=255)
    apellido = forms.CharField(max_length=255)
    dni = forms.CharField(max_length=50)
    direccion = forms.CharField(max_length=255, required=False)
    contacto = forms.CharField(max_length=255, required=False)


class VehiculoForm(forms.Form):
    matricula = forms.CharField(max_length=50)
    marca = forms.CharField(max_length=255)
    modelo = forms.CharField(max_length=255)
    color = forms.CharField(max_length=100)


class SolicitudForm(forms.Form):
    matricula = forms.CharField(max_length=50)
    marca = forms.CharField(max_length=255)
    modelo = forms.CharField(max_length=255)
    color = forms.CharField(max_length=100)


class PersonaSolicitudEmpleoForm(forms.Form):
    username = forms.CharField(max_length=255)
    nombre = forms.CharField(max_length=255)
    apellido = forms.CharField(max_length=255)
    dni = forms.CharField(max_length=50)
    contacto = forms.CharField(max_length=255)
    especialidad = forms.CharField(max_length=255)


class AsignarSolicitudForm(forms.Form):
    empleado_id = forms.IntegerField()
