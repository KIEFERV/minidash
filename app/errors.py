"""Domain errors. main.py maps them to HTTP responses."""


class MiniDashError(Exception):
    status_code = 500

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(MiniDashError):
    status_code = 404


class ConflictError(MiniDashError):
    status_code = 409


class UnprocessableError(MiniDashError):
    status_code = 422
