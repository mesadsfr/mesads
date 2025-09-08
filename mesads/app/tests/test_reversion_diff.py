import datetime

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils.translation import gettext as _

import reversion
from reversion.models import Revision

from mesads.fradm.models import Commune
from mesads.users.models import User

from ..models import ADS, ADSUser, ADSManager, ADSLegalFile, ADSManagerAdministrator
from ...fradm.models import Prefecture
from ..reversion_diff import ModelHistory, Diff


class TestReversionDiff(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@test.com")
        self.commune = Commune.objects.create(
            type_commune="COM", libelle="Melesse", insee="35173", departement="35"
        )
        prefecture = Prefecture.objects.create(numero="35", libelle="Ille-et-Vilaine")
        administrator = ADSManagerAdministrator.objects.create(prefecture=prefecture)
        self.ads_manager = ADSManager.objects.create(
            content_type=ContentType.objects.get_for_model(self.commune),
            object_id=self.commune.id,
            administrator=administrator,
        )
        self.ads = ADS.objects.create(
            number=1, ads_manager=self.ads_manager, ads_in_use=True
        )
        self.ads2 = ADS.objects.create(
            number=2, ads_manager=self.ads_manager, ads_in_use=True
        )

    def test_no_revision(self):
        revisions = ModelHistory(self.ads).get_revisions()
        self.assertEqual(revisions, [])

    def test_revision_diff(self):
        with reversion.create_revision():
            self.ads.owner_email = "myemail@domain.com"
            self.ads.save()

            ads_user = ADSUser.objects.create(ads=self.ads, name="Luke")
            ads_user.save()

            # Create another object, unrelated, to check that it is not included in the diff
            self.ads2.owner_email = "whatever@domain.com"
            self.ads2.save()

        with reversion.create_revision():
            self.ads.owner_email = "newemail@domain.com"
            self.ads.owner_name = "My name"
            self.ads.save()

            ads_user.name = "Martin"
            ads_user.save()

            self.ads2.owner_name = "Jean-Luc"
            self.ads2.save()

        revisions = ModelHistory(self.ads).get_revisions()

        self.assertEqual(len(revisions), 2)

        # -> Check the oldest revision
        revision, revision_models = revisions[1]
        self.assertIsInstance(revision, Revision)
        self.assertEqual(len(revision_models), 2)
        self.assertIn(ADS, revision_models)
        self.assertIn(ADSUser, revision_models)

        # Check ADS
        objects = revision_models[ADS]
        self.assertEqual(len(objects), 1)
        self.assertIn(self.ads.id, objects)

        diff = objects[self.ads.id]
        self.assertIsInstance(diff, Diff)
        self.assertIsInstance(str(diff), str)

        self.assertTrue(diff.is_new_object)

        self.assertIn(ADS._meta.get_field("owner_email"), diff.new_fields)
        self.assertEqual(
            diff.new_fields[ADS._meta.get_field("owner_email")],
            "myemail@domain.com",
        )

        # Check ADSUser
        objects = revision_models[ADSUser]
        self.assertEqual(len(objects), 1)
        self.assertIn(ads_user.id, objects)

        diff = objects[ads_user.id]
        self.assertIsInstance(diff, Diff)
        self.assertIsInstance(str(diff), str)

        self.assertTrue(diff.is_new_object)

        self.assertIn(ADSUser._meta.get_field("name"), diff.new_fields)
        self.assertEqual(
            diff.new_fields[ADSUser._meta.get_field("name")],
            "Luke",
        )

        # -> Check the newest revision
        revision, revision_models = revisions[0]
        self.assertIsInstance(revision, Revision)
        self.assertEqual(len(revision_models), 2)
        self.assertIn(ADS, revision_models)

        # Check updates on the ADS
        objects = revision_models[ADS]
        self.assertEqual(len(objects), 1)
        self.assertIn(self.ads.id, objects)

        diff = objects[self.ads.id]
        self.assertIsInstance(diff, Diff)
        self.assertIsInstance(str(diff), str)

        self.assertFalse(diff.is_new_object)

        self.assertIn(ADS._meta.get_field("owner_email"), diff.changed_fields)
        self.assertEqual(
            diff.changed_fields[ADS._meta.get_field("owner_email")],
            ("myemail@domain.com", "newemail@domain.com"),
        )
        self.assertIn(ADS._meta.get_field("owner_name"), diff.changed_fields)
        self.assertEqual(
            diff.changed_fields[ADS._meta.get_field("owner_name")],
            ("", "My name"),
        )

        # Check updates on the ADSUser
        objects = revision_models[ADSUser]
        self.assertEqual(len(objects), 1)
        self.assertIn(ads_user.id, objects)

        diff = objects[ads_user.id]
        self.assertIsInstance(diff, Diff)
        self.assertIsInstance(str(diff), str)

        self.assertFalse(diff.is_new_object)

        self.assertIn(ADSUser._meta.get_field("name"), diff.changed_fields)
        self.assertEqual(
            diff.changed_fields[ADSUser._meta.get_field("name")],
            ("Luke", "Martin"),
        )

    def test_render_fields(self):
        self.assertEqual(ModelHistory(ADS()).render_field(ADS, "owner_email", None), "")
        self.assertEqual(ModelHistory(ADS()).render_field(ADS, "owner_email", ""), "")
        self.assertEqual(
            ModelHistory(ADS()).render_field(ADS, "owner_email", "test@test.com"),
            "test@test.com",
        )

        self.assertEqual(
            ModelHistory(ADS()).render_field(ADS, "used_by_owner", True),
            _("Yes"),
        )
        self.assertEqual(
            ModelHistory(ADS()).render_field(ADS, "used_by_owner", False),
            _("No"),
        )

        self.assertEqual(
            ModelHistory(ADSUser()).render_field(
                ADSUser, "status", "titulaire_exploitant"
            ),
            "Le titulaire de l'ADS (personne physique)",
        )

        self.assertEqual(
            ModelHistory(ADS()).render_field(ADS, "ads_creation_date", "2012-12-21"),
            datetime.date(2012, 12, 21),
        )
        self.assertEqual(
            ModelHistory(ADSLegalFile()).render_field(
                ADSLegalFile, "deleted_at", "2023-06-02T16:16:48.112"
            ),
            datetime.datetime(2023, 6, 2, 16, 16, 48, 112000),
        )

        self.assertEqual(
            ModelHistory(ADSLegalFile()).render_field(ADSLegalFile, "file", "xxx"),
            '<a href="/uploads/xxx" target="_blank">xxx</a>',
        )

    def test_diff_removed_field(self):
        """When a field has been removed from the model but it is still
        referenced in the history, it should not be displayed."""
        # New object, because the old object is empty
        diff = Diff(
            ADS,
            lambda cls, name, value: value,
            {"number": "213", "removed_field": "whatever"},
            None,
            [],
        )
        self.assertEqual(
            diff.new_fields,
            {
                ADS._meta.get_field("number"): "213",
            },
        )

        # New revision of an existing object
        diff = Diff(
            ADS,
            lambda cls, name, value: value,
            {"number": "213", "removed_field": "new value"},
            {"number": "111", "removed_field": "old value"},
            [],
        )
        self.assertEqual(
            diff.changed_fields,
            {
                ADS._meta.get_field("number"): ("111", "213"),
            },
        )
