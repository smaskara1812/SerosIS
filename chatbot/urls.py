from django.urls import path
from . import views

urlpatterns = [
    # ── Pages ──────────────────────────────────────────────────────────────
    path("", views.chat_page, name="chat"),
    path("health/", views.health_page, name="health"),
    path("manuals/", views.manuals_page, name="manuals"),
    path("dashboard/", views.dashboard_page, name="dashboard"),
    path("listings/", views.listings_page, name="listings"),
    path("listings/incidents/", views.listings_incidents_page, name="listings_incidents"),
    path("listings/hazard-cards/", views.listings_hazard_cards_page, name="listings_hazard_cards"),
    path("listings/employees/", views.listings_employees_page, name="listings_employees"),

    # ── Dashboard API ───────────────────────────────────────────────────────
    path("api/dashboard/", views.dashboard_api, name="dashboard_api"),
    path("api/dashboard/meta/", views.dashboard_meta, name="dashboard_meta"),
    path("api/dashboard/hse/", views.dashboard_hse_api, name="dashboard_hse_api"),
    path("api/dashboard/workforce/", views.dashboard_workforce_api, name="dashboard_workforce_api"),

    # ── Listings API ────────────────────────────────────────────────────────
    path("api/listings/meta/", views.listings_meta_api, name="listings_meta_api"),
    path("api/listings/incidents/", views.listings_incidents_api, name="listings_incidents_api"),
    path("api/listings/hazard-cards/", views.listings_hazard_cards_api, name="listings_hazard_cards_api"),
    path("api/listings/employees/meta/", views.listings_employees_meta_api, name="listings_employees_meta_api"),
    path("api/listings/employees/", views.listings_employees_api, name="listings_employees_api"),

    # ── Health API ──────────────────────────────────────────────────────────
    path("api/health/", views.health_api, name="health_api"),

    # ── Conversation search ─────────────────────────────────────────────────
    path("api/conversations/search/", views.conversation_search, name="conversation_search"),

    # ── Conversation management ─────────────────────────────────────────────
    path("api/conversations/", views.conversation_list, name="conversation_list"),
    path("api/conversations/new/", views.conversation_create, name="conversation_create"),
    path("api/conversations/<uuid:conversation_id>/", views.conversation_detail, name="conversation_detail"),
    path("api/conversations/<uuid:conversation_id>/delete/", views.conversation_delete, name="conversation_delete"),
    path("api/conversations/<uuid:conversation_id>/rename/", views.conversation_rename, name="conversation_rename"),

    # ── Chat ────────────────────────────────────────────────────────────────
    path("api/conversations/<uuid:conversation_id>/chat/", views.chat_api, name="chat_api"),

    # ── Manual management ───────────────────────────────────────────────────
    path("api/manuals/", views.manual_list, name="manual_list"),
    path("api/manuals/upload/", views.manual_upload, name="manual_upload"),
    path("api/manuals/ingest/", views.manual_ingest_start, name="manual_ingest_start"),
    path("api/manuals/ingest/status/", views.manual_ingest_status, name="manual_ingest_status"),
    path("api/manuals/<str:filename>/delete/", views.manual_delete, name="manual_delete"),
]
