"""
Consistent API error envelope:

{
  "error": {
    "code": "validation_error" | "not_found" | "permission_denied" | ...,
    "message": "human readable summary",
    "details": {...}   # original DRF error data, field-level where applicable
  }
}
"""
from rest_framework.views import exception_handler as drf_exception_handler


_CODE_BY_STATUS = {
    400: "validation_error",
    401: "authentication_required",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    429: "rate_limited",
    500: "server_error",
}


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    if isinstance(detail, dict) and "detail" in detail and len(detail) == 1:
        message = str(detail["detail"])
    elif isinstance(detail, list):
        message = "; ".join(str(d) for d in detail)
    else:
        message = "Request failed validation."

    response.data = {
        "error": {
            "code": _CODE_BY_STATUS.get(response.status_code, "error"),
            "message": message,
            "details": detail,
        }
    }
    return response
