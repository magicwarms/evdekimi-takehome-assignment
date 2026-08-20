"""Custom exceptions. Each one maps to an HTTP status in main.py."""


class AppError(Exception):
    """Base class for errors we raise on purpose."""

    status_code = 500
    message = "Something went wrong."

    def __init__(self, message=None):
        super().__init__(message or self.message)
        if message:
            self.message = message


class NotFoundError(AppError):
    status_code = 404
    message = "Not found."


class ValidationError(AppError):
    status_code = 400
    message = "Invalid input."


class LLMError(AppError):
    status_code = 503
    message = "The AI service is unavailable right now. Please try again."
