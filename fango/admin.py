from django.contrib import admin, messages
from django.db.models import ForeignKey, ManyToManyField
from django.http import HttpResponseRedirect
from fastapi import HTTPException

from fango.auth import context_user


class AutoRawIdFieldsMixin:
    """
    Mixin for prevend FK and M2M data loading.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raw_id_fields = tuple(
            [field.name for field in self.model._meta.get_fields() if type(field) in (ForeignKey, ManyToManyField)]
        )


class FangoTabularInline(AutoRawIdFieldsMixin, admin.TabularInline):
    """
    Base TabularInline class with auto use raw_id_fields.

    """


class FangoStackedInline(AutoRawIdFieldsMixin, admin.StackedInline):
    """
    Base StackedInline class with auto use raw_id_fields.

    """


class FangoModelAdmin(AutoRawIdFieldsMixin, admin.ModelAdmin):
    """
    Base ModelAdmin class with set context_user var and auto use raw_id_fields.

    """

    def save_model(self, request, obj, form, change):
        context_user.set(request.user)
        super().save_model(request, obj, form, change)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        try:
            return super().changeform_view(request, object_id, form_url, extra_context)
        except HTTPException as e:
            self.message_user(request, e.detail, level=messages.ERROR)
            return HttpResponseRedirect(request.path)
