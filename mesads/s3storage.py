import re

from storages.backends.s3boto3 import S3Boto3Storage


class HackishS3Boto3Storage(S3Boto3Storage):
    """By default, clever-cloud serves S3 files from the domain
    cellar-c2.services.clever-cloud.com. Unfortunately this domain is sometimes
    blacklisted by browsers that believe it is a phishing site.

    To avoid being blocked, we can serve the files from a custom domain. To do
    so, we need to:
    * name the bucket after the domain we want to use (s3.mesads.beta.gouv.fr)
    * create a CNAME record in the DNS zone of mesads.beta.gouv.fr that points
      to cellar-c2.services.clever-cloud.com

    Then, from Django, it should be in theory possible to use S3Boto3Storage and
    set the parameter custom_domain to the custom domain.

    Unfortunately, if we do so, models.FileField().url wil not generate signed
    URLs, so it will be impossible to access the files. This is likely due to
    this GitHub issue: https://github.com/jschneier/django-storages/issues/165 ;
    in short, signed URLs are disabled when a custom domain is used.

    As a workaround, we leave custom_domain empty, and use a custom backend that
    replaces `url` (that is signed) formed as
    https://cellar-c2.services.clever-cloud.com/s3.mesads.beta.gouv.fr/<filename>?AWSAccessKeyId=...&Signature=...&Expires=...
    by https://s3.mesads.beta.gouv.fr/<filename>?<params>
    """

    def url(self, name, parameters=None, expire=None, http_method=None):
        url = super().url(
            name, parameters=parameters, expire=expire, http_method=http_method
        )
        matches = re.search(r"^(https?)://[^/]+/([^/]+)", url)
        match = matches.group(0)
        protocol = matches.group(1)
        bucket = matches.group(2)
        new_url = url.replace(match, f"{protocol}://{bucket}")
        return new_url
