# Import enhanced parsers for application runtime
try:
    # Enhanced parsers with confidence scoring and provenance tracking
    from .hager.parser import HagerParser
    from .select.parser import SelectHingesParser

    # Legacy parser for compatibility (if needed)

    __all__ = ["HagerParser", "SelectHingesParser", "BasePDFParser"]

except ImportError as e:
    # Fallback to legacy parsers if enhanced ones fail
    print(f"Warning: Enhanced parsers unavailable, falling back to legacy: {e}")
    try:
        from .hager_parser import HagerParser as LegacyHagerParser
        from .select_hinges_parser import SelectHingesParser as LegacySelectHingesParser

        # Alias legacy parsers
        HagerParser = LegacyHagerParser
        SelectHingesParser = LegacySelectHingesParser

        __all__ = ["BasePDFParser", "HagerParser", "SelectHingesParser"]
    except ImportError:
        print("Critical: No parsers available")
        __all__ = []
