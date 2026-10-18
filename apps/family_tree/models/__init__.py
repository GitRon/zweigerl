"""
Every model of the domain. Django reads exactly this module, so a model not imported here gets no table -
see docs/patterns/app-layout.md. What the models mean, and how they map to GEDCOM, is
docs/patterns/family.md.
"""

from apps.family_tree.models.parent_child import ParentChild
from apps.family_tree.models.partnership import Partnership
from apps.family_tree.models.person import Person
from apps.family_tree.models.sibling_pair import SiblingPair
from apps.family_tree.models.tree_settings import TreeSettings

__all__ = ["ParentChild", "Partnership", "Person", "SiblingPair", "TreeSettings"]
