import pkg_resources
import unittest

import yaml

from django.urls import URLPattern, URLResolver, get_resolver


def list_modules_urls(*modules):
    """List all the reverse URLs with a target view in the given modules."""

    def recurse(patterns):
        urls = []
        for item in patterns:
            if isinstance(item, URLPattern) and item.name:
                for module in modules:
                    if item.callback.__module__.startswith(module):
                        urls.append(item.name)
            elif isinstance(item, URLResolver):
                urls.extend(recurse(item.url_patterns))
        return urls

    return recurse(get_resolver().url_patterns)


class TestHTMLMetadata(unittest.TestCase):
    def test_yaml_file(self):
        """Make sure the keys in the YAML file cover all URLs."""
        data = pkg_resources.resource_string(__name__, "html_metadata.yml")
        metadata = yaml.safe_load(data)
        metadata_views = list(metadata.get("urls", {}).keys())
        mesads_reverses = list_modules_urls("mesads.app", "mesads.vehicules_relais")

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
        all_urls = list_modules_urls("")
        for name in metadata_views:
            self.assertIn(
                name,
                all_urls,
                msg=f"The url {name} is in html_metadata.yml but is related to a non-existing URL",
            )
