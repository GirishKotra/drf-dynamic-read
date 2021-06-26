from contextlib import suppress
from itertools import groupby

from rest_framework.serializers import ListSerializer
from collections import OrderedDict
from functools import lru_cache
from operator import itemgetter, attrgetter


class ChildNotSupported(Exception):
    """Represents a child object cannot be used with dynamic drf"""

    def __init__(self, child):
        self.child = child

    def __str__(self):
        return f"ChildNotSupported: {self.child}"


@lru_cache(maxsize=1024)
def split_fields(fields: tuple):
    return tuple((each.split("__") for each in fields))


class DynamicReadSerializerMixin(object):
    """
    A serializer mixin that takes an additional `fields` argument that controls
    which fields should be displayed.
    """

    __slots__ = ("dynamic_filter_fields", "dynamic_omit_fields", "disable_dynamic_read")
    _subclasses = []

    @staticmethod
    def get_concrete_classes():
        return list(DynamicReadSerializerMixin._subclasses)

    def __init_subclass__(cls):
        DynamicReadSerializerMixin._subclasses.append(cls)

    def __init__(
        self,
        *args,
        dynamic_filter_fields=None,
        dynamic_omit_fields=None,
        disable_dynamic_read=False,
        **kwargs,
    ):
        """
        Overrides the original __init__ to support disabling dynamic flex fields.

        :param args:
        :param kwargs:
        :param dynamic_filter_fields: This represents list of fields that should be allowed for serialization
        :param dynamic_omit_fields: This represents list of fields that shouldn't be allowed for serialization
        :param disable_dynamic_read: This field decides whether to enable/disable dynamic read

        """

        self.dynamic_filter_fields = (
            split_fields(dynamic_filter_fields) if dynamic_filter_fields else []
        )
        self.dynamic_omit_fields = (
            split_fields(dynamic_omit_fields) if dynamic_omit_fields else []
        )
        self.disable_dynamic_read = disable_dynamic_read

        super(DynamicReadSerializerMixin, self).__init__(*args, **kwargs)

    @property
    def fields(self):
        """
        Filters the fields according to the `fields` query parameter.
        A blank `fields` parameter (?fields) will remove all fields. Not
        passing `fields` will pass all fields individual fields are comma
        separated (?fields=id,name,url,email).
        """
        fields = super(DynamicReadSerializerMixin, self).fields

        if not hasattr(self, "_context") or self.disable_dynamic_read:
            # We are being called before a request cycle or dynamic read was disabled
            return fields

        existing, current_depth = set(fields.keys()), getattr(self, "depth", 0)

        # apply field filtering only if fields query param is provided
        filter_fields = map(itemgetter(current_depth), self.dynamic_filter_fields)

        # apply omit filtering only if omit query param is provided
        omit_fields = [
            omit_field[current_depth]
            for omit_field in self.dynamic_omit_fields
            if len(omit_field) == current_depth + 1
        ]

        allowed, excluded = set(filter(None, filter_fields)) or existing
        excluded = set(filter(None, omit_fields))

        # Final list of fields that are in allowed and not in excluded
        final_list = (existing & allowed) - excluded

        # Generate new fields dict
        fields = dict(zip(final_list, itemgetter(*final_list)(fields)))
        return fields

    def extract_serializer_from_child(self, child):
        """Child object can be a ListSerializer, PresentablePrimaryKeyRelatedField, etc. Use this to define serializer
        object extraction from child object. This method must return a DynamicReadSerializerMixin object. Or exit raising
        ChildNotSupported exception."""
        if isinstance(child, DynamicReadSerializerMixin):
            return child

        if isinstance(child, ListSerializer) and isinstance(
            child.child, DynamicReadSerializerMixin
        ):
            return child.child

        # Apply any additional child extraction logic here
        raise ChildNotSupported(child)

    def process_fields_for_dynamic_read(self):
        if not (self.dynamic_filter_fields or self.dynamic_omit_fields):
            self.disable_dynamic_read = True
            return

        # current_depth
        current_depth = getattr(self, "depth", 0)
        next_depth, fields = current_depth + 1, self.fields

        def extend_child(list_getter):
            next_fields_to_update = groupby(
                list_getter(self), key=itemgetter(current_depth)
            )
            for field, next_filter_fields in next_fields_to_update:
                with suppress(ChildNotSupported, KeyError):
                    field = self.extract_serializer_from_child(fields[field])

                    # set the child depth
                    setattr(field, "depth", next_depth)
                    list_getter(field).extend(next_filter_fields)

        extend_child(attrgetter("dynamic_filter_fields"))
        extend_child(attrgetter("dynamic_omit_fields"))

    def to_representation(self, instance):
        # inherit self.disable_dynamic_read from immediate parent
        # parent is populated after bind, cannot reproduce this in __init__
        self.disable_dynamic_read = self.disable_dynamic_read or getattr(
            self.parent,
            "disable_dynamic_read",
            False,
        )

        # check if dynamic read is disabled
        if not self.disable_dynamic_read:
            self.process_fields_for_dynamic_read()
        return super(DynamicReadSerializerMixin, self).to_representation(instance)
