from whitenoise.storage import CompressedManifestStaticFilesStorage


class SafeCompressedManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """
    Subclass of WhiteNoise's CompressedManifestStaticFilesStorage that disables
    strict manifest enforcement. If a file is missing from the manifest (e.g. during local
    development or test runs where collectstatic has not been run), it falls back gracefully
    to serving the unhashed file instead of raising a ValueError.
    """
    manifest_strict = False
