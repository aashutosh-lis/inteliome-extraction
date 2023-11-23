from rest_framework.response import Response


def project_return(message=None, data=None, error=None, status=None):
    return Response(
        {"message": message, "data": data, "status": status, "error": error},
        status=status,
    )


def credentials_to_dict(credentials):
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
        "expiry": credentials.expiry,
    }
