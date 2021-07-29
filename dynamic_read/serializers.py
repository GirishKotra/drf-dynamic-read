from django.utils.functional import cached_property
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ListSerializer
from rest_framework.utils.serializer_helpers import BindingDict

from .utils import get_prefetch_select, process_field_options, get_relational_fields
from .exceptions import ChildNotSupported


def sub_class_hook(cls):
    if (
        hasattr(cls, "Meta")
        and hasattr(cls.Meta, "model")
        and not cls.Meta.model._meta.abstract
    ):
        cls._all_select_prefetch = cls.get_all_select_prefetch()
    else:
        cls.__init_subclass__ = classmethod(sub_class_hook)


class DynamicReadSerializerMixin(object):
    """
    A serializer mixin that takes some additional arguments that controls
    which fields should be displayed, and respective queryset optimizations.
    """

    __init_subclass__ = classmethod(sub_class_hook)

    def __init__(
        self,
        *args,
        filter_fields=None,
        omit_fields=None,
        optimize_queryset=False,
        **kwargs,
    ):
        """
        Overrides the original __init__ to support disabling dynamic flex fields.

        :param args:
        :param kwargs:
        :param filter_fields: This represents list of fields that should be allowed for serialization
        :param omit_fields: This represents list of fields that shouldn't be allowed for serialization
        :param optimize_queryset: boolean to enable/disable queryset optimizations

        """

        assert not bool(
            filter_fields and omit_fields,
        ), "Pass either filter_fields or omit_fields, not both"

        # type casting to tuple
        filter_fields, omit_fields = (
            tuple() if not filter_fields else tuple(filter_fields),
            tuple() if not omit_fields else tuple(omit_fields),
        )

        self.dr_meta = (
            process_field_options(filter_fields, omit_fields)
            if filter_fields or omit_fields
            else None
        )
        if optimize_queryset:
            queryset = args[0]
            select, prefetch = get_prefetch_select(
                self.__class__, filter_fields, omit_fields
            )
            if select:
                queryset = queryset.select_related(*select)
            if prefetch:
                queryset = queryset.prefetch_related(*prefetch)
            args = (queryset, *args[1:])

        super(DynamicReadSerializerMixin, self).__init__(*args, **kwargs)

    def extract_serializer_from_child(self, child):
        """Child object can be a ListSerializer, PresentablePrimaryKeyRelatedField, etc. This method is responsible to
        return a DynamicReadSerializerMixin object(desired child), Override this to handle additional types of child and
        perform a super call if you want the ListSerializer child type to be handled if input child type is not known
        exit raising ChildNotSupported exception."""
        if isinstance(child, DynamicReadSerializerMixin):
            return child

        if isinstance(child, ListSerializer) and isinstance(
            child.child, DynamicReadSerializerMixin,
        ):
            return child.child

        raise ChildNotSupported(child)

    def derive_desired_fields(self, field_names, fields_map) -> set:
        # derive final set of field names wrt fields, omit
        if self.dr_meta["omit"]:
            desired_field_names = field_names - self.dr_meta["omit"]
        else:
            desired_field_names = (
                field_names
                if self.dr_meta["fields"] == "__all__"
                else self.dr_meta["fields"].intersection(field_names)
            )

        # attach dr_meta to necessary children
        for field, field_meta in self.dr_meta["nested"].items():
            try:
                nested_field = self.extract_serializer_from_child(fields_map[field])
                nested_field.dr_meta = field_meta
            except KeyError:
                continue

        # (optional) process id_fields and update the fields_map respectively
        for field in self.dr_meta["id_fields"]:
            real_field = field.split("_id")[0]
            try:
                # if a write_only PrimaryKeyRelatedField is defined
                if field in fields_map and isinstance(
                    fields_map[field], PrimaryKeyRelatedField,
                ):
                    fields_map[field].write_only = False
                    desired_field_names.add(field)

                # if not defined, then reroute to default fk serializer field
                elif real_field in fields_map and isinstance(
                    fields_map[real_field], PrimaryKeyRelatedField,
                ):
                    fields_map[field] = fields_map[real_field]
                    fields_map[field].write_only = False
                    desired_field_names.add(field)
            except KeyError:
                continue
        return desired_field_names

    @cached_property
    def fields(self):
        """
        A dictionary of {field_name: field_instance}.
        Overridden method to support dynamic selection of fields during serialization
        check rest_framework.serializers.Serializer.fields for source definition
        """
        # `fields` is evaluated lazily. We do this to ensure that we don't
        # have issues importing modules that use ModelSerializers as fields,
        # even if Django's app-loading stage has not yet run.

        fields = BindingDict(self)
        fields_map = self.get_fields()
        field_names = set(fields_map.keys())
        if self.dr_meta:
            field_names = self.derive_desired_fields(field_names, fields_map)
        for field in field_names:
            fields[field] = fields_map[field]
        return fields

    def evaluate_select_prefetch(self, accessor_prefix=""):
        final_select = []
        final_prefetch = []
        serializer_obj = self.child if isinstance(self, ListSerializer) else self
        relational_fields = get_relational_fields(serializer_obj.__class__)
        for field_name, field_obj in serializer_obj.fields.items():
            field_name = (field_obj.source or field_name).split(".")[0]
            if field_name not in relational_fields:
                continue
            is_many = isinstance(field_obj, ListSerializer)
            field_obj = field_obj.child if is_many else field_obj
            if isinstance(field_obj, DynamicReadSerializerMixin):
                (
                    sub_select_related,
                    sub_prefetch_related,
                ) = field_obj.evaluate_select_prefetch(
                    accessor_prefix=f"{accessor_prefix}{field_name}__",
                )
                if sub_select_related:
                    if not is_many:
                        final_select.extend(sub_select_related)
                    else:
                        final_prefetch.extend(sub_select_related)
                elif not is_many:
                    final_select.append(f"{accessor_prefix}{field_name}")
                if sub_prefetch_related:
                    final_prefetch.extend(sub_prefetch_related)
                elif is_many:
                    final_prefetch.append(f"{accessor_prefix}{field_name}")
        return final_select, final_prefetch

    @classmethod
    def get_all_select_prefetch(cls):
        if hasattr(cls, "_all_select_prefetch"):
            return cls._all_select_prefetch
        return cls().evaluate_select_prefetch()
