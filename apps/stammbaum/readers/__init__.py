"""
Everything that reads: the queries a screen needs, so a view never builds one itself.

A view calls a reader; a reader never writes and never calls an action or a view. See
AGENTS.md, "Where code goes".
"""
