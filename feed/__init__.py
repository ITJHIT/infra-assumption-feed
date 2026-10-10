"""Pull market assumptions for infrastructure models from primary sources, with provenance."""


class SourceError(RuntimeError):
    """A source could not be read, or returned something other than what was expected.

    Raised instead of falling back to a cached or default value: a model input that
    silently went stale is worse than a run that stops.
    """
