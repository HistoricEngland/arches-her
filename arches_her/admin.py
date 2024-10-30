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

from .models.models import HeritageApiLog
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


# class HeritageApiLogAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
class HeritageApiLogAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    readonly_fields = (
        "pretty_totals",
        "pretty_messages",
    )
    exclude = ("messages", "totals")
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


admin.site.register(HeritageApiLog, HeritageApiLogAdmin)
