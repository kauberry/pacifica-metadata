#!/usr/bin/python
"""
Pacifica Metadata ORM Base Class

This class implements the basic functionality needed for all
metadata objects in the metadata model for Pacifica.
"""
from os import getenv
from json import dumps, loads

from peewee import PostgresqlDatabase as pgdb
from peewee import Model, Expression, OP, PrimaryKeyField, fn, CompositeKey

from metadata.orm.utils import index_hash, ExtendDateTimeField
from metadata.orm.utils import datetime_converts, date_converts, datetime_now_nomicrosecond

# Primary PeeWee database connection object constant
DB = pgdb(getenv('POSTGRES_ENV_POSTGRES_DB', 'pacifica_metadata'),
          user=getenv('POSTGRES_ENV_POSTGRES_USER', 'pacifica'),
          password=getenv('POSTGRES_ENV_POSTGRES_PASSWORD', 'pacifica'),
          host=getenv('POSTGRES_PORT_5432_TCP_ADDR', 'localhost'),
          port=int(getenv('POSTGRES_PORT_5432_TCP_PORT', 5432)))

DEFAULT_ELASTIC_ENDPOINT = getenv('ELASTICDB_PORT', 'tcp://127.0.0.1:9200').replace('tcp', 'http')
ELASTIC_ENDPOINT = getenv('ELASTIC_ENDPOINT', DEFAULT_ELASTIC_ENDPOINT)

"""
PacificaModel

Base class inherits from the PeeWee ORM Model class to create
required fields by all objects and serialization methods for
the base fields.

There are also CherryPy methods for creating, updating, getting
and deleting these objects in from a web service layer.
"""


class PacificaModel(Model):
    """
    Basic fields for an object within the model

    Attributes:
        +-------------------+-------------------------------------+
        | Name              | Description                         |
        +===================+=====================================+
        | created           | When was the object created         |
        +-------------------+-------------------------------------+
        | updated           | When was the object last changed    |
        +-------------------+-------------------------------------+
        | deleted           | When was the object deleted         |
        +-------------------+-------------------------------------+
    """
    # this is peewee specific need to disable this check
    # pylint: disable=invalid-name
    id = PrimaryKeyField()
    # pylint: enable=invalid-name
    created = ExtendDateTimeField(default=datetime_now_nomicrosecond)
    updated = ExtendDateTimeField(default=datetime_now_nomicrosecond)
    deleted = ExtendDateTimeField(null=True)

    # pylint: disable=too-few-public-methods
    class Meta(object):
        """
        PeeWee meta class contains the db connection.
        """
        database = DB
        only_save_dirty = True
    # pylint: enable=too-few-public-methods

    def rollback(self):
        """
        Reconnect to the database on errors.
        """
        self._meta.database.rollback()

    def to_hash(self):
        """
        Converts the base object fields into serializable attributes
        in a hash.
        """
        obj = {}
        obj['created'] = self.created.isoformat()
        obj['updated'] = self.updated.isoformat()
        obj['deleted'] = self.deleted.isoformat() if self.deleted is not None else None
        obj['_id'] = index_hash(obj['created'], obj['updated'], obj['deleted'])
        return obj

    def _set_date_part(self, date_part, obj):
        if date_part in obj:
            setattr(self, date_part, date_converts(obj[date_part]))

    def _set_datetime_part(self, time_part, obj):
        """
        do more consistent type checking
        """
        if time_part in obj:
            setattr(self, time_part, datetime_converts(obj[time_part]))

    def from_hash(self, obj):
        """
        Converts the hash objects into object fields if they are
        present.
        """
        self._set_datetime_part('created', obj)
        self._set_datetime_part('updated', obj)
        self._set_datetime_part('deleted', obj)

    def from_json(self, json_str):
        """
        Converts the json string into the current object.
        """
        if not isinstance(loads(json_str), dict):
            raise ValueError('json_str not dict')
        self.from_hash(loads(json_str))

    def to_json(self):
        """
        Converts the object into a json object.
        """
        return dumps(self.to_hash())

    def where_clause(self, kwargs):
        """
        PeeWee specific extension meant to be passed to a PeeWee get
        or select.
        """
        my_class = self.__class__
        where_clause = Expression(1, OP.EQ, 1)
        if 'deleted' in kwargs:
            if kwargs['deleted'] is None:
                where_clause &= Expression(getattr(my_class, 'deleted'), OP.IS, None)
            else:
                date_obj = datetime_converts(kwargs['deleted'])
                where_clause &= Expression(getattr(my_class, 'deleted'), OP.EQ, date_obj)
        for date in ['updated', 'created']:
            if date in kwargs:
                date_obj = datetime_converts(kwargs[date])
                where_clause &= Expression(getattr(my_class, date), OP.EQ, date_obj)
        return where_clause

    @classmethod
    def last_change_date(cls):
        """
        Find the last changed date for the object
        """
        return cls.select(fn.Max(cls.updated)).scalar()

    @classmethod
    def available_hash_list(cls):
        """
        Need to figure out more about what this does...
        """
        hash_list = []
        hash_dict = {}
        all_keys_query = cls.select(*[getattr(cls, key) for key in cls.get_primary_keys()]).dicts()
        for obj in all_keys_query.execute():
            inst_key = index_hash(*obj.values())
            hash_list.append(inst_key)
            entry = {
                'key_list': obj,
                'index_hash': inst_key
            }
            hash_dict[inst_key] = entry
        return hash_list, hash_dict

    @classmethod
    def get_primary_keys(cls):
        """
        Return the primary keys for the object
        """
        # pylint: disable=no-member
        primary_key = cls._meta.primary_key
        if isinstance(primary_key, CompositeKey) and len(cls._meta.rel) > 0:
            return list(primary_key.field_names)
            # pylint: enable=no-member
        else:
            return [primary_key.name]
