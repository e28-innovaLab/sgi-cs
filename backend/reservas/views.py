from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status, viewsets
from rest_framework.decorators import api_view, action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from usuarios.models import Rol
from usuarios.permissions import (
    es_administrador,
    PermisoActividad,
    PermisoEstadoReserva,
    PermisoParticipante,
    PermisoReserva,
    PermisoReservaParticipante,
    PermisoSolicitudEquipo,
    PermisoUsuarioReserva,
    )

from .models import (
    Actividad,
    EstadoReserva,
    Participante,
    Reserva,
    ReservaParticipante,
    SolicitudEquipo,
    UsuarioPorReserva,
    )
from espacios.models import Equipamiento
from .serializers import (
    ActividadSerializer,
    ConsultaDisponibilidadSerializer,
    EstadoReservaSerializer,
    ParticipanteSerializer,
    ReservaParticipanteSerializer,
    ReservaSerializer,
    SolicitudEquipoSerializer,
    UsuarioPorReservaSerializer,
    )
from .services import (
    obtener_aulas_disponibles,
    asignar_aulas_reserva,
    solicitar_equipamiento_reserva,
    actualizar_solicitud_equipamiento,
    eliminar_solicitud_equipamiento,
    _puede_operar_reserva,
    asociar_usuario_reserva,
    cambiar_solicitante_reserva,
    eliminar_usuario_reserva,
    quitar_aula_reserva,
    actualizar_estados_reservas,
    confirmar_reserva,
    rechazar_reserva,
    cancelar_reserva,
    _validar_recursos_reserva,
    )


@api_view(["GET"])
def aulas_disponibles(request):
    consulta = ConsultaDisponibilidadSerializer(data=request.query_params)
    consulta.is_valid(raise_exception=True)
    datos = consulta.validated_data

    aulas = obtener_aulas_disponibles(
        datos["fecha"],
        datos["hora_inicio"],
        datos["hora_fin"],
    )

    if "capacidad_min" in datos:
        aulas = aulas.filter(capacidad__gte=datos["capacidad_min"])

    resultado = [
        {
            "id": aula.pk,
            "nombre": aula.nombre,
            "capacidad": aula.capacidad,
        }
        for aula in aulas
    ]

    return Response(resultado)


class ReservaViewSet(viewsets.ModelViewSet):
    serializer_class = ReservaSerializer
    permission_classes = [IsAuthenticated, PermisoReserva]

    def get_queryset(self):
        usuario = self.request.user

        reservas = Reserva.objects.select_related(
            "actividad",
            "estado_reserva",
        ).prefetch_related(
            "aulas"
        ).order_by("-fecha_reserva", "-horario_inicio")

        # Administración y Coordinación pueden consultar todas.
        if (
            es_administrador(usuario)
            or (
                hasattr(usuario, "rol")
                and usuario.rol.nombre == Rol.COORDINACION
            )
        ):
            return reservas

        # Los solicitantes solamente ven sus propias reservas.
        return reservas.filter(
            usuarios_asociados__usuario=usuario,
            usuarios_asociados__solicitante=True,
        ).distinct()

    def perform_create(self, serializer):
        # Actualizar los estados de las reservas vencidas.
        actualizar_estados_reservas()

        usuario = self.request.user

        try:
            with transaction.atomic():
                estado_pendiente = EstadoReserva.objects.get(
                    estado=EstadoReserva.Estados.PENDIENTE
                )

                reserva = serializer.save(
                    estado_reserva=estado_pendiente
                )

                UsuarioPorReserva.objects.create(
                    reserva=reserva,
                    usuario=usuario,
                    solicitante=True,
                )

        except DjangoValidationError as error:
            raise ValidationError(
                error.message_dict
                if hasattr(error, "message_dict")
                else error.messages
            )

    def perform_update(self, serializer):
        try:
            with transaction.atomic():
                # Bloqueamos solamente la reserva.
                reserva = Reserva.objects.select_for_update(
                    of=("self",)
                ).get(pk=serializer.instance.pk)

                # Consultamos el estado de la reserva.
                reserva = Reserva.objects.select_related(
                    "estado_reserva"
                ).get(pk=reserva.pk)

                # Solamente se pueden modificar reservas pendientes.
                if (
                    reserva.estado_reserva is None
                    or reserva.estado_reserva.estado
                    != EstadoReserva.Estados.PENDIENTE
                ):
                    raise ValidationError(
                        "Solamente se pueden modificar reservas pendientes."
                    )

                serializer.instance = reserva
                reserva = serializer.save()

                _validar_recursos_reserva(
                    reserva,
                    exigir_aulas=False,
                )

        except DjangoValidationError as error:
            raise ValidationError(
                error.message_dict
                if hasattr(error, "message_dict")
                else error.messages
            )

    @action(
        detail=True,
        methods=["post"],
        url_path="confirmar",
    )
    def confirmar(self, request, pk=None):
        reserva = self.get_object()

        try:
            reserva = confirmar_reserva(
                reserva_id=reserva.pk,
                usuario=request.user,
            )
        except DjangoValidationError as error:
            raise ValidationError(
                error.message_dict
                if hasattr(error, "message_dict")
                else error.messages
            )

        return Response({
            "mensaje": "Reserva confirmada correctamente.",
            "reserva_id": reserva.pk,
            "estado": reserva.estado_reserva.estado,
        }, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_path="rechazar",
    )
    def rechazar(self, request, pk=None):
        reserva = self.get_object()

        try:
            reserva = rechazar_reserva(
                reserva_id=reserva.pk,
                usuario=request.user,
            )
        except DjangoValidationError as error:
            raise ValidationError(
                error.message_dict
                if hasattr(error, "message_dict")
                else error.messages
            )

        return Response({
            "mensaje": "Reserva rechazada correctamente.",
            "reserva_id": reserva.pk,
            "estado": reserva.estado_reserva.estado,
        }, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_path="cancelar",
    )
    def cancelar(self, request, pk=None):
        reserva = self.get_object()

        try:
            reserva = cancelar_reserva(
                reserva_id=reserva.pk,
                usuario=request.user,
            )
        except DjangoValidationError as error:
            raise ValidationError(
                error.message_dict
                if hasattr(error, "message_dict")
                else error.messages
            )

        return Response({
            "mensaje": "Reserva cancelada correctamente.",
            "reserva_id": reserva.pk,
            "estado": reserva.estado_reserva.estado,
        }, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_path="asignar-aulas",
    )
    def asignar_aulas(self, request, pk=None):
        # ADMIN o solicitante de la reserva pueden asignar aulas.
        reserva = self.get_object()

        if not _puede_operar_reserva(reserva, request.user):
            raise PermissionDenied(
                "No tenés permisos para gestionar las aulas de esta reserva."
            )

        # Obtenemos los IDs de las aulas enviados en el cuerpo.
        aulas_ids = request.data.get("aulas_ids")

        if not isinstance(aulas_ids, list) or not aulas_ids:
            raise ValidationError({
                "aulas_ids": "Debe enviar una lista con al menos un aula."
            })

        if any(
            not isinstance(aula_id, int) or isinstance(aula_id, bool)
            or aula_id <= 0
            for aula_id in aulas_ids
        ):
            raise ValidationError({
                "aulas_ids": "Todos los IDs deben ser números enteros positivos."
            })

        try:
            aulas = asignar_aulas_reserva(
                reserva_id=pk,
                aulas_ids=aulas_ids,
            )
        except DjangoValidationError as error:
            raise ValidationError(
                error.message_dict
                if hasattr(error, "message_dict")
                else error.messages
            )

        return Response([
            {
                "id": aula.pk,
                "nombre": aula.nombre,
                "capacidad": aula.capacidad,
            }
            for aula in aulas
        ])

    @action(
        detail=True,
        methods=["delete"],
        url_path="quitar-aula",
    )
    def quitar_aula(self, request, pk=None):
        # ADMIN o solicitante de la reserva pueden quitar aulas.
        reserva = self.get_object()

        if not _puede_operar_reserva(reserva, request.user):
            raise PermissionDenied(
                "No tenés permisos para gestionar las aulas de esta reserva."
            )

        # Obtenemos el ID del aula enviado en el cuerpo.
        aula_id = request.data.get("aula_id")

        if (
            not isinstance(aula_id, int)
            or isinstance(aula_id, bool)
            or aula_id <= 0
        ):
            raise ValidationError({
                "aula_id": "Debe ser un número entero positivo."
            })

        try:
            aulas = quitar_aula_reserva(
                reserva_id=reserva.pk,
                aula_id=aula_id,
            )
        except DjangoValidationError as error:
            raise ValidationError(
                error.message_dict
                if hasattr(error, "message_dict")
                else error.messages
            )

        return Response([
            {
                "id": aula.pk,
                "nombre": aula.nombre,
                "capacidad": aula.capacidad,
            }
            for aula in aulas
        ])

    @action(
            detail=True,
            methods=["post"],
            url_path="solicitar-equipamiento",
        )
    def solicitar_equipamiento(self, request, pk=None):
        reserva = self.get_object()

        if not _puede_operar_reserva(reserva, request.user):
            raise PermissionDenied(
                "No tenés permisos para gestionar el equipamiento de esta reserva."
            )

        equipamiento_id = request.data.get("equipamiento_id")
        cantidad_solicitada = request.data.get("cantidad_solicitada")
        cantidad_critica = request.data.get("cantidad_critica")

        datos = {
            "equipamiento_id": equipamiento_id,
            "cantidad_solicitada": cantidad_solicitada,
            "cantidad_critica": cantidad_critica,
        }

        for campo, valor in datos.items():
            if (
                not isinstance(valor, int)
                or isinstance(valor, bool)
                or valor <= 0
            ):
                raise ValidationError({
                    campo: "Debe ser un número entero positivo."
                })

        try:
            solicitud = solicitar_equipamiento_reserva(
                reserva_id=reserva.pk,
                equipamiento_id=equipamiento_id,
                cantidad_solicitada=cantidad_solicitada,
                cantidad_critica=cantidad_critica,
            )
        except DjangoValidationError as error:
            raise ValidationError(
                error.message_dict
                if hasattr(error, "message_dict")
                else error.messages
            )

        return Response({
            "id_solicitud": solicitud.pk,
            "reserva_id": solicitud.reserva_id,
            "equipamiento_id": solicitud.equipamiento_id,
            "equipamiento_nombre": solicitud.equipamiento.nombre,
            "cantidad_solicitada": solicitud.cantidad_solicitada,
            "cantidad_reservada": solicitud.cantidad_reservada,
            "cantidad_critica": solicitud.cantidad_critica,
        })

    @action(
        detail=True,
        methods=["delete"],
        url_path="eliminar-solicitud-equipamiento",
    )
    def eliminar_solicitud_equipamiento(self, request, pk=None):
        reserva = self.get_object()

        if not _puede_operar_reserva(reserva, request.user):
            raise PermissionDenied(
                "No tenés permisos para gestionar el equipamiento de esta reserva."
            )

        equipamiento_id = request.data.get("equipamiento_id")

        if (
            not isinstance(equipamiento_id, int)
            or isinstance(equipamiento_id, bool)
            or equipamiento_id <= 0
        ):
            raise ValidationError({
                "equipamiento_id": "Debe ser un número entero positivo."
            })

        try:
            eliminar_solicitud_equipamiento(
                reserva_id=reserva.pk,
                equipamiento_id=equipamiento_id,
            )
        except DjangoValidationError as error:
            raise ValidationError(
                error.message_dict
                if hasattr(error, "message_dict")
                else error.messages
            )

        return Response(
            {"mensaje": "Solicitud de equipamiento eliminada correctamente."},
            status=status.HTTP_200_OK,
        )


class ActividadViewSet(viewsets.ModelViewSet):
    serializer_class = ActividadSerializer
    permission_classes = [IsAuthenticated, PermisoActividad]

    def get_queryset(self):
        usuario = self.request.user

        actividades = Actividad.objects.select_related(
            "responsable"
        )

        # Administración y Coordinación pueden consultar todas.
        if (
            es_administrador(usuario)
            or (
                hasattr(usuario, "rol")
                and usuario.rol.nombre == Rol.COORDINACION
            )
        ):
            return actividades

        # Los solicitantes pueden consultar todas las actividades.
        return actividades

    def perform_create(self, serializer):
        usuario = self.request.user

        try:
            with transaction.atomic():
                actividad = serializer.save(responsable=usuario)
                actividad.full_clean()
                actividad.save()

        except DjangoValidationError as error:
            raise ValidationError(
                error.message_dict
                if hasattr(error, "message_dict")
                else error.messages
            )

    def perform_update(self, serializer):
        try:
            with transaction.atomic():
                actividad = serializer.save()
                actividad.full_clean()
                actividad.save()

        except DjangoValidationError as error:
            raise ValidationError(
                error.message_dict
                if hasattr(error, "message_dict")
                else error.messages
            )


class ParticipanteViewSet(viewsets.ModelViewSet):
    queryset = Participante.objects.select_related(
        "creado_por"
    ).all()
    serializer_class = ParticipanteSerializer
    permission_classes = [IsAuthenticated, PermisoParticipante]

    def perform_create(self, serializer):
        usuario = self.request.user
        serializer.save(creado_por=usuario)


class ReservaParticipanteViewSet(viewsets.ModelViewSet):
    queryset = ReservaParticipante.objects.select_related(
        "reserva",
        "participante",
    ).all()

    serializer_class = ReservaParticipanteSerializer
    permission_classes = [
        IsAuthenticated,
        PermisoReservaParticipante,
    ]

    def get_queryset(self):
        usuario = self.request.user
        asociaciones = self.queryset

        if es_administrador(usuario) or (
            hasattr(usuario, "rol")
            and usuario.rol.nombre == Rol.COORDINACION
        ):
            return asociaciones

        return asociaciones.filter(
            reserva__usuarios_asociados__usuario=usuario,
            reserva__usuarios_asociados__solicitante=True,
        ).distinct()

    def perform_create(self, serializer):
        usuario = self.request.user
        reserva = serializer.validated_data["reserva"]

        if not es_administrador(usuario):
            es_solicitante = (
                hasattr(usuario, "rol")
                and usuario.rol.nombre == Rol.SOLICITANTE
            )

            if not es_solicitante:
                raise PermissionDenied(
                    "No tenés permiso para asociar participantes."
                )

            if not reserva.usuarios_asociados.filter(
                usuario=usuario,
                solicitante=True,
            ).exists():
                raise PermissionDenied(
                    "Solo podés asociar participantes a tus propias reservas."
                )

        serializer.save()


    def perform_update(self, serializer):
        usuario = self.request.user

        if not es_administrador(usuario):
            reserva = serializer.validated_data.get(
                "reserva",
                serializer.instance.reserva,
            )

            if not reserva.usuarios_asociados.filter(
                usuario=usuario,
                solicitante=True,
            ).exists():
                raise PermissionDenied(
                    "Solo podés asociar participantes a tus propias reservas."
                )

        serializer.save()


class SolicitudEquipoViewSet(viewsets.ModelViewSet):
    queryset = SolicitudEquipo.objects.select_related(
        "reserva",
        "equipamiento",
    ).all()

    serializer_class = SolicitudEquipoSerializer
    permission_classes = [
        IsAuthenticated,
        PermisoSolicitudEquipo,
    ]

    def get_queryset(self):
        usuario = self.request.user
        solicitudes = self.queryset

        # ADMIN y COORDINACION pueden consultar todas.
        if es_administrador(usuario) or (
            hasattr(usuario, "rol")
            and usuario.rol.nombre == Rol.COORDINACION
        ):
            return solicitudes

        # SOLICITANTE solamente consulta solicitudes
        # de sus propias reservas.
        return solicitudes.filter(
            reserva__usuarios_asociados__usuario=usuario,
            reserva__usuarios_asociados__solicitante=True,
        ).distinct()


    def perform_create(self, serializer):
        usuario = self.request.user
        datos = serializer.validated_data
        reserva = datos["reserva"]

        # ADMIN puede crear solicitudes en cualquier reserva.
        if not es_administrador(usuario):
            es_solicitante = (
                hasattr(usuario, "rol")
                and usuario.rol.nombre == Rol.SOLICITANTE
            )

            if not es_solicitante:
                raise PermissionDenied(
                    "No tenés permiso para crear solicitudes de equipamiento."
                )

            # Verificar que la reserva pertenezca al solicitante.
            if not reserva.usuarios_asociados.filter(
                usuario=usuario,
                solicitante=True,
            ).exists():
                raise PermissionDenied(
                    "Solo podés solicitar equipamiento para tus propias reservas."
                )

        # Utilizar el servicio para aplicar todas las reglas de negocio.
        try:
            solicitud = solicitar_equipamiento_reserva(
                reserva_id=reserva.pk,
                equipamiento_id=datos["equipamiento"].pk,
                cantidad_solicitada=datos["cantidad_solicitada"],
                cantidad_critica=datos["cantidad_critica"],
            )
        except DjangoValidationError as error:
            raise ValidationError(error.messages)

        # Asignar la instancia para que DRF pueda devolverla en la respuesta.
        serializer.instance = solicitud

    def perform_update(self, serializer):
        usuario = self.request.user
        solicitud_actual = serializer.instance
        datos = serializer.validated_data

        # La reserva no puede cambiar durante una actualización.
        reserva = solicitud_actual.reserva

        # Si no se envía algún campo, conservamos su valor actual.
        equipamiento = datos.get(
            "equipamiento",
            solicitud_actual.equipamiento,
        )

        cantidad_solicitada = datos.get(
            "cantidad_solicitada",
            solicitud_actual.cantidad_solicitada,
        )

        cantidad_critica = datos.get(
            "cantidad_critica",
            solicitud_actual.cantidad_critica,
        )

        # ADMIN puede modificar cualquier solicitud.
        if not es_administrador(usuario):
            es_solicitante = (
                hasattr(usuario, "rol")
                and usuario.rol.nombre == Rol.SOLICITANTE
            )

            if not es_solicitante:
                raise PermissionDenied(
                    "No tenés permiso para modificar solicitudes de equipamiento."
                )

            # Verificar que la reserva pertenezca al solicitante.
            if not reserva.usuarios_asociados.filter(
                usuario=usuario,
                solicitante=True,
            ).exists():
                raise PermissionDenied(
                    "Solo podés modificar solicitudes de tus propias reservas."
                )

        # Utilizar el servicio para aplicar todas las reglas de negocio.
        try:
            solicitud = actualizar_solicitud_equipamiento(
                solicitud_id=solicitud_actual.pk,
                equipamiento_id=equipamiento.pk,
                cantidad_solicitada=cantidad_solicitada,
                cantidad_critica=cantidad_critica,
            )
        except DjangoValidationError as error:
            raise ValidationError(error.messages)

        # Asignar la instancia actualizada para la respuesta de DRF.
        serializer.instance = solicitud


class EstadoReservaViewSet(viewsets.ModelViewSet):
    queryset = EstadoReserva.objects.all()
    serializer_class = EstadoReservaSerializer
    permission_classes = [IsAuthenticated, PermisoEstadoReserva]


class UsuarioPorReservaViewSet(viewsets.ModelViewSet):
    queryset = UsuarioPorReserva.objects.select_related("reserva", "usuario").all()
    serializer_class = UsuarioPorReservaSerializer
    permission_classes = [IsAuthenticated, PermisoUsuarioReserva]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reserva = serializer.validated_data["reserva"]
        usuario = serializer.validated_data["usuario"]

        # Solo ADMIN o el solicitante actual pueden asociar usuarios.
        if not _puede_operar_reserva(reserva, request.user):
            raise PermissionDenied(
            "No tenés permiso para asociar usuarios a esta reserva."
            )

        # La transferencia del solicitante se realiza mediante PATCH.
        if serializer.validated_data.get("solicitante", False):
            raise ValidationError({
                "solicitante": (
                    "Para transferir la responsabilidad, utilizá "
                    "la actualización de una asociación existente."
                )
            })

        try:
            asociacion = asociar_usuario_reserva(
                reserva.pk,
                usuario.pk,
                solicitante=False,
            )
        except DjangoValidationError as e:
            raise ValidationError(
                e.messages if hasattr(e, "messages") else str(e)
            )

        read_serializer = self.get_serializer(asociacion)
        return Response(
            read_serializer.data,
            status=status.HTTP_201_CREATED,
        )


    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        # No permitimos trasladar una asociación a otra reserva
        # ni cambiar el usuario asociado.
        if "reserva" in request.data or "usuario" in request.data:
            raise ValidationError(
                "No se puede modificar la reserva ni el usuario asociado."
            )

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)

        nuevo_solicitante = serializer.validated_data.get(
            "solicitante",
            instance.solicitante,
        )

        # No se puede quitar directamente al solicitante actual.
        if instance.solicitante and not nuevo_solicitante:
            raise ValidationError({
                "solicitante": (
                    "Para cambiar al solicitante, asigná primero "
                    "otro usuario asociado."
                )
            })

        try:
            if nuevo_solicitante and not instance.solicitante:
                asociacion = cambiar_solicitante_reserva(
                    instance.reserva_id,
                    instance.usuario_id,
                )
            else:
                asociacion = instance

        except DjangoValidationError as e:
            raise ValidationError(
                e.messages if hasattr(e, "messages") else str(e)
            )

        # Recuperamos el registro actualizado desde la base de datos.
        asociacion.refresh_from_db()

        return Response(self.get_serializer(asociacion).data)


    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            # Utilizamos la función de servicio transaccional para eliminar respetando las reglas de negocio
            eliminar_usuario_reserva(instance.reserva_id, instance.usuario_id)
        except DjangoValidationError as e:
            raise ValidationError(e.messages if hasattr(e, "messages") else str(e))

        return Response(status=status.HTTP_204_NO_CONTENT)
