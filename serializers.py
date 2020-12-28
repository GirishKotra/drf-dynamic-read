from rest_framework import serializers


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
            [each.split("__") for each in self.dynamic_filter_fields]
            if dynamic_filter_fields
            else None
        )

        self.dynamic_omit_fields = (
            [each.split("__") for each in self.dynamic_omit_fields]
            if dynamic_omit_fields
            else None
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

        filter_fields = getattr(self, "dynamic_filter_fields", [])
        omit_fields = getattr(self, "dynamic_omit_fields", [])

        # Drop any fields that are not specified in the `fields` argument.
        existing = set(fields.keys())

        # current_depth
        current_depth = getattr(self, "depth", 0)

        # apply field filtering only if fields query param is provided
        filter_fields = (
            [filter_field[current_depth] for filter_field in filter_fields]
            if filter_fields
            else []
        )

        # apply omit filtering only if omit query param is provided
        omit_fields = (
            [
                omit_field[current_depth]
                for omit_field in omit_fields
                if len(omit_field) == current_depth + 1
            ]
            if omit_fields
            else []
        )

        allowed = set([_f for _f in filter_fields if _f]) or existing

        excluded = set([_f for _f in omit_fields if _f])

        # patch to allow fk ids for reading if they are defined as write_only fields
        if filter_fields:
            for field in filter_fields:
                if (
                    field.endswith("_id")
                    and (field in fields)
                    and fields[field].write_only is True
                ):
                    fields[field].write_only = False

        for field in existing:
            if field not in allowed or (field in excluded):
                fields.pop(field, None)

        return fields

    def process_fields_for_dynamic_read(self):
        request = self.context.get("request", None)

        # check if current serializer is the root model serializer
        is_real_root = (self.root == self) or (
            self.parent == self.root and getattr(self.parent, "many", False)
        )

        # inherit self.disable_dynamic_read from immediate parent
        self.disable_dynamic_read = self.disable_dynamic_read or getattr(
            self.parent, "disable_dynamic_read", False,
        )

        # check if dynamic read is disabled
        if self.disable_dynamic_read:
            return

        # current_depth
        current_depth = getattr(self, "depth", 0)

        # extract query params from request
        query_params = getattr(request, "query_params", getattr(request, "GET", {}))

        # check if any filter_fields/omit_fields are explicitly set for this serializer
        # else grab it from request object if the current serializer is the root or it's parent is list root
        if (
            self.dynamic_filter_fields is None
            and ("fields" in query_params)
            and is_real_root
        ):
            self.dynamic_filter_fields = [
                each.split("__") for each in query_params.get("fields").split(",")
            ]
        if (
            self.dynamic_omit_fields is None
            and ("omit" in query_params)
            and is_real_root
        ):
            self.dynamic_omit_fields = [
                each.split("__") for each in query_params.get("omit").split(",")
            ]

        dynamic_filter_fields = getattr(self, "dynamic_filter_fields", None)
        dynamic_omit_fields = getattr(self, "dynamic_omit_fields", None)

        for child_field_name, child_field in self.fields.items():
            # process nested_relationships only if there are any filter_fields/omit_fields set
            # --> many_to_many/one_to_many(reverse_lookup): observed as list_serializer(ModelSerializer with many=True)
            # --> many_to_one/one_to_one relationship: observed as ModelSerializer
            if (self.dynamic_filter_fields or self.dynamic_omit_fields) and (
                isinstance(child_field, DynamicReadSerializerMixin)
                or (
                    isinstance(child_field, serializers.ListSerializer)
                    and isinstance(child_field.child, DynamicReadSerializerMixin)
                )
            ):
                field = (
                    child_field
                    if isinstance(child_field, DynamicReadSerializerMixin)
                    else child_field.child
                )
                # set the child depth
                setattr(field, "depth", current_depth + 1)

                # pre_set
                field.dynamic_filter_fields = field.dynamic_filter_fields or []
                field.dynamic_omit_fields = field.dynamic_omit_fields or []

                # check for matches w.r.t current_depth
                if dynamic_filter_fields:
                    for filter_field in dynamic_filter_fields:
                        if child_field_name == filter_field[
                            current_depth
                        ] and current_depth + 1 < len(filter_field):
                            field.dynamic_filter_fields.append(filter_field)
                if dynamic_omit_fields:
                    for omit_field in dynamic_omit_fields:
                        if child_field_name == omit_field[current_depth]:
                            field.dynamic_omit_fields.append(omit_field)

    def to_representation(self, instance):
        self.process_fields_for_dynamic_read()
        return super(DynamicReadSerializerMixin, self).to_representation(instance)
