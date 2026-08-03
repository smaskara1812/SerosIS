from django.urls import path
from . import views

urlpatterns = [
    # ── Pages ──────────────────────────────────────────────────────────────
    path("", views.chat_page, name="chat"),
    path("health/", views.health_page, name="health"),
    path("manuals/", views.manuals_page, name="manuals"),
    path("dashboard/", views.dashboard_page, name="dashboard"),

    path("rigs/", views.rigs_page, name="rigs"),
    path("rigs/<int:rig_id>/", views.rig_detail_page, name="rig_detail"),

    path("listings/", views.listings_page, name="listings"),
    path("api/report-preview/", views.reportbro_preview, name="reportbro_preview"),
    path("api/pdf-templates/<str:report_name>/", views.pdf_template_get, name="pdf_template_get"),
    path("api/pdf-templates/<str:report_name>/save/", views.pdf_template_save, name="pdf_template_save"),
    path("listings/incidents/", views.listings_incidents_page, name="listings_incidents"),
    path("listings/hazard-cards/", views.listings_hazard_cards_page, name="listings_hazard_cards"),
    path("listings/employees/", views.listings_employees_page, name="listings_employees"),
    path("listings/staff/", views.listings_staff_page, name="listings_staff"),
    path("listings/crew-rotations/", views.listings_crew_rotations_page, name="listings_crew_rotations"),
    path("listings/invoices/", views.listings_invoices_page, name="listings_invoices"),
    path("listings/certificates/", views.listings_certificates_page, name="listings_certificates"),

    # ── Rigs 360 API ───────────────────────────────────────────────────────
    path("api/rigs/", views.rigs_list_api, name="rigs_list_api"),
    path("api/rigs/<int:rig_id>/overview/", views.rig_overview_api, name="rig_overview_api"),
    path("api/rigs/<int:rig_id>/snapshot/", views.rig_snapshot_api, name="rig_snapshot_api"),
    path("api/rigs/<int:rig_id>/crew-groups/", views.rig_crew_groups_api, name="rig_crew_groups_api"),
    path("api/rigs/<int:rig_id>/people/", views.rig_people_api, name="rig_people_api"),
    path("api/rigs/<int:rig_id>/safety/", views.rig_safety_api, name="rig_safety_api"),
    path("api/rigs/<int:rig_id>/finance/", views.rig_finance_api, name="rig_finance_api"),
    path("api/rigs/<int:rig_id>/operations/", views.rig_operations_api, name="rig_operations_api"),

    # ── Dashboard API ───────────────────────────────────────────────────────
    path("api/dashboard/", views.dashboard_api, name="dashboard_api"),
    path("api/dashboard/meta/", views.dashboard_meta, name="dashboard_meta"),
    path("api/dashboard/hse/", views.dashboard_hse_api, name="dashboard_hse_api"),
    path("api/dashboard/hse/hotspot/", views.dashboard_hse_hotspot_api, name="dashboard_hse_hotspot_api"),
    path("api/dashboard/hse/correlation/", views.dashboard_hse_correlation_api, name="dashboard_hse_correlation_api"),
    path("api/dashboard/workforce/", views.dashboard_workforce_api, name="dashboard_workforce_api"),
    path("api/dashboard/finance/", views.dashboard_finance_api, name="dashboard_finance_api"),
    path("api/dashboard/finance/meta/", views.dashboard_finance_meta, name="dashboard_finance_meta"),

    # ── Listings API ────────────────────────────────────────────────────────
    path("api/listings/meta/", views.listings_meta_api, name="listings_meta_api"),
    path("api/listings/incidents/", views.listings_incidents_api, name="listings_incidents_api"),
    path("api/listings/hazard-cards/", views.listings_hazard_cards_api, name="listings_hazard_cards_api"),
    path("api/listings/hazard-cards/pdf/", views.listings_hazard_cards_pdf, name="listings_hazard_cards_pdf"),
    path("api/listings/employees/meta/", views.listings_employees_meta_api, name="listings_employees_meta_api"),
    path("api/listings/employees/", views.listings_employees_api, name="listings_employees_api"),
    path("api/listings/staff/meta/", views.listings_staff_meta_api, name="listings_staff_meta_api"),
    path("api/listings/staff/", views.listings_staff_api, name="listings_staff_api"),
    path("api/listings/crew-rotations/meta/", views.listings_crew_rotations_meta_api, name="listings_crew_rotations_meta_api"),
    path("api/listings/crew-rotations/", views.listings_crew_rotations_api, name="listings_crew_rotations_api"),
    path("api/listings/invoices/meta/", views.listings_invoices_meta_api, name="listings_invoices_meta_api"),
    path("api/listings/invoices/", views.listings_invoices_api, name="listings_invoices_api"),
    path("api/listings/certificates/meta/", views.listings_certificates_meta_api, name="listings_certificates_meta_api"),
    path("api/listings/certificates/", views.listings_certificates_api, name="listings_certificates_api"),

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
