from django.contrib import admin

from common.admin import HistoricalAdmin
from .models import BidderMemberExternalCheck, ExternalCheckSource


@admin.register(ExternalCheckSource)
class ExternalCheckSourceAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "homepage_url", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    readonly_fields = ("created_at", "created_by", "updated_at", "updated_by", "row_version")


@admin.register(BidderMemberExternalCheck)
class BidderMemberExternalCheckAdmin(HistoricalAdmin):
    list_display = ("bidder_member", "bidder", "process", "source", "query_type", "result_status", "requires_human_review", "version_no")
    list_filter = ("result_status", "requires_human_review", "source")
    search_fields = ("bidder_member__name", "bidder__name", "query_value", "notes")
