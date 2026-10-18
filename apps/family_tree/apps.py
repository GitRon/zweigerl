from django.apps import AppConfig


class FamilyTreeConfig(AppConfig):
    name = "apps.family_tree"
    verbose_name = "Stammbaum"
    # Set here rather than as DEFAULT_AUTO_FIELD in the settings: the domain is the one app with models of
    # its own, and a family tree imported from PAF can outgrow nothing smaller anyway.
    default_auto_field = "django.db.models.BigAutoField"
