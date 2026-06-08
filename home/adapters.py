from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.shortcuts import redirect


class SynclySocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_requests_session(self):
        session = super().get_requests_session()
        session.trust_env = False
        return session

    def on_authentication_error(
        self,
        request,
        provider,
        error=None,
        exception=None,
        extra_context=None,
    ):
        provider_name = getattr(provider, "name", None) or str(provider).title()
        details = error or "unknown_error"

        if exception:
            details = f"{details}: {exception}"

        messages.error(
            request,
            f"{provider_name} login failed. {details}",
        )
        raise ImmediateHttpResponse(redirect("login_user"))
