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

from .models.models import (
    HeritageApiConceptMapping,
    HeritageApiLog,
    HeritageApiExclusion,
    HeritageApiInclusion,
    HeritageApiData,
)
from django.contrib import admin
from django import forms
from guardian.admin import GuardedModelAdmin
import json
import logging
from django.utils.safestring import mark_safe
from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import HtmlFormatter
from django.contrib import messages
from django.core.exceptions import ValidationError


logger = logging.getLogger(__name__)


def add_text_wrap_mode(style_defs):
    # Find the .s2 class definition
    start_index = style_defs.find('.s2 {')
    if start_index == -1:
        return style_defs  # .s2 class not found, return original string

    # Find the end of the .s2 class definition
    end_index = style_defs.find('}', start_index)
    if end_index == -1:
        return style_defs  # Malformed CSS, return original string

    # Insert the new property before the closing brace
    new_property = '; text-wrap-mode: wrap; '
    updated_style_defs = style_defs[:end_index] + \
        new_property + style_defs[end_index:]

    return updated_style_defs


formatter = HtmlFormatter(style="colorful")
style_defs = add_text_wrap_mode(formatter.get_style_defs())
maximum_pretty_print = 500


def format_json_field(data, style="colorful", prettify=True, sort_keys=False):
    response = json.dumps(data, sort_keys=sort_keys, indent=4)
    if prettify:
        response = highlight(response, JsonLexer(), formatter)
        style = "<style>" + style_defs + "</style><br>"
        return mark_safe(style + response)
    else:
        return mark_safe(f"<pre>{response}</pre>")


class GuardedAdmin(GuardedModelAdmin):
    pass


class ReadOnlyAdminMixin:
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class NoEditAdminMixin:
    def has_change_permission(self, request, obj=None):
        return False


class HeritageApiLogAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    readonly_fields = (
        "pretty_totals",
        "pretty_messages",
        "pretty_resources",
        "pretty_exceptions",
        "pretty_parameters",
    )
    exclude = ("messages", "totals", "resources", "exceptions", "parameters")
    list_display = (
        "batch_id",
        "start",
        "finish",
        "run_type",
        "id",
    )
    search_fields = ["batch_id"]
    ordering = ["-start"]
    list_per_page = 20

    def pretty_messages(self, instance):
        return format_json_field(instance.messages)

    pretty_messages.short_description = "Messages"

    def pretty_totals(self, instance):
        return format_json_field(instance.totals)

    pretty_totals.short_description = "Totals"

    def pretty_resources(self, instance):
        resources = instance.resources or {}
        prettify = len(resources) <= maximum_pretty_print
        return format_json_field(resources, prettify=prettify)

    pretty_resources.short_description = "Resources"

    def pretty_exceptions(self, instance):
        return format_json_field(instance.exceptions)

    pretty_exceptions.short_description = "Exceptions"

    def pretty_parameters(self, instance):
        return format_json_field(instance.parameters)

    pretty_parameters.short_description = "Parameters"


class HeritageApiExclusionAdmin(NoEditAdminMixin, admin.ModelAdmin):
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

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except ValidationError:
            if hasattr(obj, '_validation_error'):
                messages.error(request, obj._validation_error.message)


class HeritageApiInclusionAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
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

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except ValidationError:
            if hasattr(obj, '_validation_error'):
                messages.error(request, obj._validation_error.message)


class HeritageApiDataAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    fields = ['batch_id', 'part', 'timestamp', 'pretty_validation',
              'pretty_data', 'id', 'hapi_log_id']
    readonly_fields = (
        "pretty_data",
        "pretty_validation",
    )
    exclude = (
        "data",
        "validation",
    )
    list_display = (
        "batch_id",
        "timestamp",
        "part",
        "id",
        "hapi_log_id",
    )
    search_fields = ["batch_id"]
    ordering = ["-batch_id", "-timestamp"]
    list_per_page = 20

    def pretty_data(self, instance):
        return format_json_field(instance.data, sort_keys=True)

    pretty_data.short_description = "Data"

    def pretty_validation(self, instance):
        return format_json_field(instance.validation)

    pretty_validation.short_description = "Validation"


class HeritageApiConceptMappingAdmin(admin.ModelAdmin):
    class ConceptMappingAdminForm(forms.ModelForm):
        class Meta:
            model = HeritageApiConceptMapping
            fields = "__all__"
            labels = {
                "hapi_field": "H.API field",
                "source_concept": "Source concept  (narrow)",
                "heritage_gateway_concept": "Heritage Gateway concept (broad)",
            }

    form = ConceptMappingAdminForm
    list_display = (
        "hapi_field",
        "source_concept",
        "mandatory",
        "heritage_gateway_concept",
    )
    search_fields = [
        "hapi_field",
        "source_concept",
        "mandatory",
        "heritage_gateway_concept",
    ]
    ordering = ["hapi_field"]


admin.site.register(HeritageApiLog, HeritageApiLogAdmin)
admin.site.register(HeritageApiExclusion, HeritageApiExclusionAdmin)
admin.site.register(HeritageApiInclusion, HeritageApiInclusionAdmin)
admin.site.register(HeritageApiData, HeritageApiDataAdmin)
admin.site.register(HeritageApiConceptMapping, HeritageApiConceptMappingAdmin)
