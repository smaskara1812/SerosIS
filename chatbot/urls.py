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
    path("masters/travel-eligibility/", views.travel_eligibility_page, name="travel_eligibility"),
    path("masters/reporting-structure/", views.reporting_structure_page, name="reporting_structure"),
    path("masters/rig-operation/", views.rig_operation_page, name="rig_operation"),
    path("masters/contact-exposure-type/", views.contact_exposure_type_page, name="contact_exposure_type"),
    path("masters/indicator-type/", views.indicator_type_page, name="indicator_type"),
    path("masters/indicator-subtype/", views.indicator_subtype_page, name="indicator_subtype"),
    path("masters/parts-of-body/", views.parts_of_body_page, name="parts_of_body"),
    path("masters/qhse-category/", views.qhse_category_page, name="qhse_category"),
    path("masters/hse-activity/", views.hse_activity_page, name="hse_activity"),
    path("masters/hse-consumable/", views.hse_consumable_page, name="hse_consumable"),
    path("masters/hazard-type/", views.hazard_type_page, name="hazard_type"),

    # ── Contractor Master API ──────────────────────────────────────────────────
    path("api/masters/contractor/", views.contractor_list_api, name="contractor_list"),
    path("api/masters/contractor/save/", views.contractor_save_api, name="contractor_save"),
    path("api/masters/contractor/<int:contractor_id>/", views.contractor_get_api, name="contractor_get"),
    path("api/masters/contractor/<int:contractor_id>/check-delete/", views.contractor_check_delete_api, name="contractor_check_delete"),
    path("api/masters/contractor/<int:contractor_id>/delete/", views.contractor_delete_api, name="contractor_delete"),

    # ── Rig Operation Master API ───────────────────────────────────────────────
    path("api/masters/rig-operation/", views.rig_operation_list_api, name="rig_operation_list"),
    path("api/masters/rig-operation/save/", views.rig_operation_save_api, name="rig_operation_save"),
    path("api/masters/rig-operation/<int:op_id>/", views.rig_operation_get_api, name="rig_operation_get"),
    path("api/masters/rig-operation/<int:op_id>/check-delete/", views.rig_operation_check_delete_api, name="rig_operation_check_delete"),
    path("api/masters/rig-operation/<int:op_id>/delete/", views.rig_operation_delete_api, name="rig_operation_delete"),

    # ── Contact Exposure Type Master API ───────────────────────────────────────
    path("api/masters/contact-exposure-type/", views.contact_exposure_type_list_api, name="contact_exposure_type_list"),
    path("api/masters/contact-exposure-type/save/", views.contact_exposure_type_save_api, name="contact_exposure_type_save"),
    path("api/masters/contact-exposure-type/<int:type_id>/", views.contact_exposure_type_get_api, name="contact_exposure_type_get"),
    path("api/masters/contact-exposure-type/<int:type_id>/check-delete/", views.contact_exposure_type_check_delete_api, name="contact_exposure_type_check_delete"),
    path("api/masters/contact-exposure-type/<int:type_id>/delete/", views.contact_exposure_type_delete_api, name="contact_exposure_type_delete"),

    # ── Indicator Type Master API ──────────────────────────────────────────────
    path("api/masters/indicator-type/", views.indicator_type_list_api, name="indicator_type_list"),
    path("api/masters/indicator-type/save/", views.indicator_type_save_api, name="indicator_type_save"),
    path("api/masters/indicator-type/<int:type_id>/", views.indicator_type_get_api, name="indicator_type_get"),
    path("api/masters/indicator-type/<int:type_id>/check-delete/", views.indicator_type_check_delete_api, name="indicator_type_check_delete"),
    path("api/masters/indicator-type/<int:type_id>/delete/", views.indicator_type_delete_api, name="indicator_type_delete"),

    # ── Indicator Subtype Master API ───────────────────────────────────────────
    path("api/masters/indicator-subtype/meta/", views.indicator_subtype_meta_api, name="indicator_subtype_meta"),
    path("api/masters/indicator-subtype/", views.indicator_subtype_list_api, name="indicator_subtype_list"),
    path("api/masters/indicator-subtype/save/", views.indicator_subtype_save_api, name="indicator_subtype_save"),
    path("api/masters/indicator-subtype/<int:subtype_id>/", views.indicator_subtype_get_api, name="indicator_subtype_get"),
    path("api/masters/indicator-subtype/<int:subtype_id>/check-delete/", views.indicator_subtype_check_delete_api, name="indicator_subtype_check_delete"),
    path("api/masters/indicator-subtype/<int:subtype_id>/delete/", views.indicator_subtype_delete_api, name="indicator_subtype_delete"),

    # ── Parts Of Body Master API (add/edit only) ───────────────────────────────
    path("api/masters/parts-of-body/", views.parts_of_body_list_api, name="parts_of_body_list"),
    path("api/masters/parts-of-body/save/", views.parts_of_body_save_api, name="parts_of_body_save"),
    path("api/masters/parts-of-body/<int:part_id>/", views.parts_of_body_get_api, name="parts_of_body_get"),

    # ── QHSE Category Master API (add/edit only) ───────────────────────────────
    path("api/masters/qhse-category/", views.qhse_category_list_api, name="qhse_category_list"),
    path("api/masters/qhse-category/save/", views.qhse_category_save_api, name="qhse_category_save"),
    path("api/masters/qhse-category/<int:cat_id>/", views.qhse_category_get_api, name="qhse_category_get"),

    # ── HSE Activity Master API ────────────────────────────────────────────────
    path("api/masters/hse-activity/", views.hse_activity_list_api, name="hse_activity_list"),
    path("api/masters/hse-activity/save/", views.hse_activity_save_api, name="hse_activity_save"),
    path("api/masters/hse-activity/<int:act_id>/", views.hse_activity_get_api, name="hse_activity_get"),
    path("api/masters/hse-activity/<int:act_id>/check-delete/", views.hse_activity_check_delete_api, name="hse_activity_check_delete"),
    path("api/masters/hse-activity/<int:act_id>/delete/", views.hse_activity_delete_api, name="hse_activity_delete"),

    # ── HSE Consumable Master API ──────────────────────────────────────────────
    path("api/masters/hse-consumable/", views.hse_consumable_list_api, name="hse_consumable_list"),
    path("api/masters/hse-consumable/save/", views.hse_consumable_save_api, name="hse_consumable_save"),
    path("api/masters/hse-consumable/<int:con_id>/", views.hse_consumable_get_api, name="hse_consumable_get"),
    path("api/masters/hse-consumable/<int:con_id>/check-delete/", views.hse_consumable_check_delete_api, name="hse_consumable_check_delete"),
    path("api/masters/hse-consumable/<int:con_id>/delete/", views.hse_consumable_delete_api, name="hse_consumable_delete"),

    # ── Hazard Type Master API ─────────────────────────────────────────────────
    path("api/masters/hazard-type/", views.hazard_type_list_api, name="hazard_type_list"),
    path("api/masters/hazard-type/save/", views.hazard_type_save_api, name="hazard_type_save"),
    path("api/masters/hazard-type/<int:haz_id>/", views.hazard_type_get_api, name="hazard_type_get"),
    path("api/masters/hazard-type/<int:haz_id>/check-delete/", views.hazard_type_check_delete_api, name="hazard_type_check_delete"),
    path("api/masters/hazard-type/<int:haz_id>/delete/", views.hazard_type_delete_api, name="hazard_type_delete"),

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

    # ── Travel Eligibility API ─────────────────────────────────────────────────
    path("api/masters/travel-eligibility/meta/", views.travel_eligibility_meta_api, name="travel_eligibility_meta"),
    path("api/masters/travel-eligibility/", views.travel_eligibility_list_api, name="travel_eligibility_list"),
    path("api/masters/travel-eligibility/save/", views.travel_eligibility_save_api, name="travel_eligibility_save"),
    path("api/masters/travel-eligibility/<int:rec_id>/", views.travel_eligibility_get_api, name="travel_eligibility_get"),
    path("api/masters/travel-eligibility/<int:rec_id>/check-delete/", views.travel_eligibility_check_delete_api, name="travel_eligibility_check_delete"),
    path("api/masters/travel-eligibility/<int:rec_id>/delete/", views.travel_eligibility_delete_api, name="travel_eligibility_delete"),
    path("api/masters/reporting-structure/meta/", views.reporting_structure_meta_api, name="reporting_structure_meta"),
    path("api/masters/reporting-structure/", views.reporting_structure_list_api, name="reporting_structure_list"),
    path("api/masters/reporting-structure/save/", views.reporting_structure_save_api, name="reporting_structure_save"),
    path("api/masters/reporting-structure/<int:rec_id>/", views.reporting_structure_get_api, name="reporting_structure_get"),
    path("api/masters/reporting-structure/<int:rec_id>/delete/", views.reporting_structure_delete_api, name="reporting_structure_delete"),

    path("masters/job-descriptions/", views.job_description_page, name="job_description"),
    path("api/masters/job-descriptions/meta/", views.job_description_meta_api, name="job_description_meta"),
    path("api/masters/job-descriptions/", views.job_description_list_api, name="job_description_list"),
    path("api/masters/job-descriptions/save/", views.job_description_save_hdr_api, name="job_description_save_hdr"),
    path("api/masters/job-descriptions/<int:hdr_id>/", views.job_description_get_api, name="job_description_get"),
    path("api/masters/job-descriptions/<int:hdr_id>/delete/", views.job_description_delete_hdr_api, name="job_description_delete_hdr"),
    path("api/masters/job-descriptions/dtl/save/", views.job_description_save_dtl_api, name="job_description_save_dtl"),
    path("api/masters/job-descriptions/dtl/<int:dtl_id>/delete/", views.job_description_delete_dtl_api, name="job_description_delete_dtl"),

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
    path("admin-panel/audit-trail/", views.admin_audit_trail_page, name="admin_audit_trail"),
    path("api/admin/audit/", views.admin_audit_list_api, name="admin_audit_list"),
    path("api/admin/audit/facets/", views.admin_audit_facets_api, name="admin_audit_facets"),
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
    # ── Competency Master ───────────────────────────────────────────────────
    path("api/me/perms/", views.me_perms_api, name="me_perms"),
    path("masters/competency/", views.competency_page, name="competency"),
    path("api/masters/competency/meta/", views.competency_meta_api, name="competency_meta"),
    path("api/masters/competency/", views.competency_list_api, name="competency_list"),
    path("api/masters/competency/save/", views.competency_save_api, name="competency_save"),
    path("api/masters/competency/<int:rec_id>/", views.competency_get_api, name="competency_get"),
    path("api/masters/competency/<int:rec_id>/check-delete/", views.competency_check_delete_api, name="competency_check_delete"),
    path("api/masters/competency/<int:rec_id>/delete/", views.competency_delete_api, name="competency_delete"),

    # ── Mapping Masters ────────────────────────────────────────────────────────
    path("api/masters/users-search/", views.mapping_users_search_api, name="mapping_users_search"),

    path("masters/user-rig-mapping/", views.user_rig_mapping_page, name="user_rig_mapping"),
    path("api/masters/user-rig-mapping/meta/", views.user_rig_mapping_meta_api, name="user_rig_mapping_meta"),
    path("api/masters/user-rig-mapping/", views.user_rig_mapping_list_api, name="user_rig_mapping_list"),
    path("api/masters/user-rig-mapping/save/", views.user_rig_mapping_save_api, name="user_rig_mapping_save"),
    path("api/masters/user-rig-mapping/<int:rec_id>/", views.user_rig_mapping_get_api, name="user_rig_mapping_get"),
    path("api/masters/user-rig-mapping/<int:rec_id>/delete/", views.user_rig_mapping_delete_api, name="user_rig_mapping_delete"),

    path("masters/user-category-mapping/", views.user_category_mapping_page, name="user_category_mapping"),
    path("api/masters/user-category-mapping/meta/", views.user_category_mapping_meta_api, name="user_category_mapping_meta"),
    path("api/masters/user-category-mapping/", views.user_category_mapping_list_api, name="user_category_mapping_list"),
    path("api/masters/user-category-mapping/save/", views.user_category_mapping_save_api, name="user_category_mapping_save"),
    path("api/masters/user-category-mapping/<int:rec_id>/", views.user_category_mapping_get_api, name="user_category_mapping_get"),
    path("api/masters/user-category-mapping/<int:rec_id>/delete/", views.user_category_mapping_delete_api, name="user_category_mapping_delete"),

    path("masters/rig-to-email-mapping/", views.rig_to_email_mapping_page, name="rig_to_email_mapping"),
    path("api/masters/rig-to-email-mapping/meta/", views.rig_to_email_mapping_meta_api, name="rig_to_email_mapping_meta"),
    path("api/masters/rig-to-email-mapping/", views.rig_to_email_mapping_list_api, name="rig_to_email_mapping_list"),
    path("api/masters/rig-to-email-mapping/save/", views.rig_to_email_mapping_save_api, name="rig_to_email_mapping_save"),
    path("api/masters/rig-to-email-mapping/<int:rec_id>/", views.rig_to_email_mapping_get_api, name="rig_to_email_mapping_get"),
    path("api/masters/rig-to-email-mapping/<int:rec_id>/delete/", views.rig_to_email_mapping_delete_api, name="rig_to_email_mapping_delete"),

    path("api/masters/employees-search/", views.mapping_employees_search_api, name="mapping_employees_search"),

    path("masters/doc-to-sign-mapping/", views.doc_to_sign_mapping_page, name="doc_to_sign_mapping"),
    path("api/masters/doc-to-sign-mapping/meta/", views.doc_to_sign_mapping_meta_api, name="doc_to_sign_mapping_meta"),
    path("api/masters/doc-to-sign-mapping/", views.doc_to_sign_mapping_list_api, name="doc_to_sign_mapping_list"),
    path("api/masters/doc-to-sign-mapping/save/", views.doc_to_sign_mapping_save_api, name="doc_to_sign_mapping_save"),
    path("api/masters/doc-to-sign-mapping/<int:rec_id>/", views.doc_to_sign_mapping_get_api, name="doc_to_sign_mapping_get"),
    path("api/masters/doc-to-sign-mapping/<int:rec_id>/delete/", views.doc_to_sign_mapping_delete_api, name="doc_to_sign_mapping_delete"),

    path("masters/interviewer-mapping/", views.interviewer_mapping_page, name="interviewer_mapping"),
    path("api/masters/interviewer-mapping/meta/", views.interviewer_mapping_meta_api, name="interviewer_mapping_meta"),
    path("api/masters/interviewer-mapping/sign-upload/", views.interviewer_sign_upload_api, name="interviewer_sign_upload"),
    path("api/masters/interviewer-mapping/", views.interviewer_mapping_list_api, name="interviewer_mapping_list"),
    path("api/masters/interviewer-mapping/save/", views.interviewer_mapping_save_api, name="interviewer_mapping_save"),
    path("api/masters/interviewer-mapping/<int:rec_id>/", views.interviewer_mapping_get_api, name="interviewer_mapping_get"),
    path("api/masters/interviewer-mapping/<int:rec_id>/delete/", views.interviewer_mapping_delete_api, name="interviewer_mapping_delete"),

    path("api/masters/locations-search/", views.mapping_locations_search_api, name="mapping_locations_search"),

    path("masters/project-contract/", views.project_contract_page, name="project_contract"),
    path("api/masters/project-contract/meta/", views.project_contract_meta_api, name="project_contract_meta"),
    path("api/masters/project-contract/", views.project_contract_list_api, name="project_contract_list"),
    path("api/masters/project-contract/save/", views.project_contract_save_api, name="project_contract_save"),
    path("api/masters/project-contract/<int:hdr_id>/", views.project_contract_get_api, name="project_contract_get"),
    path("api/masters/project-contract/<int:hdr_id>/delete/", views.project_contract_delete_api, name="project_contract_delete"),
    path("api/masters/project-contract/dtl/save/", views.project_contract_save_dtl_api, name="project_contract_save_dtl"),
    path("api/masters/project-contract/dtl/<int:dtl_id>/delete/", views.project_contract_delete_dtl_api, name="project_contract_delete_dtl"),

    path("masters/project-drilling-rates/", views.project_drilling_rates_page, name="project_drilling_rates"),
    path("api/masters/project-drilling-rates/meta/", views.project_drilling_rates_meta_api, name="project_drilling_rates_meta"),
    path("api/masters/project-drilling-rates/rigs/<int:project_id>/", views.project_drilling_rigs_api, name="project_drilling_rigs"),
    path("api/masters/project-drilling-rates/", views.project_drilling_rates_list_api, name="project_drilling_rates_list"),
    path("api/masters/project-drilling-rates/save/", views.project_drilling_rates_save_api, name="project_drilling_rates_save"),
    path("api/masters/project-drilling-rates/<int:rec_id>/delete/", views.project_drilling_rates_delete_api, name="project_drilling_rates_delete"),

    path("masters/drilling-operations/", views.drilling_operations_page, name="drilling_operations"),
    path("api/masters/drilling-operations/", views.drilling_operations_list_api, name="drilling_operations_list"),
    path("api/masters/drilling-operations/save/", views.drilling_operations_save_api, name="drilling_operations_save"),
    path("api/masters/drilling-operations/<int:ops_id>/", views.drilling_operations_get_api, name="drilling_operations_get"),
    path("api/masters/drilling-operations/<int:ops_id>/check-delete/", views.drilling_operations_check_delete_api, name="drilling_operations_check_delete"),
    path("api/masters/drilling-operations/<int:ops_id>/delete/", views.drilling_operations_delete_api, name="drilling_operations_delete"),

    path("masters/drilling-sections/", views.drilling_sections_page, name="drilling_sections"),
    path("api/masters/drilling-sections/", views.drilling_sections_list_api, name="drilling_sections_list"),
    path("api/masters/drilling-sections/save/", views.drilling_sections_save_api, name="drilling_sections_save"),
    path("api/masters/drilling-sections/<int:sec_id>/", views.drilling_sections_get_api, name="drilling_sections_get"),
    path("api/masters/drilling-sections/<int:sec_id>/check-delete/", views.drilling_sections_check_delete_api, name="drilling_sections_check_delete"),
    path("api/masters/drilling-sections/<int:sec_id>/delete/", views.drilling_sections_delete_api, name="drilling_sections_delete"),

    path("api/manuals/upload/", views.manual_upload, name="manual_upload"),
    path("api/manuals/ingest/", views.manual_ingest_start, name="manual_ingest_start"),
    path("api/manuals/ingest/status/", views.manual_ingest_status, name="manual_ingest_status"),
    path("api/manuals/<str:filename>/delete/", views.manual_delete, name="manual_delete"),
]
