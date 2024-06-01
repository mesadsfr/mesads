import unittest

from .s3storage import HackishS3Boto3Storage


class TestHackishS3Boto3Storage(unittest.TestCase):
    def test_storage(self):
        storage = HackishS3Boto3Storage(
            bucket_name="mybucket.domain.com",
            access_key="key",
            secret_key="secret",
            endpoint_url="https://cellar-c2.services.clever-cloud.com/",
        )
        res = storage.url("/directory/file.jpg")
        self.assertIn("https://mybucket.domain.com/directory/file.jpg", res)
        self.assertIn("AWSAccessKeyId=", res)
        self.assertIn("Signature=", res)
        self.assertIn("Expires=", res)
