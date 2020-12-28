from serializers import DynamicReadSerializerMixin
from dynamic_orm import get_prefetch_select


class DynamicReadViewMixin(object):
    _subclasses = []

    @classmethod
    def get_concrete_classes(cls):
        return list(cls._subclasses)

    def __init_subclass__(cls):
        if cls.queryset and cls.serializer_class:
            DynamicReadViewMixin._subclasses.append(cls)

    def get_queryset(self):
        queryset = super(DynamicReadViewMixin, self).get_queryset()
        if (
            self.request.method == "GET"
            and hasattr(self, "serializer_class")
            and self.serializer_class
            and issubclass(self.serializer_class, DynamicReadSerializerMixin)
        ):
            fields, omit = (
                tuple(self.request.query_params.get("fields", "").split(",")),
                tuple(self.request.query_params.get("omit", "").split(",")),
            )

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
