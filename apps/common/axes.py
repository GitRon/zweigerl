def no_client_ip(request) -> None:
    """
    The client IP django-axes stores with every login attempt - none. Lockouts go by username, so the
    address would only be personal data kept for nothing.
    """
    return
