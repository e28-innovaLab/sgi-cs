from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete
from django.dispatch import receiver

from reservas.models import Actividad, Reserva, ReservaAula, ReservaParticipante, SolicitudEquipo
from .history import registrar_reserva


@receiver(post_save, sender=Reserva)
def guardar_reserva(sender, instance, created, raw=False, using='default', **kwargs):
    if not raw:
        registrar_reserva(instance.pk, 'CREADA' if created else 'CAMBIO', using)


@receiver(pre_delete, sender=Reserva)
def eliminar_reserva(sender, instance, using='default', **kwargs):
    registrar_reserva(instance.pk, 'ELIMINADA', using)


@receiver(post_save, sender=ReservaAula)
@receiver(post_save, sender=SolicitudEquipo)
@receiver(post_save, sender=ReservaParticipante)
@receiver(post_delete, sender=ReservaAula)
@receiver(post_delete, sender=SolicitudEquipo)
@receiver(post_delete, sender=ReservaParticipante)
def cambiar_relacion(sender, instance, raw=False, origin=None, using='default', **kwargs):
    # Evita snapshots parciales durante el borrado en cascada de una reserva.
    if raw or isinstance(origin, Reserva) or getattr(origin, 'model', None) is Reserva:
        return
    registrar_reserva(instance.reserva_id, 'RELACIONES', using)


@receiver(post_save, sender=Actividad)
def cambiar_actividad(sender, instance, raw=False, using='default', **kwargs):
    if not raw:
        for pk in instance.reservas.using(using).values_list('pk', flat=True):
            registrar_reserva(pk, 'ACTIVIDAD', using)


@receiver(m2m_changed, sender=Reserva.aulas.through)
@receiver(m2m_changed, sender=Reserva.participantes.through)
def cambiar_aulas(sender, instance, action, reverse, pk_set, using='default', **kwargs):
    if not reverse and action in ('post_add', 'post_remove', 'post_clear'):
        registrar_reserva(instance.pk, 'RELACIONES', using)
    elif reverse:
        if action == 'pre_clear':
            instance._reservas_historial = list(instance.reservas.values_list('pk', flat=True))
        elif action in ('post_add', 'post_remove', 'post_clear'):
            for pk in (pk_set or getattr(instance, '_reservas_historial', [])):
                registrar_reserva(pk, 'RELACIONES', using)
