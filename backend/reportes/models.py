from django.db import models


class HistorialReserva(models.Model):
    # Sin FK: una eliminación operativa no debe borrar ni alterar el historial.
    reserva_original_id = models.PositiveIntegerField(db_index=True)
    fecha_reserva = models.DateField(db_index=True)
    registrado_en = models.DateTimeField(auto_now_add=True)
    evento = models.CharField(max_length=30)
    huella = models.CharField(max_length=64)
    datos = models.JSONField()

    class Meta:
        ordering = ['-registrado_en', '-pk']
        indexes = [models.Index(fields=['reserva_original_id', '-id'], name='historial_reserva_ultimo')]
