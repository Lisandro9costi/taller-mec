from django.urls import path
from . import views

app_name = "taller"

urlpatterns = [
    path("", views.clientes_lista, name="clientes_lista"),
    path("crear-cliente/", views.crear_cliente, name="crear_cliente"),
    path("<int:cliente_id>/", views.panel_cliente, name="panel_cliente"),
    path("<int:cliente_id>/agregar-vehiculo/", views.agregar_vehiculo, name="agregar_vehiculo"),
    path("<int:cliente_id>/enviar-solicitud/", views.enviar_solicitud, name="enviar_solicitud"),
    path("solicitar-empleo/", views.solicitar_empleo, name="solicitar_empleo"),
    path("admin/", views.dashboard, name="dashboard"),
    path("admin/clientes/", views.admin_clientes, name="admin_clientes"),
    path("admin/vehiculos/", views.vehiculos, name="vehiculos"),
    path("admin/ordenes/", views.ordenes, name="ordenes"),
    path("admin/empleados/", views.empleados, name="empleados"),
    path("admin/solicitudes/", views.solicitudes_empleo, name="solicitudes"),
    path("admin/solicitudes-taller/", views.solicitudes_taller, name="solicitudes_taller"),
    path("admin/solicitudes-taller/<int:solicitud_id>/asignar/", views.asignar_solicitud, name="asignar_solicitud"),
    path("solicitudes/<int:solicitud_id>/aceptar/", views.aceptar_solicitud, name="aceptar_solicitud"),
    path("admin/solicitudes/empleo/<int:solicitud_id>/aprobar/", views.aprobar_solicitud, name="aprobar_solicitud"),
    path("admin/solicitudes/empleo/<int:solicitud_id>/rechazar/", views.rechazar_solicitud, name="rechazar_solicitud"),
    path("panel-empleado/", views.panel_empleado, name="panel_empleado"),
]
