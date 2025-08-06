from rest_framework.views import exception_handler
from django.db import IntegrityError
from rest_framework.response import Response
from rest_framework import status

from rest_framework.views import exception_handler
from django.db import IntegrityError
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    print(f"Exception caught: {exc} ({type(exc)})")
    response = exception_handler(exc, context)

    if isinstance(exc, IntegrityError):
        return Response(
            {"error": "Database integrity error", "details": str(exc)},
            status=status.HTTP_400_BAD_REQUEST
        )
    return response

