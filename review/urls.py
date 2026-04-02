from django.urls import path

from . import views


app_name = "review"


urlpatterns = [
    path("processes/", views.process_list, name="process_list"),
    path("processes/<uuid:process_id>/", views.process_detail, name="process_detail"),
    path("processes/<uuid:process_id>/bidders/", views.process_bidder_list, name="process_bidder_list"),
    path("processes/<uuid:process_id>/bidders/<uuid:bidder_id>/", views.bidder_dossier, name="bidder_dossier"),
    path(
        "processes/<uuid:process_id>/bidders/<uuid:bidder_id>/finance/",
        views.finance_overview,
        name="finance_overview",
    ),
    path(
        "processes/<uuid:process_id>/bidders/<uuid:bidder_id>/finance/input/new/",
        views.financial_input_create,
        name="financial_input_create",
    ),
    path(
        "processes/<uuid:process_id>/bidders/<uuid:bidder_id>/finance/input/<uuid:input_id>/assessment/new/",
        views.financial_assessment_create,
        name="financial_assessment_create",
    ),
    path(
        "processes/<uuid:process_id>/bidders/<uuid:bidder_id>/finance/input/<uuid:input_id>/",
        views.financial_input_detail,
        name="financial_input_detail",
    ),
    path(
        "processes/<uuid:process_id>/bidders/<uuid:bidder_id>/sections/<str:section>/",
        views.bidder_dossier_section,
        name="bidder_dossier_section",
    ),
]
