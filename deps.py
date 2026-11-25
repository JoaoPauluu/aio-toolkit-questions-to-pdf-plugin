"""Python packages the plugin needs, installed once into $AIO_DATA/venvs/assignment-pdf."""
import aio

PACKAGES = ("pydantic>=2.7,<3",)


def ensure():
    try:
        import pydantic  # noqa: F401  (already available, e.g. in local development)
    except ImportError:
        aio.ensure_packages("assignment-pdf", *PACKAGES)
