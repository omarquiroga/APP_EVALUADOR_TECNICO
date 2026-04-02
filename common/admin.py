from django.contrib import admin


class SafeReadOnlyAdmin(admin.ModelAdmin):
    """Read-only admin: view only, no add, no edit, no delete."""

    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in ("GET", "HEAD", "OPTIONS")

    def has_view_permission(self, request, obj=None):
        return True

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_delete_permission(self, request, obj=None):
        return False


class HistoricalAdmin(SafeReadOnlyAdmin):
    readonly_fields = ("created_at", "created_by", "version_no", "supersedes")


class AuditAdmin(SafeReadOnlyAdmin):
    readonly_fields = "__all__"


class AddOnlyAdmin(admin.ModelAdmin):
    """Allows creation, but existing records become read-only."""

    actions = None

    def has_view_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        return request.method in ("GET", "HEAD", "OPTIONS")

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return [field.name for field in self.model._meta.fields]
        return list(getattr(super(), "readonly_fields", []))


class ReadOnlyTabularInline(admin.TabularInline):
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]
