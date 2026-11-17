from django.core.management.base import BaseCommand

from reservas.services import actualizar_estados_reservas


class Command(BaseCommand):
    help = (
    "Cancela reservas pendientes vencidas y finaliza "
    "reservas confirmadas cuyo horario ya terminó."
    )

    def handle(self, *args, **options):
        resultado = actualizar_estados_reservas()

        self.stdout.write(
            self.style.SUCCESS(
                "Proceso completado. "
                f"Reservas canceladas: {resultado['canceladas']}. "
                f"Reservas finalizadas: {resultado['finalizadas']}."
            )
        )
