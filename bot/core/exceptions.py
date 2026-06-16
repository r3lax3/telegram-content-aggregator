class AdvertiseFoundError(Exception):
    pass


class MediaUnavailableError(Exception):
    """Media could not be downloaded or exceeds the allowed size.

    Raised so the distributor skips the whole post and moves on to the next
    candidate instead of publishing it without its media.
    """
    pass
