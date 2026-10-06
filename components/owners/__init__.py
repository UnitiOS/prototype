"""Who may seal under a name. See owners.py."""

from components.owners.owners import (
    OwnerError, add, at_seal, claim, first, known, names, owned, owners, remove,
    scope_of, state,
)

__all__ = ["OwnerError", "add", "at_seal", "claim", "first", "known", "names", "owned",
           "owners", "remove", "scope_of", "state"]
