class GeordnetesPaarMixin:
    """
    For a model that links two people symmetrically through "person_a" and "person_b" and stores each pair
    once, the lower primary key first - which its CheckConstraint holds.
    """

    def save(self, *args, **kwargs) -> None:
        self.ordne_paar()
        super().save(*args, **kwargs)

    def ordne_paar(self) -> None:
        """
        Puts the lower primary key first. Called by "clean" as well as "save": the admin validates the
        constraints before it saves, so a pair entered the other way round has to be turned before that.
        """
        if self.person_a_id is not None and self.person_b_id is not None and self.person_a_id > self.person_b_id:
            self.person_a, self.person_b = self.person_b, self.person_a
