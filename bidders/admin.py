from django.contrib import admin

from .models import Bidder, BidderMember


class BidderMemberInline(admin.TabularInline):
    model = BidderMember
    extra = 0


@admin.register(Bidder)
class BidderAdmin(admin.ModelAdmin):
    list_display = ("name", "process", "identification_type", "identification_number", "bidder_type", "state")
    list_filter = ("state", "bidder_type", "process")
    search_fields = ("name", "identification_number", "process__code", "process__name")
    readonly_fields = ("created_at", "created_by", "updated_at", "updated_by", "row_version")
    inlines = [BidderMemberInline]


@admin.register(BidderMember)
class BidderMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "bidder", "identification_type", "identification_number", "participation_percentage", "is_lead")
    list_filter = ("is_lead", "member_role")
    search_fields = ("name", "identification_number", "bidder__name", "bidder__process__code")
    readonly_fields = ("created_at", "created_by", "updated_at", "updated_by", "row_version")
