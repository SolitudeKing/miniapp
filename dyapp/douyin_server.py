import requests


class Douyin:

    headers = {
        "Content-Type": "application/json",
    }

    @classmethod
    def getAccessToken(cls, appid: str, secret: str):

        error_mapping = {
            0: "成功",
            -1: "系统错误",
            40015: "appid 错误",
            40017: "secret 错误",
            40020: "grant_type 不是 client_credential",

        }
        token_url = "https://developer.toutiao.com/api/apps/v2/token"
        token_params = {
            "grant_type": "client_credential",
            "appid": appid,
            "secret": secret
        }
        headers = cls.headers

        token_response = requests.post(token_url, headers=headers, json=token_params)
        token_data = token_response.json()
        errcode = token_data.get("err_no", -1)
        errmsg = token_data.get("err_tips")
        assert int(errcode) == 0, error_mapping.get(errcode, errmsg)
        return {
            "access_token": token_data.get("access_token", None),
            "expires_in": token_data.get("expires_in", None)
        }


from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
import base64


class Miniapp(Douyin):

    # 解密手机号date
    @classmethod
    def decodeMobile(cls, ciphertext_str: str, private_key_str: str):
        # 加载密钥
        private_key = serialization.load_pem_private_key(
            private_key_str.encode(),
            password=None,
        )

        ciphertext = base64.b64decode(ciphertext_str.encode('utf-8'))
        plaintext = private_key.decrypt(
            ciphertext,
            padding.PKCS1v15()
        )
        return plaintext.decode()

    @classmethod
    def loginVerify(cls, appid: str, secret: str, code: str, anonymous_code: str = None, *args, **kwargs) -> dict:
        """
        登录

        Args:
            appid (str): 小程序ID
            secret (str): 小程序密钥
            code (str): 登录时获取的code
            anonymous_code (str, optional): 匿名登录时获取的code. Defaults to None.
        """
        error_mapping = {
            0: "成功",
            -1: "系统错误",
            40014: "未传必要参数，请检查",
            40015: "appid错误",
            40017: "secret错误",
            40018: "code错误",
            40019: "anonymous_code错误",

        }

        verify_url = "https://developer.toutiao.com/api/apps/v2/jscode2session"
        verify_params = {
            "appid": appid,
            "secret": secret,
            "code": code
        }
        if anonymous_code:
            verify_params["anonymous_code"] = anonymous_code

        verify_response = requests.post(verify_url, headers=cls.headers, json=verify_params)
        response_data = verify_response.json()
        errcode = response_data.get("err_no", -1)
        errmsg = response_data.get("err_tips")
        assert int(errcode) == 0, error_mapping.get(errcode, errmsg)
        verify_data = response_data.get("data")
        return {
            "openid": verify_data.get("openid"),
            "unionid": verify_data.get("unionid", None),
            "anonymous_openid": verify_data.get("anonymous_openid", None),
            "session_key": verify_data.get("session_key"),
        }

    @classmethod
    def getPhoneNumber(cls, access_token: str, code: str, private_key: str) -> dict:

        error_mapping = {

        }

        method_url = "https://open.douyin.com/api/apps/v1/get_phonenumber_info/"

        headers = cls.headers
        headers["access-token"] = access_token

        method_data = {
            "code": code
        }

        res = requests.post(method_url, headers=headers, json=method_data)
        res_data = res.json()
        errcode = res_data.get("err_no", -1)
        errmsg = res_data.get("err_tips")
        assert int(errcode) == 0, error_mapping.get(errcode, errmsg)
        data = res_data["data"]
        # 解密data

        phone_info = cls.decodeMobile(data, private_key)
        return {
            "mobile": phone_info.get("purePhoneNumber", None),  # 没有区号的手机号
            "country_code": phone_info.get("countryCode", None)  # 区号
        }
