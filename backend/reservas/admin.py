from django.contrib import admin
from .models import Reserva, ReservaAula, SolicitudEquipo, Participante

admin.site.register(Reserva)
admin.site.register(ReservaAula)
admin.site.register(SolicitudEquipo)
admin.site.register(Participante)