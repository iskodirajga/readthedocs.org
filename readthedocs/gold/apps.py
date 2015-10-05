import logging

from django.apps import AppConfig

log = logging.getLogger(__name__)


class GoldAppConfig(AppConfig):
    name = 'readthedocs.gold'
    verbose_name = 'Read the Docs Gold'

    def ready(self):
        if hasattr(self, 'already_run'):
            return
        self.already_run = True
        import readthedocs.gold.signals
