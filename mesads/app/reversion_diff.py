"""django-reversion provides a hook to setup a callback when a model is saved to
store the history of changes in the database.

django-reversion-compare is another package which offers a view in the
administration to compare two versions of a model. It also includes low-level
functions to compare two versions of a model, but it doesn't provide a way to
get the full history of a model.

This file provides a class ModelHistory which takes a model instance as input,
and returns a list of ModelHistoryRevision objects. Each ModelHistoryRevision
contains all the changes for a given revision, for the object and all the models
that have a foreign key to this object.
"""

from collections import defaultdict
import functools
import json

import dateparser

from django.contrib.postgres.fields import JSONField
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models.functions import Cast
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from reversion.models import Version


class Diff:
    """Computes the differences between the dict `obj` and its previous version.
    `prev` can be None.

    If `prev` is None, then `is_new_object` is True, and `new_fields` contains
    all the fields of `obj`.

    If `prev` is not None, then `is_new_object` is False, and `changed_fields`
    contains all the fields that have changed.
    """

    def __init__(self, model, render_field, data, prev_data, ignore_fields):
        self.model = model
        self.render_field = render_field
        self.model_name = model._meta.model_name
        self.data = data
        self.prev_data = prev_data
        self.ignore_fields = ignore_fields
        self.changed_fields = {}
        self.new_fields = {}
        self.is_new_object = not prev_data

        if not self.is_new_object:
            self._diff()
        else:
            self.new_fields = self._exclude_ignored_fields(
                {
                    self._resolve_field(key): self.render_field(self.model, key, value)
                    for key, value in data.items()
                    if self._resolve_field(key) and (value or value is False)
                }
            )

    def __repr__(self):
        if self.is_new_object:
            return f"<Diff is_new_object={self.new_fields}>"

        changed = ",".join(str(v) for v in self.changed_fields.keys())
        ret = "<Diff"
        if changed:
            ret += f" changed={changed}"
        return ret + ">"

    def _exclude_ignored_fields(self, data):
        return {
            key: value for key, value in data.items() if key not in self.ignore_fields
        }

    @functools.cache
    def _resolve_field(self, name):
        try:
            return self.model._meta.get_field(name)
        except FieldDoesNotExist:
            return None

    def _diff(self):
        common_keys = set(self.data.keys()).intersection(set(self.prev_data.keys()))

        for key in common_keys:
            if self.data[key] != self.prev_data[key]:
                field = self._resolve_field(key)
                if not field:
                    continue

                self.changed_fields[field] = (
                    self.render_field(self.model, key, self.prev_data[key]),
                    self.render_field(self.model, key, self.data[key]),
                )

        self.changed_fields = self._exclude_ignored_fields(self.changed_fields)


class ModelHistory:
    def __init__(self, instance, ignore_fields=None):
        self.instance = instance
        self.ignore_fields = ignore_fields or []

    def _foreign_key_referring_model(self, model):
        """For a given model, returns all the models that have a foreign key to this
        model, and the name of the foreign key field.

        For example:

        >>> class Parent(models.Model):
        ...    pass

        >>> class Child(models.Model):
        ...    parent = models.ForeignKey(Parent)

        >>> Class Child2(models.Model):
        ...    daddy = models.ForeignKey(Parent)

        >>> foreign_key_referring_model(Parent)
        [(Child, 'parent'), (Child2, 'daddy')]
        """
        referring_models = []
        for related_object in model._meta.related_objects:
            referring_models.append(
                (related_object.related_model, related_object.field.name)
            )
        return referring_models

    def _build_revisions_list(self, obj):
        """To get the full history of a model, we need to get all the versions for
        this model, and all the versions for models that have a foreign key to this
        model.

        This function returns a list of tuples, where each tuple has the following format:

        >>> (revision, {Model: {object_id: version, object_id: version}})

        The first element of the tuple is the revision object.

        The second element is a dict:
            * the top-level keys are the models that have a change in this revision.
            * the second-level keys are the object ids of the objects that have a change in this revision.
            * the values are the version objects for this object id.

        The list is sorted to have the most recent revision first.
        """
        revisions = defaultdict(lambda: defaultdict(dict))

        # List all the versions for this object
        for version in Version.objects.get_for_object(obj).select_related(
            "revision__user"
        ):
            revisions[version.revision][obj._meta.model].update({obj.id: version})

        # List all the versions the models that have a foreign key to this object
        for model, pk_name in self._foreign_key_referring_model(obj._meta.model):
            # This query filters all the versions for models that have a foreign key to `obj`.
            # django-reversion stores the serialized data in a text field. We need to cast it to JSON to filter it.
            # Also, the serialized data is a list of dictionaries. It seems there is
            # always only one dictionary in the list, so we don't need to iterate over it and can just use the first.
            qs = (
                Version.objects.get_for_model(model)
                .select_related("revision")
                .annotate(json_data=Cast("serialized_data", JSONField()))
                .filter(**{f"json_data__0__fields__{pk_name}": obj.id})
            )
            for row in qs:
                revisions[row.revision][model].update(
                    {
                        int(row.object_id): row,
                    }
                )
        # Convert defaultdict to dict, and sort the revisions with the most recent first
        return sorted(
            [(key, dict(value)) for key, value in revisions.items()],
            key=lambda x: x[0].id,
            reverse=True,
        )

    def _find_first_version_from_revisions_list(self, revisions, search_cls, search_id):
        """Given a list of revisions returned by `_build_revisions_list`, this
        function returns the first version of the object with the given id and
        class."""
        for _, objects in revisions:
            for cls, objects_ids in objects.items():
                if cls == search_cls and search_id in objects_ids:
                    return objects_ids[search_id]
        return None

    def _set_diff_in_revisions_list(self, revisions):
        """Given the list of revisions returned by `_build_revisions_list`, this
        function replaces every version object with a dict containing the
        differences with the previous version.
        """
        for idx, (_, objects) in enumerate(revisions):
            for cls, objects_ids in objects.items():
                for object_id, version in objects_ids.items():
                    last_version = self._find_first_version_from_revisions_list(
                        revisions[idx + 1 :], cls, object_id
                    )
                    diff = Diff(
                        model=cls,
                        render_field=self.render_field,
                        data=json.loads(version.serialized_data)[0]["fields"],
                        prev_data=json.loads(last_version.serialized_data)[0]["fields"]
                        if last_version
                        else None,
                        ignore_fields=self.ignore_fields,
                    )
                    objects_ids[object_id] = diff
        return revisions

    def _remove_empty_revisions(self, revisions):
        """Given the revisions returned by _set_diff_in_revisions_list, this
        function removes entries where there are no changes. It can happen when
        the only fields updated for a revision are ignored fields."""
        new_revisions = []
        for revision, objects in revisions:
            new_objects = {}
            for cls, objects_ids in objects.items():
                new_objects_ids = {}
                for object_id, diff in objects_ids.items():
                    if any((diff.new_fields, diff.changed_fields)):
                        new_objects_ids[object_id] = diff
                if new_objects_ids:
                    new_objects[cls] = new_objects_ids
            if new_objects:
                new_revisions.append((revision, new_objects))
        return new_revisions

    def get_revisions(self):
        revisions = self._build_revisions_list(self.instance)
        revisions = self._set_diff_in_revisions_list(revisions)
        return self._remove_empty_revisions(revisions)

    def render_field(self, cls, name, value):
        """This function can be overridden to customize the way a field is rendered."""
        if value is None:
            return ""

        if isinstance(value, bool):
            return _("Yes") if value else _("No")

        field = cls._meta.get_field(name)

        if field.choices:
            return next(
                (
                    human_readable
                    for value, human_readable in field.choices
                    if value == value
                ),
                None,
            )

        if isinstance(field, models.DateTimeField):
            return dateparser.parse(value)

        if isinstance(field, models.DateField):
            return dateparser.parse(value).date()

        if isinstance(field, models.FileField):
            maxsize = 64
            url = field.storage.url(value)
            name = f"…{value[-maxsize:]}" if len(value) > maxsize + 3 else value
            return mark_safe(f'<a href="{url}" target="_blank">{name}</a>')

        return value
