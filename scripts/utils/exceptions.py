"""Custom exceptions for Alpha Finder."""


class AlphaFinderError(Exception):
    """Base exception for Alpha Finder."""
    pass


class ConfigurationError(AlphaFinderError):
    """Configuration or data setup error."""
    pass


class CrawlerError(AlphaFinderError):
    """Error during web crawling or filing fetch."""
    pass


class DocumentProcessingError(AlphaFinderError):
    """Error processing a document."""
    pass


class AnalysisError(AlphaFinderError):
    """Error during analysis."""
    pass


class FilteringError(AlphaFinderError):
    """Error during filtering."""
    pass
