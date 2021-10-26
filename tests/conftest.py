import os

import boto3
import pytest
from dotenv import load_dotenv


def pytest_configure():
    load_dotenv()


def create_env_fixture(envname: str):
    """
    A helper function to create a fixture that safely extracts the
    required environment variable. If the variable was not set,
    the test case using the fixture, skips.

    """
    def inner():
        if not os.environ.get(envname):
            pytest.skip("A required variable did not set: " + envname)
        return os.environ[envname]
    inner.__doc__ = ("Returns the value of " + envname + " variable. "
                     "If it is empty, the test will be skipped")
    return pytest.fixture(inner)


@pytest.fixture
def boto_client(
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region: str,
        bucket_name: str
):
    """
    Creates a boto3 instance to check s3 objects we're uploading
    """
    return boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region
    )


aws_access_key_id = create_env_fixture("AWS_ACCESS_KEY_ID")
aws_secret_access_key = create_env_fixture("AWS_SECRET_ACCESS_KEY")
region = create_env_fixture("REGION")
bucket_name = create_env_fixture("BUCKET_NAME")
