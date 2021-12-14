from .serializers import DynamicReadSerializerMixin


class DynamicReadViewMixin(object):
    optimize_queryset = False

    @property
    def fields(self):
        unparsed = self.request.query_params.get("fields", "")
        return tuple(unparsed.split(",")) if unparsed else tuple()

    @property
    def omit(self):
        unparsed = self.request.query_params.get("omit", "")
        return tuple(unparsed.split(",")) if unparsed else tuple()

    def get_queryset(self):
        queryset = super().get_queryset()
        serializer_class = self.get_serializer_class()
        if (
            self.optimize_queryset
            and issubclass(serializer_class, DynamicReadSerializerMixin)
            and self.request.method == "GET"
        ):
            return serializer_class.optimize_queryset(
                filter_fields=self.fields,
                omit_fields=self.omit,
                queryset=queryset
            )
        return queryset

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs.setdefault("context", self.get_serializer_context())
        if (
            issubclass(serializer_class, DynamicReadSerializerMixin)
            and self.request.method == "GET"
        ):
            return serializer_class(
                *args,
                filter_fields=self.fields,
                omit_fields=self.omit,
                **kwargs,
            )
        return serializer_class(*args, **kwargs)
