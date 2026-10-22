BACKENDS = ("mpv", "miniaudio")


def create_backend(name="auto"):
    """Creates an audio backend by name.

    "auto" uses mpv if libmpv is installed (it plays more formats), and
    otherwise miniaudio, which needs nothing but pip packages."""
    if name in ("auto", "mpv"):
        try:
            from .mpv_backend import MpvBackend
            return MpvBackend()
        except (ImportError, OSError):
            # python-mpv manglar, eller libmpv er ikkje installert
            if name == "mpv":
                raise
    from .miniaudio_backend import MiniaudioBackend
    return MiniaudioBackend()
