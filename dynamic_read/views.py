from .serializers import DynamicReadSerializerMixin


class DynamicReadViewMixin(object):
    optimize_queryset = False

    @property
    def fields(self):
        unparsed = self.request.query_params.get("fields", "")
        return unparsed.split(",") if unparsed else None

    @property
    def omit(self):
        unparsed = self.request.query_params.get("omit", "")
        return unparsed.split(",") if unparsed else None

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
                optimize_queryset=self.optimize_queryset,
                **kwargs,
            )
        return serializer_class(*args, **kwargs)
