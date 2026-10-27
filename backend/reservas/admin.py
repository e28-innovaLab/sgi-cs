from django.contrib import admin
from .models import (
    Actividad,
    Reserva,
    EstadoReserva,
    ReservaAula,
    SolicitudEquipo,
    UsuarioPorReserva,
    Participante,
    ReservaParticipante
)



@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = (
        "id_actividad",
        "nombre",
        "tipo",
        "responsable",
        "fecha_estimada",
        "horario_inicio_estimado",
        "horario_fin_estimado",
        "participantes_estimados",
    )
    list_filter = ("tipo", "fecha_estimada")
    search_fields = ("nombre", "responsable__username")
    ordering = ("fecha_estimada", "horario_inicio_estimado")


@admin.register(EstadoReserva)
class EstadoReservaAdmin(admin.ModelAdmin):
    list_display = ("id_estado_reserva", "estado")
    search_fields = ("estado",)


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = (
        "id_reserva",
        "actividad",
        "fecha_reserva",
        "horario_inicio",
        "horario_fin",
        "estado_reserva",
    )
    list_filter = ("estado_reserva", "fecha_reserva")
    search_fields = ("actividad__nombre", "cod_reunion")
    ordering = ("-fecha_reserva",)


@admin.register(ReservaAula)
class ReservaAulaAdmin(admin.ModelAdmin):
    list_display = ("id_reserva_por_aula", "reserva", "aula", "estado_reserva")
    list_filter = ("estado_reserva",)


@admin.register(SolicitudEquipo)
class SolicitudEquipoAdmin(admin.ModelAdmin):
    list_display = (
        "id_solicitud_por_equipo",
        "reserva",
        "equipamiento",
        "cantidad_solicitada",
        "cantidad_reservada",
        "cantidad_critica",
        "estado_reserva",
    )
    list_filter = ("estado_reserva",)
    search_fields = ("reserva__actividad__nombre", "equipamiento__nombre")


@admin.register(UsuarioPorReserva)
class UsuarioPorReservaAdmin(admin.ModelAdmin):
    list_display = ("id_usuario_por_reserva", "reserva", "usuario", "solicitante")
    list_filter = ("solicitante",)
    search_fields = ("usuario__username", "reserva__actividad__nombre")



@admin.register(Participante)
class ParticipanteAdmin(admin.ModelAdmin):
    list_display = (
        "id_participante",
        "apellidos",
        "nombres",
        "tipo_documento",
        "numero_documento",
        "nacionalidad",
        "lugar_residencia",
        "institucion",
    )

    list_filter = (
        "tipo_documento",
        "genero",
        "nacionalidad",
        "lugar_residencia",
        "institucion",
    )

    search_fields = (
        "nombres",
        "apellidos",
        "numero_documento",
        "mail",
        "institucion",
    )

    ordering = ("apellidos", "nombres")


@admin.register(ReservaParticipante)
class ReservaParticipanteAdmin(admin.ModelAdmin):
    list_display = (
        "id_reserva_participante",
        "reserva",
        "participante",
        "rol",
        "presente",
    )
    list_filter = ("rol", "presente")
    search_fields = (
        "participante__nombres",
        "participante__apellidos",
        "reserva__actividad__nombre",
    )