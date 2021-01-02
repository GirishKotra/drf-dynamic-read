drf-dynamic-read
===================================================
A utility to improve and optimise read operations for Django Rest Framework based applications


Official version support:

- Django 1.11, 2.0, 2.1
- Supported REST Framework versions: 3.8, 3.9
- Python 3.4+

What it does
-----

- Gives the ability to dynamically select required fields to be serialized for a model serializer
    - This rules out the requirement of defining multiple serializers and views for a single model, thereby eliminating lots of boilerplate code
    - We can specify required fields to be serialized for a GET request via query params
    - Using a single ModelViewSet and ModelSerializer for a model, we can serve GET requests for different kinds of scenario
    - This also reduces response size comparatively as we pick only required fields in different scenarios
- Improves querying and reduces overall I/O load by a very good factor
    - reduces overall number of queries required to serve a generic GET Request by a `rest_framework.viewsets.ModelViewSet`


What it provides
-----
This package provides following mixins:
- `DynamicReadSerializerMixin` provides an API on top of `ModelSerializer` to provide required fields to be serialized(via args)
    - following arguments can be passed to a model serializer inheriting this mixin:
        - `dynamic_filter_fields` : list of serializer field names which should be allowed for serialization 
        - `dynamic_omit_fields` : list of serializer field names which should not be allowed for serialization
- `DynamicReadBaseViewMixin` provides support on top of `rest_framework.viewsets.ModelViewSet` to pick required fields to be serialized via query params of a GET request, these required fields then are internally forwarded to `DynamicReadSerializerMixin`
    - following query params can be passed in a GET request which is served by a model viewset inheriting this mixin:
        - `fields` : serializer field names provided as comma seperated values, which should be considered for serialization (will be forwarded to `dynamic_filter_fields`)
        - `omit` : serializer field names provided as comma seperated values, which should not be considered for serialization (will be forwarded to `dynamic_omit_fields`)
- `DynamicReadORMViewMixin` provides support on top of `DynamicReadBaseViewMixin` to optimize queryset by dynamically calculating necessary select_related and prefetch_related operations per request based on `fields` and `omit` query params which are explained above


Installing
----------

    yet to be registered on pypi, copy source files until then, :D

Important note:
-   Please invoke populate_dynamic_orm_cache from dynamic_orm after router is populated(in urls.py)

Example urls.py:

    from rest_framework.routers import DefaultRouter
    from dynamic_read.dynamic_orm import populate_dynamic_orm_cache

    router = DefaultRouter()
    router.register(..)
    router.register(..)
    router.register(..)

    populate_dynamic_orm_cache()




Usage
------------
Example Entity Relationship:

    from django.db import models

    class User(models.Model)
        username = models.CharField()


    class EventType(models.Model)
        name = models.CharField()
        created_by = models.ForeignKey(User)


    class EventCause(models.Model)
        name = models.CharField()
        created_by = models.ForeignKey(User)


    class Event(models.Model):
        type = models.ForeignKey(EventType)
        causes = models.ManyToManyField(EventCause)
        owner = models.OneToOneField(User)


Example serializers for above ER:

    from rest_framework import serializers
    from dynamic_read.serializers import DynamicReadSerializerMixin


    class UserSerializer(DynamicReadSerializerMixin, serializers.ModelSerializer):
        class Meta:
            model = models.User
            fields = "__all__"


    class EventTypeSerializer(DynamicReadSerializerMixin, serializers.ModelSerializer):
        created_by_id = serializers.PrimaryKeyRelatedField(
            queryset=EventType.objects.all(), write_only=True, source="created_by",
        )
        created_by = UserSerializer(read_only=True)

        class Meta:
            model = EventType
            fields = "__all__"


    class EventCauseSerializer(DynamicReadSerializerMixin, serializers.ModelSerializer):
        created_by_id = serializers.PrimaryKeyRelatedField(
            queryset=EventCause.objects.all(), write_only=True, source="created_by",
        )
        created_by = UserSerializer(read_only=True)

        class Meta:
            model = EventCause
            fields = "__all__"


    class EventSerializer(DynamicReadSerializerMixin, serializers.ModelSerializer):
        type_id = serializers.PrimaryKeyRelatedField(
            queryset=EventType.objects.all(), write_only=True, source="type",
        )
        cause_ids = serializers.PrimaryKeyRelatedField(
            queryset=EventCause.objects.all(), write_only=True, source="cause", many=True
        )
        type = EventTypeSerializer(read_only=True)
        causes = EventCauseSerializer(read_only=True, many=True)
        created_by = UserSerializer(read_only=True)

        class Meta:
            model = EventCause
            fields = "__all__"

Example views for above ER:

    from dynamic_read.views import DynamicReadBaseViewMixin
    from rest_framework import viewsets
    from rest_framework.routers import DefaultRouter

    class EventModelViewSet(viewsets.ModelViewSet, DynamicReadBaseViewMixin):
        queryset = Event.objects.all()
        serializer_class = EventSerializer


    router = DefaultRouter()
    router.register("/api/event_basic/")


A regular request returns all fields:

``GET /api/event_basic/``

Response::

    [
      {
        "id": 1,
        "type": {
          "id": 2,
          "name": "Type2",
          "created_by": {
            "id": 1,
            "username": "user1"
          }
        },
        "cause": [
          {
            "id": 1,
            "name": "Cause1",
            "created_by": {
              "id": 1,
              "username": "user1"
            }
          },
          {
            "id": 2,
            "name": "Cause2",
            "created_by": {
              "id": 2,
              "username": "user2"
            }
          }
        ],
        "owner": {
          "id": 2,
          "username": "user2"
        }
      },
      ...
    ]



A `GET` request with the `fields` parameter returns only a subset of
the fields:

``GET /api/event_basic/?fields=id,type``

Response:

    [
      {
        "id": 1,
        "type": {
          "id": 2,
          "name": "Type2",
          "created_by": {
            "id": 1,
            "username": "user1"
          }
        }
      },
      {
        "id": 2,
        "type": {
          "id": 1,
          "name": "Type1",
          "created_by": {
            "id": 1,
            "username": "user1"
          }
        }
      }
    ]

`fields` parameter can spawn through the relationships also:

``GET /api/event_basic/?fields=id,type__name,cause__name,owner__username``

Response:

    [
      {
        "id": 1,
        "type": {
          "name": "Type2"
        },
        "cause": [
          {
            "name": "Cause1"
          },
          {
            "name": "Cause2"
          }
        ],
        "owner": {
          "username": "user2"
        }
      },
      ...
    ]


A `GET` request with the `omit` parameter excludes specified fields(can also spawn through relationships just like the above example for `fields`).

``GET /api/event_basic/?omit=type,cause__created_by,owner__id``

Response:

    [
      {
        "id": 1,
        "cause": [
          {
            "id": 1,
            "name": "Cause1",
          },
          {
            "id": 2,
            "name": "Cause2",
          }
        ],
        "owner": {
          "username": "user2"
        }
      },
      ...
    ]


You can use both `fields` and `omit` in the same request!

``GET /api/event_basic/?fields=id,type&omit=type__created_by``

Response:

    [
      {
        "id": 1,
        "type": {
          "id": 2,
          "name": "Type2"1
        }
      },
      {
        "id": 2,
        "type": {
          "id": 1,
          "name": "Type1"
        }
      },
      ...
    ]


All the above examples apply the same way to detail routes also

Query Optimization
----------

Now first let's consider this general request which returns all the fields:
``GET /api/event_basic/``

Total number of queries would be: 51
-   1 (Base query to return all the event objects)
-   10 x 1 (fetch type for an event)
-   10 x 1 (fetch created_by for an each type)
-   10 x 1 (fetch all causes for an event)
-   10 x 1 (fetch created_by for an event cause)
-   10 x 1 (fetch owner for an event)


Now let's define a new view in views.py:

    from dynamic_read.views import DynamicReadBaseViewMixin, DynamicReadORMViewMixin
    from rest_framework import viewsets
    from rest_framework.routers import DefaultRouter

    class EventModelViewSet(viewsets.ModelViewSet, DynamicReadBaseViewMixin):
        queryset = Event.objects.all()
        serializer_class = EventSerializer


    class EventOptimizedModelViewSet(viewsets.ModelViewSet, DynamicReadORMViewMixin)
        queryset = Event.objects.all()
        serializer_class = EventSerializer

    router = DefaultRouter()
    router.register("/api/event_basic/")
    router.register("/api/event_enhanced/")

Now let's try the optimized version: ``GET /api/event_enhanced/``

Total number of queries would be: 3
-   `.select_related("type", "owner__created_by")`
    - 1 (Query which gets all events inner joined with event types(inner joined with users), users) 
-   `.prefetch_related("causes__created_by")`
    - 1 (Query to get all required event causes separately)
    - 1 (Query to get all users(created_by) for event causes)


Now first let's consider the above example with `fields`:
``GET /api/event_enhanced/?fields=type__name,owner__created_by``

Total number of queries would be: 1
-   `.select_related("type", "owner__created_by")`
    - 1 (Query which gets all events inner joined with event types(inner joined with users), users) 


Testing
-------

Yet to be written :(


Credits
-------

- This implementation is inspired from `drf-dynamic-fields`
  <https://github.com/dbrgn/drf-dynamic-fields>. Thanks to
  ``dbrgn``
- Thanks to Rishab Jain for implementing caching in the process of evaluating required fields to be used in `select_related, prefetch_related`
- Thanks to Martin Garrix for his amazing music which brings in all the required dopamine


License
-------

MIT license, see ``LICENSE`` file.
