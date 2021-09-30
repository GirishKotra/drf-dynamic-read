from django.db.models import QuerySet

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
            if self.optimize_queryset:
                serializer_feed = args[0]
                if isinstance(serializer_feed, QuerySet):
                    args = list(args)
                    args[0] = serializer_class.optimize_queryset(
                        filter_fields=self.fields,
                        omit_fields=self.omit,
                        queryset=serializer_feed
                    )
            return serializer_class(
                *args,
                filter_fields=self.fields,
                omit_fields=self.omit,
                **kwargs,
            )
        return serializer_class(*args, **kwargs)
