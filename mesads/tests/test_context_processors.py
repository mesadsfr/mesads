import pkg_resources
import re
import unittest

import yaml

from django.urls import URLPattern, URLResolver, get_resolver


EXCLUDE_MODULES = [
    r".*autocomplete.*",
    r"^(app.*|auth_.*|users_.*|fradm_.*|vehicules_relais_.*)_add$",
    r"^(app.*|auth_.*|users_.*|fradm_.*|vehicules_relais_.*)_change$",
    r"^(app.*|auth_.*|users_.*|fradm_.*|vehicules_relais_.*)_changelist$",
    r"^(app.*|auth_.*|users_.*|fradm_.*|vehicules_relais_.*)_compare$",
    r"^(app.*|auth_.*|users_.*|fradm_.*|vehicules_relais_.*)_delete$",
    r"^(app.*|auth_.*|users_.*|fradm_.*|vehicules_relais_.*)_history$",
    r"^(app.*|auth_.*|users_.*|fradm_.*|vehicules_relais_.*)_list$",
    r"^(app.*|auth_.*|users_.*|fradm_.*|vehicules_relais_.*)_recover$",
    r"^(app.*|auth_.*|users_.*|fradm_.*|vehicules_relais_.*)_recoverlist$",
    r"^(app.*|auth_.*|users_.*|fradm_.*|vehicules_relais_.*)_revision$",
    r"^ads-updates",
    r"^api",
    r"^authtoken",
    r"^django_cron",
    r"^history_refresh$",
    r"^history_sidebar$",
    r"^index$",
    r"^login",
    r"^logout",
    r"^markdownx.*",
    r"^render_panel$",
    r"^sql_.*$",
    r"^template_source$",
    r"jsi18n",
    r"view_on_site",
    r"admin-statistiques",
]


def list_modules_urls():
    def recurse(patterns, parents):
        urls = []
        for item in patterns:
            if isinstance(item, URLPattern) and item.name:
                for module in EXCLUDE_MODULES:
                    if re.match(module, item.name):
                        break
                else:
                    urls.append(item.name)
            elif isinstance(item, URLResolver):
                urls.extend(
                    recurse(item.url_patterns, parents=parents + [item.pattern])
                )
        return urls

    return recurse(get_resolver().url_patterns, parents=[])


class TestHTMLMetadata(unittest.TestCase):
    def test_yaml_file(self):
        """Make sure the keys in the YAML file cover all URLs."""
        data = pkg_resources.resource_string(__name__, "../html_metadata.yml")
        metadata = yaml.safe_load(data)
        metadata_views = list(metadata.get("urls", {}).keys())
        mesads_reverses = list_modules_urls()

        for name in mesads_reverses:
            self.assertIn(
                name,
                metadata_views,
                msg=f"The url {name} is in the code but the HTML title or description is missing in the YAML file html_metadata.yml",
            )
            if metadata["urls"][name].get("missing") is not True:
                self.assertIn("title", metadata["urls"][name])
                self.assertIn("description", metadata["urls"][name])

        # All the entries in the YAML file should relate to an existing URL
        all_urls = list_modules_urls()
        for name in metadata_views:
            self.assertIn(
                name,
                all_urls,
                msg=f"The url {name} is in html_metadata.yml but is related to a non-existing URL",
            )
