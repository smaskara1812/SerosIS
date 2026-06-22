from django.conf import settings
from django.urls import path, include

urlpatterns = [
    path("", include("chatbot.urls")),
]

if settings.DEBUG and not settings.TESTING:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()
