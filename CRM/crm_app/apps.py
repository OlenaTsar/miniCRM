from django.apps import AppConfig


class CrmAppConfig(AppConfig):
    name = 'crm_app'

    def ready(self):
        # підключає signals при старті
        import crm_app.signals
