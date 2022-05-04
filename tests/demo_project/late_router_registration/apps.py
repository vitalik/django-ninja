from django.apps import AppConfig


class LateRouterRegistrationAppConfig(AppConfig):
    default = True
    name = "late_router_registration"

    def ready(self) -> None:
        super().ready()
        from .api import router
        from .routers import api_late_registration

        api_late_registration.add_router("", router)
