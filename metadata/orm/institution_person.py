#!/usr/bin/python
"""
Connects a User with an Institution
"""
from peewee import ForeignKeyField, Expression, OP, CompositeKey
from metadata.orm.users import Users
from metadata.orm.institutions import Institutions
from metadata.orm.base import DB, PacificaModel

class InstitutionPerson(PacificaModel):
    """
    Relates persons and institution objects.
    """
    user = ForeignKeyField(Users, related_name='institutions')
    institution = ForeignKeyField(Institutions, related_name='users')

    # pylint: disable=too-few-public-methods
    class Meta(object):
        """
        PeeWee meta class contains the database and the primary key.
        """
        database = DB
        primary_key = CompositeKey('user', 'institution')
    # pylint: enable=too-few-public-methods

    def to_hash(self):
        """
        Converts the object to a hash
        """
        obj = super(InstitutionPerson, self).to_hash()
        obj['person_id'] = int(self.user.person_id)
        obj['institution_id'] = int(self.institution.institution_id)
        return obj

    def from_hash(self, obj):
        """
        Converts the hash into the object
        """
        super(InstitutionPerson, self).from_hash(obj)
        if 'person_id' in obj:
            self.user = Users.get(Users.person_id == obj['person_id'])
        if 'institution_id' in obj:
            self.institution = Institutions.get(
                Institutions.institution_id == obj['institution_id']
            )

    def where_clause(self, kwargs):
        """
        Where clause for the various elements.
        """
        where_clause = super(InstitutionPerson, self).where_clause(kwargs)
        if 'person_id' in kwargs:
            person = Users.get(Users.person_id == kwargs['person_id'])
            where_clause &= Expression(InstitutionPerson.user, OP.EQ, person)
        if 'institution_id' in kwargs:
            institution = Institutions.get(Institutions.institution_id == kwargs['institution_id'])
            where_clause &= Expression(InstitutionPerson.institution, OP.EQ, institution)
        return where_clause
