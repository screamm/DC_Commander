"""App-level composition modules for ModernCommanderApp.

This package hosts purpose-driven controllers that ``ModernCommanderApp``
composes at construction time. Each controller owns a cohesive slice of
application behaviour (file actions, navigation, selection, view modes)
and is given a back-reference to the owning app so it can reach shared
state (panels, services, error boundary) without re-implementing it.

Controllers are intentionally thin wrappers around the existing logic —
their job is organisation, not abstraction. ``ModernCommanderApp``
delegates its ``action_*`` / ``_perform_*`` methods to them so the top
level class stays small.
"""
