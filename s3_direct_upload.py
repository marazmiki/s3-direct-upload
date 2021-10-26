from binascii import b2a_base64
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from hmac import new as hmac
from json import dumps as json_dumps
from typing import Union

Signable = Union[str, bytes]

ACL_PRIVATE = "private"
ACL_PUBLIC = "public"
DEFAULT_CONTENT_TYPE = "application/octet-stream"
DEFAULT_EXPIRES_IN = 5 * 60
DEFAULT_REGION = "us-east-1"

REGIONS = {
    "us-east-1": "s3.amazonaws.com",
    "us-west-2": "s3-us-west-2.amazonaws.com",
    "us-west-1": "s3-us-west-1.amazonaws.com",
    "eu-west-1": "s3-eu-west-1.amazonaws.com",
    "eu-central-1": "s3.eu-central-1.amazonaws.com",
    "ap-southeast-1": "s3-ap-southeast-1.amazonaws.com",
    "ap-southeast-2": "s3-ap-southeast-2.amazonaws.com",
    "ap-northeast-1": "s3-ap-northeast-1.amazonaws.com",
    "sa-east-1": "s3-sa-east-1.amazonaws.com",
}


@dataclass
class Result:
    url: str
    method: str = "POST"
    params: dict[str, str] = None

    def as_html(self, newline=True) -> str:
        return ("\n" if newline else "").join(self.render_field(k, v) for
                                              k, v in self.params.items())

    def render_field(self, name: str, value: str) -> str:
        return (
            """<input type="hidden" name="{name}" value="{value}">"""
        ).format(name=name, value=value)


def base64_encode(string: bytes):
    return b2a_base64(string, newline=False)


def get_bucket_url(bucket_name: str, region: str):
    return "https://" + bucket_name + "." + REGIONS.get(region,
                                                        "s3.amazonaws.com")


def _b(data):
    return data.encode() if isinstance(data, str) else data


def sign(key: Signable, msg: Signable, as_hexdigest: bool = False) -> bytes:
    return getattr(
        hmac(_b(key), _b(msg), digestmod=sha256),
        "hexdigest" if as_hexdigest else "digest"
    )()


class Signer:
    ALGO = "AWS4-HMAC-SHA256"
    SERVICE = "s3"
    SCOPE = "aws4_request"

    def __init__(self, access_key_id: str, secret_access_key: str,
                 bucket: str, region: str):
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket = bucket
        self.region = region

    def get_x_amz_credential(self):
        raw_date = datetime.utcnow().strftime('%Y%m%d')
        return "/".join([self.access_key_id, raw_date, self.region,
                         self.SERVICE, self.SCOPE])

    def get_x_amz_algorithm(self):
        return self.ALGO

    def get_x_amz_date(self):
        return datetime.utcnow().strftime("%Y%m%dT%H%M%S000Z")

    def get_policy_object(self, expiration: str, acl: str, content_type: str):
        return {
            'expiration': expiration,
            'conditions': [
                {'bucket': self.bucket},
                {'acl': acl},
                ['starts-with', "$key", ''],
                {'success_action_status': '201'},
                {'x-amz-credential': self.get_x_amz_credential()},
                {'x-amz-algorithm': self.get_x_amz_algorithm()},
                {'x-amz-date': self.get_x_amz_date()},
                {'content-type': content_type},
            ]
        }

    def sign(
            self,
            key: str,
            content_type: str = DEFAULT_CONTENT_TYPE,
            acl: str = ACL_PRIVATE,
            expires_in: int = DEFAULT_EXPIRES_IN
    ) -> Result:
        now = datetime.utcnow()
        now_date = self.get_x_amz_date()
        raw_date = now.strftime('%Y%m%d')
        expires = (
                now + timedelta(seconds=expires_in)
        ).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        policy_object = json_dumps(
            self.get_policy_object(
                acl=acl,
                content_type=content_type,
                expiration=expires
            )
        )

        policy = base64_encode(policy_object.encode())

        date_key = sign("AWS4" + self.secret_access_key, raw_date)
        date_region_key = sign(date_key, self.region)
        date_region_service_key = sign(date_region_key, self.SERVICE)
        signing_key = sign(date_region_service_key, self.SCOPE)
        signature = sign(signing_key, policy, as_hexdigest=True)

        return Result(
            url=get_bucket_url(self.bucket, self.region),
            method="POST",
            params={
                "policy": policy.decode(),
                "success_action_status": 201,
                "x-amz-credential": self.get_x_amz_credential(),
                "x-amz-date": now_date,
                "x-amz-signature": signature,
                "x-amz-algorithm": "AWS4-HMAC-SHA256",
                "key": key,
                "acl": acl,
                "content-type": content_type
            }
        )
