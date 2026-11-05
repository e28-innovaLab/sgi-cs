from django.core.management.base import BaseCommand

from reservas.services import finalizar_reservas_vencidas


class Command(BaseCommand):
    help = (
    "Cancela reservas pendientes vencidas y finaliza "
    "reservas confirmadas cuyo horario ya terminó."
    )

    def handle(self, *args, **options):
        cantidad = finalizar_reservas_vencidas()

        self.stdout.write(
            self.style.SUCCESS(
                f"Proceso completado. "
                f"Reservas finalizadas: {cantidad}."
            )
        )
