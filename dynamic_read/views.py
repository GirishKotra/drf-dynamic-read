from functools import cached_property

from .serializers import DynamicReadSerializerMixin
from .dynamic_orm import get_prefetch_select


class DynamicReadBaseViewMixin(object):
    _subclasses = []

    @classmethod
    def get_concrete_classes(cls):
        return list(cls._subclasses)

    def __init_subclass__(cls):
        if cls.queryset and cls.serializer_class:
            DynamicReadBaseViewMixin._subclasses.append(cls)

    @cached_property
    def fields(self):
        return self.request.query_params.get("fields", "").split(",")

    @cached_property
    def omit(self):
        return self.request.query_params.get("omit", "").split(",")

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())
        if issubclass(serializer_class, DynamicReadSerializerMixin):
            return serializer_class(
                *args,
                dynamic_filter_fields=self.fields,
                dynamic_omit_fields=self.omit,
                **kwargs
            )
        return serializer_class(*args, **kwargs)


class DynamicReadORMViewMixin(DynamicReadBaseViewMixin):
    def get_queryset(self):
        queryset = super(DynamicReadORMViewMixin, self).get_queryset()
        if (
            self.request.method == "GET"
            and issubclass(self.serializer_class, DynamicReadSerializerMixin)
        ):
            fields, omit = tuple(self.fields), tuple(self.omit)

            if not fields[0]:
                fields = ()
            if not omit[0]:
                omit = ()

            select, prefetch = get_prefetch_select(
                self.get_serializer().__class__, fields, omit,
            )

            if select:
                queryset = queryset.select_related(*select)
            if prefetch:
                queryset = queryset.prefetch_related(*prefetch)

        return queryset
