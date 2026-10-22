from rest_framework.exceptions import APIException


class ConflictoDeRelacion(APIException):
    status_code = 409
    default_detail = 'El registro tiene relaciones que impiden eliminarlo.'
    default_code = 'conflicto_de_relacion'
