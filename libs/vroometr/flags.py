"""Named kill-switch flags. App code uses OpenFeature, not Unleash directly."""

from openfeature import api
from openfeature.evaluation_context import EvaluationContext
from openfeature.flag_evaluation import FlagResolutionDetails, Reason
from openfeature.provider import AbstractProvider
from openfeature.provider.metadata import Metadata

FLAG_WEB_RESEARCH = "web_research"
FLAG_VISION = "vision"
FLAG_VOICE = "voice"
FLAG_AI_WRITES = "ai_writes"

KILL_SWITCHES = (
    FLAG_WEB_RESEARCH,
    FLAG_VISION,
    FLAG_VOICE,
    FLAG_AI_WRITES,
)

_configured = False


class StaticBooleanProvider(AbstractProvider):
    """In-memory booleans for tests and local boot before Unleash is used."""

    def __init__(self, values: dict[str, bool]) -> None:
        self._values = values

    def get_metadata(self) -> Metadata:
        return Metadata(name="vroometr-static-boolean")

    def resolve_boolean_details(
        self,
        flag_key: str,
        default_value: bool,
        evaluation_context: EvaluationContext | None = None,
    ) -> FlagResolutionDetails:
        del evaluation_context
        return FlagResolutionDetails(
            value=self._values.get(flag_key, default_value),
            reason=Reason.STATIC,
        )

    def resolve_string_details(
        self,
        flag_key: str,
        default_value: str,
        evaluation_context: EvaluationContext | None = None,
    ) -> FlagResolutionDetails:
        del flag_key, evaluation_context
        return FlagResolutionDetails(value=default_value, reason=Reason.DEFAULT)

    def resolve_integer_details(
        self,
        flag_key: str,
        default_value: int,
        evaluation_context: EvaluationContext | None = None,
    ) -> FlagResolutionDetails:
        del flag_key, evaluation_context
        return FlagResolutionDetails(value=default_value, reason=Reason.DEFAULT)

    def resolve_float_details(
        self,
        flag_key: str,
        default_value: float,
        evaluation_context: EvaluationContext | None = None,
    ) -> FlagResolutionDetails:
        del flag_key, evaluation_context
        return FlagResolutionDetails(value=default_value, reason=Reason.DEFAULT)

    def resolve_object_details(
        self,
        flag_key: str,
        default_value: dict | list | None,
        evaluation_context: EvaluationContext | None = None,
    ) -> FlagResolutionDetails:
        del flag_key, evaluation_context
        return FlagResolutionDetails(value=default_value, reason=Reason.DEFAULT)


def use_in_memory_flags(overrides: dict[str, bool] | None = None) -> None:
    global _configured
    values = dict.fromkeys(KILL_SWITCHES, True)
    if overrides:
        values.update(overrides)
    api.set_provider(StaticBooleanProvider(values))
    _configured = True


def _use_unleash() -> None:
    global _configured
    from unleash_openfeature_python_provider import UnleashFlagProvider

    from vroometr.settings import settings

    provider = UnleashFlagProvider(
        url=settings.unleash_url,
        app_name=settings.unleash_app_name,
        custom_headers={"Authorization": settings.unleash_api_token},
    )
    api.set_provider_and_wait(provider)
    _configured = True


def configure_flags() -> None:
    if _configured:
        return
    from vroometr.settings import settings

    if settings.flags_provider == "unleash":
        _use_unleash()
        return
    use_in_memory_flags()


def is_enabled(flag_key: str, *, default: bool = True) -> bool:
    configure_flags()
    return api.get_client().get_boolean_value(flag_key, default)
