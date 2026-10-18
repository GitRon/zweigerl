"""
Every model of the domain. Django reads exactly this module, so a model not imported here gets no table -
see docs/patterns/app-layout.md. What the models mean, and how they map to GEDCOM, is
docs/patterns/familie.md.
"""

from apps.stammbaum.models.angabe import Angabe
from apps.stammbaum.models.einstellung import Einstellung
from apps.stammbaum.models.eltern_kind import ElternKind
from apps.stammbaum.models.geschwister import Geschwister
from apps.stammbaum.models.partnerschaft import Partnerschaft
from apps.stammbaum.models.person import Person
from apps.stammbaum.models.quelle import Quelle
from apps.stammbaum.models.zitat import Zitat

__all__ = ["Angabe", "Einstellung", "ElternKind", "Geschwister", "Partnerschaft", "Person", "Quelle", "Zitat"]
