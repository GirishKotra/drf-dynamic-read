from rest_framework.serializers import ListSerializer


class ChildNotSupported(Exception):
    """Represents a child object cannot be used with dynamic drf"""

    def __init__(self, child):
        self.child = child

    def __str__(self):
        return f"ChildNotSupported: {self.child}"


class DynamicReadSerializerMixin(object):
    """
    A serializer mixin that takes an additional `fields` argument that controls
    which fields should be displayed.
    """

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
            [each.split("__") for each in dynamic_filter_fields]
            if dynamic_filter_fields
            else []
        )

        self.dynamic_omit_fields = (
            [each.split("__") for each in dynamic_omit_fields]
            if dynamic_omit_fields
            else []
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

        # Drop any fields that are not specified in the `fields` argument.
        existing = set(fields.keys())

        # current_depth
        current_depth = getattr(self, "depth", 0)

        # apply field filtering only if fields query param is provided
        filter_fields = [
            filter_field[current_depth] for filter_field in self.dynamic_filter_fields
        ]

        # apply omit filtering only if omit query param is provided
        omit_fields = [
            omit_field[current_depth]
            for omit_field in self.dynamic_omit_fields
            if len(omit_field) == current_depth + 1
        ]

        allowed = set([_f for _f in filter_fields if _f]) or existing

        excluded = set([_f for _f in omit_fields if _f])

        # filtering fields keeping existing fields as source in order to avoid invalid query param values
        for field in existing:
            if field not in allowed or (field in excluded):
                fields.pop(field, None)

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
        # current_depth
        current_depth = getattr(self, "depth", 0)

        if not (self.dynamic_filter_fields or self.dynamic_omit_fields):
            self.disable_dynamic_read = True
            return

        for child_field_name, child_field in self.fields.items():
            # process nested_relationships only if there are any filter_fields/omit_fields set
            # --> many_to_many/one_to_many(reverse_lookup): observed as list_serializer(ModelSerializer with many=True)
            # --> many_to_one/one_to_one relationship: observed as ModelSerializer
            try:
                field = self.extract_serializer_from_child(child_field)

                # set the child depth
                setattr(field, "depth", current_depth + 1)

                # check for matches w.r.t current_depth
                if self.dynamic_filter_fields:
                    for filter_field in self.dynamic_filter_fields:
                        if child_field_name == filter_field[
                            current_depth
                        ] and current_depth + 1 < len(filter_field):
                            field.dynamic_filter_fields.append(filter_field)

                if self.dynamic_omit_fields:
                    for omit_field in self.dynamic_omit_fields:
                        if child_field_name == omit_field[current_depth]:
                            field.dynamic_omit_fields.append(omit_field)
            except ChildNotSupported:
                # Skip if child not supported
                pass

    def to_representation(self, instance):
        # inherit self.disable_dynamic_read from immediate parent
        # parent is populated after bind, cannot reproduce this in __init__
        self.disable_dynamic_read = self.disable_dynamic_read or getattr(
            self.parent, "disable_dynamic_read", False,
        )

        # check if dynamic read is disabled
        if not self.disable_dynamic_read:
            self.process_fields_for_dynamic_read()
        return super(DynamicReadSerializerMixin, self).to_representation(instance)
