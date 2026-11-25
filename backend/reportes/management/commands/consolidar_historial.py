from django.core.management.base import BaseCommand

from reportes.history import registrar_reserva
from reservas.models import Reserva


class Command(BaseCommand):
    help = 'Consolida el estado disponible de las reservas; no reconstruye cambios previos.'

    def handle(self, *args, **options):
        nuevos = 0
        for pk in Reserva.objects.order_by('pk').values_list('pk', flat=True).iterator():
            nuevos += registrar_reserva(pk, 'CONSOLIDACION')
        self.stdout.write(self.style.SUCCESS(f'Snapshots nuevos: {nuevos}.'))
