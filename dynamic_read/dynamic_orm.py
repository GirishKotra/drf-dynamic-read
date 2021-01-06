from functools import lru_cache

from rest_framework.serializers import ListSerializer

from .serializers import DynamicReadSerializerMixin


@lru_cache(maxsize=2048)
def get_relational_fields(model):
    return {
        (hasattr(each, "get_accessor_name") and each.get_accessor_name())
        or each.name: each
        for each in model._meta.get_fields()
        if each.is_relation
    }


def get_final_fields(serializer, parent_accessor=""):
    final_select = []
    final_prefetch = []
    serializer = (
        serializer.child if isinstance(serializer, ListSerializer) else serializer
    )
    serializer.process_fields_for_dynamic_read()
    relational_fields = get_relational_fields(serializer.Meta.model)
    for field_name, field_obj in serializer.fields.items():
        field_name = (field_obj.source or field_name).split(".")[0]
        if field_name not in relational_fields:
            continue
        is_many = isinstance(field_obj, ListSerializer)
        field_obj = field_obj.child if is_many else field_obj
        if isinstance(field_obj, DynamicReadSerializerMixin):
            sub_select_related, sub_prefetch_related = get_final_fields(
                field_obj, parent_accessor=f"{parent_accessor}{field_name}__",
            )
            if sub_select_related:
                if not is_many:
                    final_select.extend(sub_select_related)
                else:
                    final_prefetch.extend(sub_select_related)
            elif not is_many:
                final_select.append(f"{parent_accessor}{field_name}")
            if sub_prefetch_related:
                final_prefetch.extend(sub_prefetch_related)
            elif is_many:
                final_prefetch.append(f"{parent_accessor}{field_name}")
    return final_select, final_prefetch


@lru_cache(maxsize=2048)
def get_all_select_prefetch(serializer_class):
    if not issubclass(serializer_class, DynamicReadSerializerMixin):
        raise TypeError(f"Serializer {serializer_class} must inherit DynamicReadSerializerMixin")

    return get_final_fields(serializer_class(disable_dynamic_read=True))


def populate_dynamic_orm_cache():
    """This method must be run after models are loaded. It caches the serializer fields into an lru cache
    for faster access during runtime."""
    for serializer_class in DynamicReadSerializerMixin.get_concrete_classes():
        get_all_select_prefetch(serializer_class)


@lru_cache(maxsize=2048)
def get_prefetch_select(serializer_class, request_fields=(), request_omit_fields=()):
    final_select, final_prefetch = [], []
    all_select, all_prefetch = get_all_select_prefetch(
        serializer_class,
    )  # fetch from cache
    if not request_fields and not request_omit_fields:
        return all_select, all_prefetch

    for field in request_fields:
        final_select.extend(
            (
                each
                for each in all_select
                if each.startswith(field) or field.startswith(each)
            )
        )
        final_prefetch.extend(
            (
                each
                for each in all_prefetch
                if each.startswith(field) or field.startswith(each)
            )
        )

    if request_omit_fields:
        if not final_select:
            final_select = all_select
        if not final_prefetch:
            final_prefetch = all_prefetch

        final_select = [
            each
            for each in final_select
            if not any(
                (
                    (each.startswith(field) or field.startswith(each))
                    for field in request_omit_fields
                )
            )
        ]

        final_prefetch = [
            each
            for each in final_prefetch
            if not any(
                (
                    (each.startswith(field) or field.startswith(each))
                    for field in request_omit_fields
                )
            )
        ]

    return final_select, final_prefetch
