from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # ── Auth ───────────────────────────────────────────────────────────────
    path("login/", auth_views.LoginView.as_view(template_name="chatbot/login.html"), name="login"),
    path("logout/", views.logout_view, name="logout"),

    # ── Pages ──────────────────────────────────────────────────────────────
    path("", views.dashboard_page, name="home"),
    path("chat/", views.chat_page, name="chat"),
    path("health/", views.health_page, name="health"),
    path("manuals/", views.manuals_page, name="manuals"),
    path("dashboard/", views.dashboard_page, name="dashboard"),

    path("masters/", views.masters_page, name="masters"),
    path("masters/rigs/", views.rig_master_page, name="rig_master"),
    path("masters/cost-centre-type/", views.cost_centre_type_page, name="cost_centre_type"),
    path("masters/cost-centre/", views.cost_centre_page, name="cost_centre"),
    path("masters/operator/", views.operator_master_page, name="operator_master"),
    path("masters/contractor/", views.contractor_master_page, name="contractor_master"),
    path("masters/email-notification-types/", views.email_notification_type_page, name="email_notification_type"),
    path("masters/cert-institutes/", views.cert_institute_page, name="cert_institute"),

    # ── Contractor Master API ──────────────────────────────────────────────────
    path("api/masters/contractor/", views.contractor_list_api, name="contractor_list"),
    path("api/masters/contractor/save/", views.contractor_save_api, name="contractor_save"),
    path("api/masters/contractor/<int:contractor_id>/", views.contractor_get_api, name="contractor_get"),
    path("api/masters/contractor/<int:contractor_id>/check-delete/", views.contractor_check_delete_api, name="contractor_check_delete"),
    path("api/masters/contractor/<int:contractor_id>/delete/", views.contractor_delete_api, name="contractor_delete"),

    # ── Operator Master API ────────────────────────────────────────────────────
    path("api/masters/operator/", views.operator_list_api, name="operator_list"),
    path("api/masters/operator/save/", views.operator_save_api, name="operator_save"),
    path("api/masters/operator/countries/", views.operator_countries_search_api, name="operator_countries"),
    path("api/masters/operator/<int:op_id>/", views.operator_get_api, name="operator_get"),
    path("api/masters/operator/<int:op_id>/deactivate/", views.operator_deactivate_api, name="operator_deactivate"),
    path("api/masters/operator/<int:op_id>/check-delete/", views.operator_check_delete_api, name="operator_check_delete"),
    path("api/masters/operator/<int:op_id>/delete/", views.operator_delete_api, name="operator_delete"),

    # ── Cost Centre API ────────────────────────────────────────────────────────
    path("api/masters/cost-centre/meta/", views.cost_centre_meta_api, name="cost_centre_meta"),
    path("api/masters/cost-centre/locations/", views.cost_centre_locations_search_api, name="cost_centre_locations"),
    path("api/masters/cost-centre/", views.cost_centre_list_api, name="cost_centre_list"),
    path("api/masters/cost-centre/save/", views.cost_centre_save_api, name="cost_centre_save"),
    path("api/masters/cost-centre/<int:cc_id>/", views.cost_centre_get_api, name="cost_centre_get"),
    path("api/masters/cost-centre/<int:cc_id>/deactivate/", views.cost_centre_deactivate_api, name="cost_centre_deactivate"),
    path("api/masters/cost-centre/<int:cc_id>/check-delete/", views.cost_centre_check_delete_api, name="cost_centre_check_delete"),
    path("api/masters/cost-centre/<int:cc_id>/delete/", views.cost_centre_delete_api, name="cost_centre_delete"),

    # ── Cost Centre Type API ───────────────────────────────────────────────────
    path("api/masters/cost-centre-type/", views.cost_centre_type_list_api, name="cost_centre_type_list"),
    path("api/masters/cost-centre-type/save/", views.cost_centre_type_save_api, name="cost_centre_type_save"),
    path("api/masters/cost-centre-type/<int:type_id>/", views.cost_centre_type_get_api, name="cost_centre_type_get"),
    path("api/masters/cost-centre-type/<int:type_id>/deactivate/", views.cost_centre_type_deactivate_api, name="cost_centre_type_deactivate"),
    path("api/masters/cost-centre-type/<int:type_id>/check-delete/", views.cost_centre_type_check_delete_api, name="cost_centre_type_check_delete"),
    path("api/masters/cost-centre-type/<int:type_id>/delete/", views.cost_centre_type_delete_api, name="cost_centre_type_delete"),

    path("api/masters/cert-institute/", views.cert_institute_list_api, name="cert_institute_list"),
    path("api/masters/cert-institute/save/", views.cert_institute_save_api, name="cert_institute_save"),
    path("api/masters/cert-institute/<int:inst_id>/", views.cert_institute_get_api, name="cert_institute_get"),
    path("api/masters/cert-institute/<int:inst_id>/check-delete/", views.cert_institute_check_delete_api, name="cert_institute_check_delete"),
    path("api/masters/cert-institute/<int:inst_id>/delete/", views.cert_institute_delete_api, name="cert_institute_delete"),

    path("api/masters/email-notification-type/", views.email_notification_type_list_api, name="email_notification_type_list"),
    path("api/masters/email-notification-type/save/", views.email_notification_type_save_api, name="email_notification_type_save"),
    path("api/masters/email-notification-type/<int:type_id>/", views.email_notification_type_get_api, name="email_notification_type_get"),
    path("api/masters/email-notification-type/<int:type_id>/deactivate/", views.email_notification_type_deactivate_api, name="email_notification_type_deactivate"),

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
    path("listings/users/", views.listings_users_page, name="listings_users"),

    # ── Rig Master API ─────────────────────────────────────────────────────────
    path("api/rigs/master/meta/", views.rig_master_meta_api, name="rig_master_meta"),
    path("api/rigs/master/search/", views.rig_master_search_api, name="rig_master_search"),
    path("api/rigs/master/<int:rig_id>/", views.rig_master_get_api, name="rig_master_get"),
    path("api/rigs/master/save/", views.rig_master_save_api, name="rig_master_save"),
    path("api/rigs/master/<int:rig_id>/check-delete/", views.rig_master_check_delete_api, name="rig_master_check_delete"),
    path("api/rigs/master/<int:rig_id>/delete/", views.rig_master_delete_api, name="rig_master_delete"),

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
    path("api/listings/incidents/export/", views.listings_incidents_export, name="listings_incidents_export"),
    path("api/listings/hazard-cards/export/", views.listings_hazard_cards_export, name="listings_hazard_cards_export"),
    path("api/listings/employees/export/", views.listings_employees_export, name="listings_employees_export"),
    path("api/listings/staff/export/", views.listings_staff_export, name="listings_staff_export"),
    path("api/listings/crew-rotations/export/", views.listings_crew_rotations_export, name="listings_crew_rotations_export"),
    path("api/listings/invoices/export/", views.listings_invoices_export, name="listings_invoices_export"),
    path("api/listings/certificates/export/", views.listings_certificates_export, name="listings_certificates_export"),
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
    path("api/listings/users/export/", views.listings_users_export, name="listings_users_export"),
    path("api/listings/users/", views.listings_users_api, name="listings_users_api"),

    # ── Health API ──────────────────────────────────────────────────────────
    path("api/health/", views.health_api, name="health_api"),

    # ── Admin panel ─────────────────────────────────────────────────────────
    path("admin-panel/", RedirectView.as_view(url="/admin-panel/user-rights/", permanent=False)),
    path("admin-panel/user-rights/", views.admin_user_rights_page, name="admin_user_rights"),
    path("api/admin/users/", views.admin_users_api, name="admin_users_api"),
    path("api/admin/users/<int:user_id>/permissions/", views.admin_user_perms_api, name="admin_user_perms_api"),
    path("api/admin/users/<int:user_id>/permissions/save/", views.admin_user_perms_save_api, name="admin_user_perms_save_api"),
    path("api/admin/users/<int:user_id>/toggle-admin/", views.admin_user_admin_toggle_api, name="admin_user_admin_toggle_api"),

    path("admin-panel/user-management/", views.admin_user_management_page, name="admin_user_management"),
    path("api/admin/manage/meta/", views.admin_user_management_meta_api, name="admin_manage_meta"),
    path("api/admin/manage/users/", views.admin_user_management_list_api, name="admin_manage_users_list"),
    path("api/admin/manage/users/create/", views.admin_user_management_create_api, name="admin_manage_users_create"),
    path("api/admin/manage/users/<int:user_id>/", views.admin_user_management_get_api, name="admin_manage_users_get"),
    path("api/admin/manage/users/<int:user_id>/update/", views.admin_user_management_update_api, name="admin_manage_users_update"),
    path("api/admin/manage/users/<int:user_id>/set-password/", views.admin_user_management_set_password_api, name="admin_manage_users_set_password"),
    path("api/admin/manage/users/<int:user_id>/remove-password/", views.admin_user_management_remove_password_api, name="admin_manage_users_remove_password"),
    path("api/admin/manage/users/<int:user_id>/toggle-active/", views.admin_user_management_toggle_active_api, name="admin_manage_users_toggle_active"),

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
