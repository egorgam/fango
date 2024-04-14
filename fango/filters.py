from typing import cast

from django.db.models import Q
from django_filters import (
    BaseInFilter,
    BooleanFilter,
    CharFilter,
    DateFilter,
    DateTimeFilter,
    Filter,
    FilterSet,
    NumberFilter,
    TimeFilter,
    UUIDFilter,
)
from pydantic import BaseModel

from fango.adapters import types


class ArrayFilter(BaseInFilter, CharFilter):
    pass


class LimitedListFilter(Filter):
    """
    Класс реализует фильтр, способный фильтровать startswith и endswith элементы в массиве.
    Ограничения Django ORM таковы, что единственный способ делать это через БД - лимитировать
    количество элементов в списке, по которым будет происходить поиск. То есть, мы можем искать
    по всем записям в таблице, но по N первых элементов массива.

    NOTE: рекомендую отключить возможность делать такие лукапы для списков.

    """

    LOOKUP_ELEMENTS = 100

    def filter(self, qs, value):
        if value:
            query = Q(**{f"{self.field_name}__0__{self.lookup_expr}": value})
            for i in range(1, self.LOOKUP_ELEMENTS):
                query |= Q(**{f"{self.field_name}__{i}__{self.lookup_expr}": value})
            qs = qs.filter(query)
        return qs


def generate_filterset_by_pydantic(schema: type[BaseModel]) -> type[FilterSet]:
    """
    Function generates django-filters FilterSet, based on pydantic schema fields.

    """
    attrs = {}

    for field_name, field in schema.model_fields.items():
        if types.is_bool(field):
            attrs[field_name] = BooleanFilter(field_name=field_name)

        elif types.is_uuid(field):
            attrs[field_name] = UUIDFilter(field_name=field_name)

        elif types.is_time(field):
            attrs[field_name] = TimeFilter(field_name=field_name)
            attrs[field_name + "_gt"] = TimeFilter(field_name=field_name, lookup_expr="gt")
            attrs[field_name + "_gte"] = TimeFilter(field_name=field_name, lookup_expr="gte")
            attrs[field_name + "_lt"] = TimeFilter(field_name=field_name, lookup_expr="lt")
            attrs[field_name + "_lte"] = TimeFilter(field_name=field_name, lookup_expr="lte")

        elif types.is_datetime(field):
            attrs[field_name] = DateTimeFilter(field_name=field_name)
            attrs[field_name + "_gt"] = DateTimeFilter(field_name=field_name, lookup_expr="gt")
            attrs[field_name + "_gte"] = DateTimeFilter(field_name=field_name, lookup_expr="gte")
            attrs[field_name + "_lt"] = DateTimeFilter(field_name=field_name, lookup_expr="lt")
            attrs[field_name + "_lte"] = DateTimeFilter(field_name=field_name, lookup_expr="lte")

        elif types.is_date(field):
            attrs[field_name] = DateFilter(field_name=field_name)
            attrs[field_name + "_gt"] = DateFilter(field_name=field_name, lookup_expr="gt")
            attrs[field_name + "_gte"] = DateFilter(field_name=field_name, lookup_expr="gte")
            attrs[field_name + "_lt"] = DateFilter(field_name=field_name, lookup_expr="lt")
            attrs[field_name + "_lte"] = DateFilter(field_name=field_name, lookup_expr="lte")

        elif types.is_numeric(field):
            attrs[field_name] = NumberFilter(field_name=field_name)
            attrs[field_name + "_gt"] = NumberFilter(field_name=field_name, lookup_expr="gt")
            attrs[field_name + "_gte"] = NumberFilter(field_name=field_name, lookup_expr="gte")
            attrs[field_name + "_lt"] = NumberFilter(field_name=field_name, lookup_expr="lt")
            attrs[field_name + "_lte"] = NumberFilter(field_name=field_name, lookup_expr="lte")

        elif types.is_list(field):
            attrs[field_name] = ArrayFilter(field_name=field_name, lookup_expr="exact")
            attrs[field_name + "_contains"] = CharFilter(field_name=field_name, lookup_expr="icontains")
            attrs[field_name + "_starts"] = LimitedListFilter(field_name=field_name, lookup_expr="istartswith")
            attrs[field_name + "_ends"] = LimitedListFilter(field_name=field_name, lookup_expr="iendswith")

        else:
            attrs[field_name] = CharFilter(field_name=field_name, lookup_expr="exact")
            attrs[field_name + "_contains"] = CharFilter(field_name=field_name, lookup_expr="icontains")
            attrs[field_name + "_starts"] = CharFilter(field_name=field_name, lookup_expr="istartswith")
            attrs[field_name + "_ends"] = CharFilter(field_name=field_name, lookup_expr="iendswith")

    return cast(type[FilterSet], type(f"{schema.__name__}FilterSet", (FilterSet,), attrs))
