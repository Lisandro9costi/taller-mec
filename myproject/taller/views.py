from types import SimpleNamespace

from django.db import connection
from django.http import Http404
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import (
    ClienteForm, VehiculoForm, SolicitudForm,
    PersonaSolicitudEmpleoForm, AsignarSolicitudForm,
)


def fetch_one(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        cols = [d[0] for d in cursor.description]
        row = cursor.fetchone()
        if row is None:
            return None
        return SimpleNamespace(**dict(zip(cols, row)))


def fetch_all(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        cols = [d[0] for d in cursor.description]
        return [SimpleNamespace(**dict(zip(cols, row))) for row in cursor.fetchall()]


def execute(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        return cursor.lastrowid


def es_rol(request, rol):
    return request.session.get("rol") == rol


def clientes_lista(request):
    clientes_list = fetch_all(
        "SELECT p.id, p.username, p.nombre, p.apellido, p.dni, p.direccion, p.contacto "
        "FROM personas p INNER JOIN clientes c ON p.id = c.persona_ptr_id "
        "WHERE p.rol = 'cliente' ORDER BY p.nombre"
    )
    return render(request, "taller/clientes_lista.html", {"clientes": clientes_list})


def crear_cliente(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            dni = form.cleaned_data["dni"]
            exists = fetch_one("SELECT 1 FROM personas WHERE dni = %s", [dni])
            if exists:
                messages.error(request, "Ya existe un cliente con ese DNI")
                return redirect("taller:clientes_lista")
            username = dni
            counter = 1
            while fetch_one("SELECT 1 FROM personas WHERE username = %s", [username]):
                username = f"{dni}_{counter}"
                counter += 1
            persona_id = execute(
                "INSERT INTO personas (username, password, rol, estado, nombre, apellido, dni, direccion, contacto) "
                "VALUES (%s, '', 'cliente', 'activo', %s, %s, %s, %s, %s)",
                [username, form.cleaned_data["nombre"], form.cleaned_data["apellido"],
                 dni, form.cleaned_data.get("direccion", ""), form.cleaned_data.get("contacto", "")],
            )
            execute("INSERT INTO clientes (persona_ptr_id) VALUES (%s)", [persona_id])
            messages.success(request, "Cliente creado correctamente")
            return redirect("taller:panel_cliente", cliente_id=persona_id)
        messages.error(request, "Datos invalidos")
        return redirect("taller:clientes_lista")
    return redirect("taller:clientes_lista")


def panel_cliente(request, cliente_id):
    cliente = fetch_one(
        "SELECT p.id, p.username, p.nombre, p.apellido, p.dni, p.direccion, p.contacto "
        "FROM personas p INNER JOIN clientes c ON p.id = c.persona_ptr_id WHERE p.id = %s",
        [cliente_id],
    )
    if not cliente:
        raise Http404
    vehiculos = fetch_all(
        "SELECT id, matricula, marca, modelo, color FROM vehiculos WHERE cliente_id = %s",
        [cliente_id],
    )
    ordenes = fetch_all(
        "SELECT o.id, o.tiempo_estimado, o.fecha_creacion, "
        "v.marca AS v_marca, v.modelo AS v_modelo, v.color AS v_color, v.matricula AS v_matricula, "
        "p_empleado.nombre AS e_nombre "
        "FROM ordenes o "
        "INNER JOIN vehiculos v ON o.vehiculo_id = v.id "
        "LEFT JOIN empleados em ON o.empleado_id = em.persona_ptr_id "
        "LEFT JOIN personas p_empleado ON em.persona_ptr_id = p_empleado.id "
        "WHERE o.cliente_id = %s ORDER BY o.fecha_creacion DESC",
        [cliente_id],
    )
    for o in ordenes:
        o.vehiculo = SimpleNamespace(marca=o.v_marca, modelo=o.v_modelo, color=o.v_color, matricula=o.v_matricula)
        o.empleado = SimpleNamespace(nombre=o.e_nombre)
    solicitudes_pendientes = fetch_one(
        "SELECT COUNT(*) AS cnt FROM solicitudes "
        "WHERE username = %s AND estado IN ('pendiente', 'asignada')",
        [cliente.username],
    )
    return render(request, "taller/panel_cliente.html", {
        "cliente": cliente,
        "vehiculos": vehiculos,
        "ordenes": ordenes,
        "solicitudes_pendientes": solicitudes_pendientes.cnt if solicitudes_pendientes else 0,
    })


def agregar_vehiculo(request, cliente_id):
    cliente = fetch_one("SELECT id FROM personas WHERE id = %s", [cliente_id])
    if not cliente:
        raise Http404
    if request.method == "POST":
        form = VehiculoForm(request.POST)
        if form.is_valid():
            execute(
                "INSERT INTO vehiculos (cliente_id, matricula, marca, modelo, color) VALUES (%s, %s, %s, %s, %s)",
                [cliente_id, form.cleaned_data["matricula"], form.cleaned_data["marca"],
                 form.cleaned_data["modelo"], form.cleaned_data["color"]],
            )
            messages.success(request, "Vehiculo agregado correctamente")
    return redirect("taller:panel_cliente", cliente_id=cliente_id)


def enviar_solicitud(request, cliente_id):
    cliente = fetch_one(
        "SELECT p.id, p.username, p.dni, p.nombre, p.apellido, p.direccion, p.contacto "
        "FROM personas p INNER JOIN clientes c ON p.id = c.persona_ptr_id WHERE p.id = %s",
        [cliente_id],
    )
    if not cliente:
        raise Http404
    if request.method == "POST":
        form = SolicitudForm(request.POST)
        if form.is_valid():
            pendiente = fetch_one(
                "SELECT 1 FROM solicitudes WHERE username = %s AND estado IN ('pendiente', 'asignada')",
                [cliente.username],
            )
            if pendiente:
                messages.error(request, "Ya tienes una solicitud pendiente. Espera a que sea aceptada o rechazada.")
                return redirect("taller:panel_cliente", cliente_id=cliente_id)
            execute(
                "INSERT INTO solicitudes (username, dni, nombre, apellido, direccion, contacto, "
                "matricula, marca, modelo, color, estado) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pendiente')",
                [cliente.username, cliente.dni, cliente.nombre, cliente.apellido,
                 cliente.direccion, cliente.contacto, form.cleaned_data["matricula"],
                 form.cleaned_data["marca"], form.cleaned_data["modelo"], form.cleaned_data["color"]],
            )
            messages.success(request, "Solicitud enviada al taller correctamente")
    return redirect("taller:panel_cliente", cliente_id=cliente_id)


def solicitar_empleo(request):
    if request.method == "POST":
        form = PersonaSolicitudEmpleoForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            username = data["username"]
            pendiente = fetch_one(
                "SELECT 1 FROM solicitudes_empleo WHERE username = %s AND estado = 'pendiente'",
                [username],
            )
            if pendiente:
                messages.error(request, "Ya tienes una solicitud de empleo pendiente.")
                return redirect("taller:solicitar_empleo")
            existing = fetch_one("SELECT id FROM personas WHERE username = %s", [username])
            if existing:
                persona_id = existing.id
            else:
                persona_id = execute(
                    "INSERT INTO personas (username, password, rol, estado, nombre, apellido, dni, contacto) "
                    "VALUES (%s, '', 'empleado', 'pendiente', %s, %s, %s, %s)",
                    [username, data["nombre"], data["apellido"], data["dni"], data["contacto"]],
                )
            execute(
                "INSERT INTO solicitudes_empleo (username, especialidad, estado) VALUES (%s, %s, 'pendiente')",
                [username, data["especialidad"]],
            )
            messages.success(request, "Solicitud de empleo enviada. Espera la aprobacion del administrador.")
            return redirect("taller:solicitar_empleo")
        messages.error(request, "Datos invalidos")
        return redirect("taller:solicitar_empleo")
    form = PersonaSolicitudEmpleoForm()
    return render(request, "taller/solicitar_empleo.html", {"form": form})


def panel_empleado(request):
    if not es_rol(request, "empleado"):
        return redirect("admin_login")
    persona_id = request.session.get("persona_id")
    username = request.session.get("username")
    empleado = fetch_one(
        "SELECT p.id, p.nombre, p.apellido, e.especialidad "
        "FROM personas p INNER JOIN empleados e ON p.id = e.persona_ptr_id WHERE p.id = %s",
        [persona_id],
    )
    if not empleado:
        raise Http404
    ordenes = fetch_all(
        "SELECT o.id, o.tiempo_estimado, o.fecha_creacion, "
        "v.marca AS v_marca, v.modelo AS v_modelo, v.matricula AS v_matricula, "
        "p_cliente.nombre AS c_nombre, p_cliente.apellido AS c_apellido, p_cliente.contacto AS c_contacto "
        "FROM ordenes o "
        "INNER JOIN vehiculos v ON o.vehiculo_id = v.id "
        "INNER JOIN personas p_cliente ON o.cliente_id = p_cliente.id "
        "WHERE o.empleado_id = %s ORDER BY o.fecha_creacion DESC",
        [persona_id],
    )
    for o in ordenes:
        o.vehiculo = SimpleNamespace(marca=o.v_marca, modelo=o.v_modelo, matricula=o.v_matricula)
        o.cliente = SimpleNamespace(nombre=o.c_nombre, apellido=o.c_apellido, contacto=o.c_contacto)
    asignadas = fetch_all(
        "SELECT id, nombre, apellido, matricula, marca, modelo, color, contacto, fecha_creacion "
        "FROM solicitudes WHERE empleado_asignado = %s AND estado = 'asignada' ORDER BY fecha_creacion DESC",
        [username],
    )
    return render(request, "taller/panel_empleado.html", {
        "empleado": empleado,
        "ordenes": ordenes,
        "asignadas": asignadas,
    })


def aceptar_solicitud(request, solicitud_id):
    if not es_rol(request, "empleado"):
        return redirect("admin_login")
    username = request.session.get("username")
    solicitud = fetch_one(
        "SELECT id, estado, empleado_asignado, matricula, marca, modelo, color, username "
        "FROM solicitudes WHERE id = %s",
        [solicitud_id],
    )
    if not solicitud:
        raise Http404
    if solicitud.estado == "asignada" and solicitud.empleado_asignado == username:
        persona_id = request.session.get("persona_id")
        tiempo = request.POST.get("tiempo_estimado", "").strip()
        cliente = fetch_one(
            "SELECT p.id FROM personas p INNER JOIN clientes c ON p.id = c.persona_ptr_id WHERE p.username = %s",
            [solicitud.username],
        )
        if not cliente:
            raise Http404
        vehiculo = fetch_one(
            "SELECT id FROM vehiculos WHERE cliente_id = %s AND matricula = %s",
            [cliente.id, solicitud.matricula],
        )
        if vehiculo is None:
            vehiculo_id = execute(
                "INSERT INTO vehiculos (cliente_id, matricula, marca, modelo, color) VALUES (%s, %s, %s, %s, %s)",
                [cliente.id, solicitud.matricula, solicitud.marca, solicitud.modelo, solicitud.color],
            )
        else:
            vehiculo_id = vehiculo.id
        if not tiempo:
            messages.error(request, "Indica un tiempo estimado")
            return redirect("taller:panel_empleado")
        execute(
            "INSERT INTO ordenes (vehiculo_id, cliente_id, empleado_id, tiempo_estimado) VALUES (%s, %s, %s, %s)",
            [vehiculo_id, cliente.id, persona_id, tiempo],
        )
        execute(
            "UPDATE solicitudes SET tiempo_estimado = %s, estado = 'aceptada' WHERE id = %s",
            [tiempo, solicitud_id],
        )
        messages.success(request, "Trabajo aceptado correctamente")
    return redirect("taller:panel_empleado")


def dashboard(request):
    if not es_rol(request, "admin"):
        return redirect("admin_login")
    ordenes = fetch_all(
        "SELECT o.id, o.tiempo_estimado, o.fecha_creacion, "
        "p_cliente.nombre AS c_nombre, p_cliente.apellido AS c_apellido, "
        "p_cliente.dni AS c_dni, p_cliente.contacto AS c_contacto, "
        "v.marca AS v_marca, v.modelo AS v_modelo, v.color AS v_color, v.matricula AS v_matricula, "
        "p_empleado.nombre AS e_nombre "
        "FROM ordenes o "
        "INNER JOIN personas p_cliente ON o.cliente_id = p_cliente.id "
        "INNER JOIN vehiculos v ON o.vehiculo_id = v.id "
        "LEFT JOIN empleados em ON o.empleado_id = em.persona_ptr_id "
        "LEFT JOIN personas p_empleado ON em.persona_ptr_id = p_empleado.id "
        "ORDER BY o.fecha_creacion DESC"
    )
    for o in ordenes:
        o.cliente = SimpleNamespace(nombre=o.c_nombre, apellido=o.c_apellido, dni=o.c_dni, contacto=o.c_contacto)
        o.vehiculo = SimpleNamespace(marca=o.v_marca, modelo=o.v_modelo, color=o.v_color, matricula=o.v_matricula)
        o.empleado = SimpleNamespace(nombre=o.e_nombre)
    empleados_count = fetch_one("SELECT COUNT(*) AS cnt FROM empleados")
    clientes_count = fetch_one("SELECT COUNT(*) AS cnt FROM personas WHERE rol = 'cliente'")
    return render(request, "taller/dashboard.html", {
        "section": "dashboard",
        "ordenes": ordenes,
        "empleados": list(range(empleados_count.cnt)) if empleados_count else [],
        "clientes": list(range(clientes_count.cnt)) if clientes_count else [],
    })


def admin_clientes(request):
    if not es_rol(request, "admin"):
        return redirect("admin_login")
    clientes_list = fetch_all(
        "SELECT p.id, p.nombre, p.apellido, p.dni, p.direccion, p.contacto "
        "FROM personas p INNER JOIN clientes c ON p.id = c.persona_ptr_id "
        "WHERE p.rol = 'cliente' ORDER BY p.nombre"
    )
    return render(request, "taller/clientes.html", {
        "section": "clientes",
        "clientes": clientes_list,
    })


def vehiculos(request):
    if not es_rol(request, "admin"):
        return redirect("admin_login")
    vehiculos_list = fetch_all(
        "SELECT v.id, v.matricula, v.marca, v.modelo, v.color, "
        "p.nombre AS c_nombre, p.apellido AS c_apellido "
        "FROM vehiculos v "
        "INNER JOIN personas p ON v.cliente_id = p.id "
        "ORDER BY v.marca, v.modelo"
    )
    for v in vehiculos_list:
        v.cliente = SimpleNamespace(nombre=v.c_nombre, apellido=v.c_apellido)
    return render(request, "taller/vehiculos.html", {
        "section": "vehiculos",
        "vehiculos": vehiculos_list,
    })


def ordenes(request):
    if not es_rol(request, "admin"):
        return redirect("admin_login")
    ordenes_list = fetch_all(
        "SELECT o.id, o.tiempo_estimado, o.fecha_creacion, "
        "p_cliente.nombre AS c_nombre, p_cliente.apellido AS c_apellido, p_cliente.contacto AS c_contacto, "
        "v.marca AS v_marca, v.modelo AS v_modelo, v.matricula AS v_matricula, "
        "p_empleado.nombre AS e_nombre "
        "FROM ordenes o "
        "INNER JOIN personas p_cliente ON o.cliente_id = p_cliente.id "
        "INNER JOIN vehiculos v ON o.vehiculo_id = v.id "
        "LEFT JOIN empleados em ON o.empleado_id = em.persona_ptr_id "
        "LEFT JOIN personas p_empleado ON em.persona_ptr_id = p_empleado.id "
        "ORDER BY o.fecha_creacion DESC"
    )
    for o in ordenes_list:
        o.cliente = SimpleNamespace(nombre=o.c_nombre, apellido=o.c_apellido, contacto=o.c_contacto)
        o.vehiculo = SimpleNamespace(marca=o.v_marca, modelo=o.v_modelo, matricula=o.v_matricula)
        o.empleado = SimpleNamespace(nombre=o.e_nombre)
    return render(request, "taller/ordenes.html", {
        "section": "ordenes",
        "ordenes": ordenes_list,
    })


def empleados(request):
    if not es_rol(request, "admin"):
        return redirect("admin_login")
    empleados_list = fetch_all(
        "SELECT p.id, p.username, p.nombre, p.apellido, e.especialidad, "
        "(SELECT COUNT(*) FROM ordenes WHERE empleado_id = p.id) AS orden_count "
        "FROM personas p "
        "INNER JOIN empleados e ON p.id = e.persona_ptr_id "
        "ORDER BY p.nombre"
    )
    for e in empleados_list:
        e.orden_set = SimpleNamespace(count=e.orden_count)
    return render(request, "taller/empleados.html", {
        "section": "empleados",
        "empleados": empleados_list,
    })


def solicitudes_empleo(request):
    if not es_rol(request, "admin"):
        return redirect("admin_login")
    solicitudes = fetch_all(
        "SELECT s.id, s.especialidad, s.estado, s.fecha_creacion, "
        "p.username AS p_username, p.nombre AS p_nombre, p.apellido AS p_apellido "
        "FROM solicitudes_empleo s "
        "INNER JOIN personas p ON s.username = p.username "
        "ORDER BY s.fecha_creacion DESC"
    )
    for s in solicitudes:
        s.username = SimpleNamespace(username=s.p_username, nombre=s.p_nombre, apellido=s.p_apellido)
    return render(request, "taller/solicitudes_empleo.html", {
        "section": "solicitudes",
        "solicitudes": solicitudes,
    })


def aprobar_solicitud(request, solicitud_id):
    if not es_rol(request, "admin"):
        return redirect("admin_login")
    solicitud = fetch_one(
        "SELECT s.id, s.estado, s.username, s.especialidad, p.id AS persona_id "
        "FROM solicitudes_empleo s INNER JOIN personas p ON s.username = p.username WHERE s.id = %s",
        [solicitud_id],
    )
    if not solicitud:
        raise Http404
    if solicitud.estado == "pendiente":
        exists = fetch_one(
            "SELECT 1 FROM empleados WHERE persona_ptr_id = %s", [solicitud.persona_id]
        )
        if not exists:
            execute(
                "INSERT INTO empleados (persona_ptr_id, especialidad) VALUES (%s, %s)",
                [solicitud.persona_id, solicitud.especialidad],
            )
        execute(
            "UPDATE personas SET estado = 'activo' WHERE id = %s", [solicitud.persona_id]
        )
        execute(
            "UPDATE solicitudes_empleo SET estado = 'aprobado' WHERE id = %s", [solicitud_id]
        )
        messages.success(request, f"Solicitud de {solicitud.username} aprobada")
    return redirect("taller:solicitudes")


def rechazar_solicitud(request, solicitud_id):
    if not es_rol(request, "admin"):
        return redirect("admin_login")
    solicitud = fetch_one(
        "SELECT s.id, s.estado, s.username, p.id AS persona_id "
        "FROM solicitudes_empleo s INNER JOIN personas p ON s.username = p.username WHERE s.id = %s",
        [solicitud_id],
    )
    if not solicitud:
        raise Http404
    if solicitud.estado == "pendiente":
        execute(
            "UPDATE personas SET estado = 'rechazado' WHERE id = %s", [solicitud.persona_id]
        )
        execute(
            "UPDATE solicitudes_empleo SET estado = 'rechazado' WHERE id = %s", [solicitud_id]
        )
        messages.success(request, f"Solicitud de {solicitud.username} rechazada")
    return redirect("taller:solicitudes")


def solicitudes_taller(request):
    if not es_rol(request, "admin"):
        return redirect("admin_login")
    solicitudes = fetch_all(
        "SELECT id, nombre, apellido, username, matricula, marca, modelo, color, "
        "estado, empleado_asignado, contacto, fecha_creacion, tiempo_estimado "
        "FROM solicitudes ORDER BY fecha_creacion DESC"
    )
    for s in solicitudes:
        s.username = SimpleNamespace(username=s.username)
    empleados = fetch_all(
        "SELECT p.id, p.username, p.nombre, p.apellido "
        "FROM personas p INNER JOIN empleados e ON p.id = e.persona_ptr_id ORDER BY p.nombre"
    )
    return render(request, "taller/solicitudes_taller.html", {
        "section": "solicitudes_taller",
        "solicitudes": solicitudes,
        "empleados": empleados,
    })


def asignar_solicitud(request, solicitud_id):
    if not es_rol(request, "admin"):
        return redirect("admin_login")
    solicitud = fetch_one("SELECT id, estado FROM solicitudes WHERE id = %s", [solicitud_id])
    if not solicitud:
        raise Http404
    form = AsignarSolicitudForm(request.POST or None)
    if solicitud.estado == "pendiente" and form.is_valid():
        empleado_id = form.cleaned_data["empleado_id"]
        empleado = fetch_one(
            "SELECT p.id, p.username FROM personas p INNER JOIN empleados e ON p.id = e.persona_ptr_id WHERE p.id = %s",
            [empleado_id],
        )
        if not empleado:
            raise Http404
        execute(
            "UPDATE solicitudes SET empleado_asignado = %s, estado = 'asignada' WHERE id = %s",
            [empleado.username, solicitud_id],
        )
        messages.success(request, f"Solicitud asignada a {empleado.username}")
    return redirect("taller:solicitudes_taller")
