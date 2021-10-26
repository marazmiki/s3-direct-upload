import io
import uuid

import requests
from botocore.client import BaseClient

from s3_direct_upload import Signer


def test_upload(
        boto_client: BaseClient,
        bucket_name: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region: str
):

    key = str(uuid.uuid4()) + ".txt"

    s = Signer(access_key_id=aws_access_key_id,
               secret_access_key=aws_secret_access_key,
               bucket=bucket_name, region=region
               )

    c = s.sign(key, content_type="text/plain")
    form_action = c.url
    print(c.url)
    print(c.as_html())
    content = b"one-two-three"

    resp = requests.post(form_action,
                         data=c.params, files={"file": io.BytesIO(content)}
                         )
    print(resp.content)
    resp.raise_for_status()

    url = boto_client.generate_presigned_url("get_object", Params={
        "Key": key,
        "Bucket": bucket_name,
    })
    # print(url)

    resp = requests.get(url)
    resp.raise_for_status()
    assert resp.content == content
