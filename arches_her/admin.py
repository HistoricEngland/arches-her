'''
ARCHES - a program developed to inventory and manage immovable cultural heritage.
Copyright (C) 2013 J. Paul Getty Trust and World Monuments Fund

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
'''

from .models.models import HeritageApiLog, HeritageApiExclusion
from django.contrib import admin
from guardian.admin import GuardedModelAdmin
import json
from django.utils.safestring import mark_safe
from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import HtmlFormatter


def format_json_field(data, style="colorful"):
    response = json.dumps(data, sort_keys=True, indent=2)
    formatter = HtmlFormatter(style=style)
    response = highlight(response, JsonLexer(), formatter)
    style = "<style>" + formatter.get_style_defs() + "</style><br>"
    return mark_safe(style + response)


class GuardedAdmin(GuardedModelAdmin):
    pass


class ReadOnlyAdminMixin:
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class HeritageApiLogAdmin(admin.ModelAdmin, ReadOnlyAdminMixin):
    readonly_fields = (
        "pretty_totals",
        "pretty_messages",
        "pretty_resources",
        "pretty_exceptions",
    )
    exclude = ("messages", "totals", "resources", "exceptions")
    list_display = (
        "batch_id",
        "start",
        "finish",
        "run_type",
        "id",
    )
    search_fields = ["batch_id"]

    def pretty_messages(self, instance):
        return format_json_field(instance.messages)

    pretty_messages.short_description = "Messages"

    def pretty_totals(self, instance):
        return format_json_field(instance.totals)

    pretty_totals.short_description = "Totals"

    def pretty_resources(self, instance):
        return format_json_field(instance.resources)

    pretty_resources.short_description = "Resources"

    def pretty_exceptions(self, instance):
        return format_json_field(instance.exceptions)

    pretty_exceptions.short_description = "Exceptions"


class HeritageApiExclusionAdmin(admin.ModelAdmin):
    readonly_fields = (
        "id",
        "created",
    )
    search_fields = ["resource_id"]
    list_display = (
        "resource_id",
        "created",
        "id",
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ("resource_id",)
        return self.readonly_fields


admin.site.register(HeritageApiLog, HeritageApiLogAdmin)
admin.site.register(HeritageApiExclusion, HeritageApiExclusionAdmin)
