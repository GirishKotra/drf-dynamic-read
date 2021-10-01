drf-dynamic-read
===================================================
A utility to improve and optimise read operations(querying and serialization of data) for Django Rest Framework based applications


Official version support:

- Django >=1.11
- Supported REST Framework versions >= 3.6.4
- Python >= 3.6

Capabilities
------------

- Gives the ability to dynamically select required fields to be serialized

    - We can specify required fields to be serialized for a GET request via query params
    - This also reduces response size comparatively as we pick only necessary fields
    - Ability to pick required fields through all kinds of nested relationships(many2one, many2many, reverse_lookups)

- Improves querying and reduces overall I/O load by a very good factor

    - reduces overall number of queries required to serve a generic GET Request by a `rest_framework.viewsets.ModelViewSet`

- Plug and Play

    - Simple API with minimal configurations


What it provides
----------------
This package provides following mixins:

- ``DynamicReadSerializerMixin``

    - provides an API on top of ``ModelSerializer`` to provide required fields to be serialized(via kwargs)
    - following kwargs can be passed to a model serializer inheriting this mixin

            - ``filter_fields`` : list of serializer field names which should be allowed for serialization
            - ``omit_fields`` : list of serializer field names which should not be allowed for serialization
    - ``DynamicReadSerializerMixin.optimize_queryset`` : a utility to return a optimized queryset by performing necessary select_related and prefetch_related based on ``fields`` and ``omit``, below are the arguments to be passed

            - ``filter_fields`` : list of serializer field names which should be allowed for serialization
            - ``omit_fields`` : list of serializer field names which should not be allowed for serialization
            - ``queryset`` : input queryset object


- ``DynamicReadViewMixin``

    - provides support on top of `rest_framework.viewsets.ModelViewSet` to pick required fields to be serialized via query params of a GET request, these required fields are internally forwarded to ``DynamicReadSerializerMixin``
    - ``optimize_queryset`` : static boolean attribute which decides whether to perform queryset optimization steps via ``DynamicReadSerializerMixin.optimize_queryset``
    - following query params can be passed for any GET request which is served by a model viewset inheriting this mixin:

        - ``fields`` : serializer field names as comma seperated values which should be considered for serialization
        - ``omit`` : serializer field names as comma seperated values which should not be considered for serialization


Installing
----------

    yet to be registered on pypi, copy source files until then, :D


Usage
------------
Example Entity Relationship:

.. sourcecode:: python

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

.. sourcecode:: python

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
            model = Event
            fields = "__all__"

Example views for above ER:

.. sourcecode:: python

    from dynamic_read.views import DynamicReadBaseViewMixin
    from rest_framework import viewsets
    from rest_framework.routers import DefaultRouter

    class EventModelViewSet(viewsets.ModelViewSet, DynamicReadBaseViewMixin):
        queryset = Event.objects.all()
        serializer_class = EventSerializer


    router = DefaultRouter()
    router.register("/api/event_basic/", EventModelViewSet)


A regular request returns all fields:

``GET /api/event_basic/``

Response:

.. sourcecode:: json

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
        "created_by": {
          "id": 2,
          "username": "user2"
        }
      },
    ]


A `GET` request with the `fields` parameter returns only a subset of
the fields:

``GET /api/event_basic/?fields=id,type``

Response:

.. sourcecode:: json

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

``GET /api/event_basic/?fields=id,type__name,cause__name,created_by__username``

Response:

.. sourcecode:: json

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
        "created_by": {
          "username": "user2"
        }
      },
    ]


A `GET` request with the `omit` parameter excludes specified fields(can also spawn through relationships just like the above example for `fields`).

``GET /api/event_basic/?omit=type,cause__created_by,created_by__id``

Response:

.. sourcecode:: json

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
        "created_by": {
          "username": "user2"
        }
      },
    ]

All the above examples work in the same mechanism for detail routes

Query Optimization
------------------

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

.. sourcecode:: python

    from dynamic_read.views import DynamicReadViewMixin
    from rest_framework import viewsets
    from rest_framework.routers import DefaultRouter

    class EventModelViewSet(DynamicReadViewMixin, viewsets.ModelViewSet):
        queryset = Event.objects.all()
        serializer_class = EventSerializer


    class EventOptimizedModelViewSet(DynamicReadViewMixin, viewsets.ModelViewSet)
        optimize_queryset = True
        queryset = Event.objects.all()
        serializer_class = EventSerializer

    router = DefaultRouter()
    router.register("/api/event_basic/", EventModelViewSet)
    router.register("/api/event_enhanced/", EventOptimizedModelViewSet)

Now let's try the optimized version: ``GET /api/event_enhanced/``

Total number of queries would be: 3

- ``.select_related("type", "owner__created_by")``

    - 1 (Query which gets all events inner joined with event types(inner joined with users), users)

- ``.prefetch_related("causes__created_by")``

    - 1 (Query to get all required event causes separately)
    - 1 (Query to get all users(created_by) for event causes)


Now first let's consider the above example with ``fields``: ``GET /api/event_enhanced/?fields=type__name,owner__created_by``

Total number of queries would be: 1

- ``.select_related("type", "owner__created_by")``

    - 1 (Query which gets all events inner joined with event types, users)


Testing
-------

Yet to write :)


Planned features
----------------

- API aliasing, single view serving extended url patterns, each url pattern is an alias mapped to specific fields,omit values
- Restricting the scope of fields,omit w.r.t user defined permissions per API


Credits
-------

- This implementation is inspired from `drf-dynamic-fields` by ``dbrgn``
- Thanks to Rishab Jain for implementing caching in evaluation of ``select_related``, ``prefetch_related`` for a ``QuerySet`` w.r.t fields, omit
- Thanks to Martin Garrix for his amazing music, sourcing all the necessary dopamine


License
-------

MIT license, see ``LICENSE`` file.
