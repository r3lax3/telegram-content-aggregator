class ScrappingError(Exception):
    """Base exception for scrapping errors."""
    pass


class ChannelNotFound(ScrappingError):
    """Raised when channel is not found (404)."""
    pass


class RobotSuspicion(ScrappingError):
    """Raised when detected as a robot (429)."""
    pass


class ParsingError(ScrappingError):
    """Raised when HTML parsing fails."""
    pass


class PostsListNotFoundException(ParsingError):
    """Raised when posts list container is not found."""
    pass


class PostIdNotFoundException(ParsingError):
    """Raised when post ID cannot be extracted."""
    pass


class PostTextNotFoundException(ParsingError):
    """Raised when post text cannot be extracted."""
    pass


class VideoUnavailableException(ScrappingError):
    """Raised when video is unavailable for preview."""
    pass


class MediaUnavailableException(ScrappingError):
    """Raised when media (e.g., carousel) is unavailable."""
    pass
