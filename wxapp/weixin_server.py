import os
import time
import json
import random
import string
import base64
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.backends import default_backend

from ..utils.ids import UUID7Generator


class Weixin:
    headers = {
        "Content-Type": "application/json",
    }

    @classmethod
    def _parseXML2Dict(cls, element: BeautifulSoup) -> dict | str:
        """
        递归函数，将 BeautifulSoup 解析后的 XML 元素转换为字典
        """
        if element.string:  # 如果元素有直接内容，则直接返回
            return element.string.strip()
        result = {}
        for child in element.children:
            if child.name:  # 忽略注释和其他非标签元素
                # 处理重复标签的情况
                if child.name in result:
                    # 如果已经存在同名标签，则将其转换为列表
                    if not isinstance(result[child.name], list):
                        result[child.name] = [result[child.name]]
                    result[child.name].append(cls._parseXML2Dict(child))
                else:
                    result[child.name] = cls._parseXML2Dict(child)
        return result

    @classmethod
    def getAccessToken(cls, appid: str, secret: str):
        """
        code:
        0       -> ok\n
        40029   -> js_code无效\n
        45011   -> API 调用太频繁，请稍候再试\n
        40226   -> 高风险等级用户，小程序登录拦截\n
        -1      -> 系统繁忙，此时请开发者稍候再试\n
        """
        error_mapping = {
            0: "ok",
            40029: "js_code无效",
            45011: "API 调用太频繁，请稍候再试",
            40226: "高风险等级用户，小程序登录拦截",
            -1: "系统繁忙，此时请开发者稍候再试"
        }
        token_url = "https://api.weixin.qq.com/cgi-bin/token"
        token_params = {
            "grant_type": "client_credential",
            "appid": appid,
            "secret": secret
        }
        token_response = requests.get(token_url, params=token_params)
        token_data = token_response.json()
        errcode = token_data.get("errcode", 0)
        errmsg = token_data.get("errmsg")
        assert int(errcode) == 0, error_mapping.get(errcode, errmsg)
        return {
            "access_token": token_data.get("access_token", None),
            "expires_in": token_data.get("expires_in", None)
        }


class Miniapp(Weixin):

    @classmethod
    def loginVerify(cls, appid: str, secret: str, code: str, *args, **kwargs) -> dict:
        """"
        code:
        0       -> ok\n
        40029   -> js_code无效\n
        45011   -> API 调用太频繁，请稍候再试\n
        40226   -> 高风险等级用户，小程序登录拦截\n
        -1      -> 系统繁忙，此时请开发者稍候再试\n
        """

        error_mapping = {
            40029: "code无效",
            45011: "API 调用太频繁，请稍候再试",
            40226: "高风险等级用户，小程序登录拦截",
            -1: "系统繁忙，此时请开发者稍候再试",
            0: "ok",
        }
        verify_url = "https://api.weixin.qq.com/sns/jscode2session"
        verify_params = {
            "grant_type": "authorization_code",
            "appid": appid,
            "secret": secret,
            "js_code": code
        }
        verify_response = requests.get(verify_url, params=verify_params)
        verify_data = verify_response.json()
        errcode = verify_data.get("errcode", 0)
        errmsg = verify_data.get("errmsg")
        assert int(errcode) == 0, error_mapping.get(errcode, errmsg)

        return {
            "openid": verify_data.get("openid"),
            "unionid": verify_data.get("unionid", None),
            "session_key": verify_data.get("session_key")
        }

    @classmethod
    def getPhoneNumber(cls, access_token: str, code: str) -> dict:
        """"
        code:
        0       -> ok\n
        40029   -> js_code无效\n
        45011   -> API 调用太频繁，请稍候再试\n
        40226   -> 高风险等级用户，小程序登录拦截\n
        -1      -> 系统繁忙，此时请开发者稍候再试\n
        """
        error_mapping = {
            40029: "code 无效",
            45011: "API 调用太频繁，请稍候再试",
            40013: "请求appid身份与获取code的小程序appid不匹配",
            -1: "系统繁忙，请开发者稍候再试",
            0: "ok",
        }
        method_url = f"https://api.weixin.qq.com/wxa/business/getuserphonenumber?access_token={access_token}"

        method_data = {
            "code": code
        }

        res = requests.post(method_url, json=method_data)
        res_data = res.json()
        errcode = res_data.get("errcode", 0)
        errmsg = res_data.get("errmsg")
        assert int(errcode) == 0, error_mapping.get(errcode, errmsg)
        phone_info = res_data.get("phone_info", {})
        return {
            "mobile": phone_info.get("purePhoneNumber", None),  # 没有区号的手机号
            "country_code": phone_info.get("countryCode", None)  # 区号
        }

    @classmethod
    def sendSubscribeMsg(
        cls,
        access_token: str,
        openid: str,
        template_id: str,
        page: str,
        data: dict,
        miniprogram_state: str = "formal"
    ):
        """
        code:
        0       -> ok\n
        40003   -> openid 无效\n
        40037   -> 模板id无效\n
        40038   -> 页面路径无效\n  
        40058   -> 模板数据字段不准确\n

        """

        error_mapping = {
            40003: "openid 无效",
            40037: "模板id无效",
            40038: "页面路径无效",
            40058: "模板数据字段不准确",
            0: "ok",
        }
        send_url = f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}"
        send_data = {
            "touser": openid,
            "template_id": template_id,
            "page": page,
            "miniprogram_state": miniprogram_state,
            "lang": "zh_CN",
            "data": data
        }
        send_response = requests.post(send_url, json=send_data)
        send_data = send_response.json()
        errcode = send_data.get("errcode", 0)
        errmsg = send_data.get("errmsg")
        assert int(errcode) == 0, error_mapping.get(errcode, errmsg)
        return send_data


class ServiceNumber(Weixin):
    """
    微信服务号
    """
    class CustomMessagBody:
        ...

    @classmethod
    def loginVerify(cls, appid: str, secret: str, code: str):
        """
        AssertionError: msg
        0       -> ok\n
        40029   -> code无效\n
        """
        ...

    @classmethod
    def getAccessToken(cls, appid: str, secret: str, force_refresh: bool = False):
        """
        code:
        0       -> ok\n
        40029   -> js_code无效\n
        45011   -> API 调用太频繁，请稍候再试\n
        40226   -> 高风险等级用户，小程序登录拦截\n
        -1      -> 系统繁忙，此时请开发者稍候再试\n
        """
        error_mapping = {
            0: "ok",
            40029: "js_code无效",
            45011: "API 调用太频繁，请稍候再试",
            40226: "高风险等级用户，小程序登录拦截",
            -1: "系统繁忙，此时请开发者稍候再试"
        }
        token_url = "https://api.weixin.qq.com/cgi-bin/stable_token"
        token_params = {
            "grant_type": "client_credential",
            "appid": appid,
            "secret": secret,
            "force_refresh": force_refresh
        }
        token_response = requests.get(token_url, params=token_params)
        token_data = token_response.json()
        errcode = token_data.get("errcode", 0)
        errmsg = token_data.get("errmsg")
        assert int(errcode) == 0, error_mapping.get(errcode, errmsg)
        return {
            "access_token": token_data.get("access_token", None),
            "expires_in": token_data.get("expires_in", None)
        }

    @classmethod
    def userBaseInfo(cls, access_token: str, openid: str, lang: str = "zh_CN") -> dict:
        """
        获取用户基本信息
        """
        error_mapping = {
            40003: "openid 无效",
            40001: "access_token 无效",
            40013: "AppID无效错误",
            0: "ok",
            -1: "系统繁忙，请开发者稍候再试"

        }
        url = f"https://api.weixin.qq.com/cgi-bin/user/info?access_token={access_token}&openid={openid}&lang={lang}"

        res = requests.get(url)
        res_data = res.json()
        errcode = res_data.get("errcode", 0)
        errmsg = res_data.get("errmsg")
        assert int(errcode) == 0, error_mapping.get(errcode, errmsg)
        return res_data

    @classmethod
    def createQRCode(
        cls,
        access_token: str,
        action_name: str,
        scene_id: int = None,
        scene_str: str = None,
        expire_seconds: int = None
    ) -> dict:
        """
        创建二维码ticket,用于生成带参数的二维码
        ================================================================================================================
        Args:
            access_token: 微信公众号的access_token
        :param scene_id: 场景值ID,临时二维码时为32位非0整型,永久二维码时最大值为100000（目前参数只支持1--100000）
        :return: 返回的JSON数据包,包含ticket、expire_seconds、url
        ===============================================================================================================
        """
        ...

    @classmethod
    def decryptMessage(
        cls,
        from_xml: str,
        msg_sign: str,
        timestamp: str,
        nonce: str,
        token: str,
        encoding_aes_key: str
    ) -> str:
        """
        解密消息

        Args:
            from_xml: XML
            msg_sign: 签名串,对应URL参数的msg_signature
            timestamp: 时间戳,对应URL参数的timestamp
            nonce: 随机串,对应URL参数的nonce
            token: 微信公众号平台设置的token
            encoding_aes_key: 公众平台上,开发者设置的EncodingAESKey

        Returns:
            xml_content: 解密后的消息
        """
        ...

    @classmethod
    def sendCustomMessage(cls, openid: str, meg_body: CustomMessagBody):

        ...

    @classmethod
    def sendTemplateMessage(
        cls,
        appid: str,
        access_token: str,
        openid: str,
        template_id: str,
        data: dict,
        url: str = None
    ):
        """
        发送模板消息
        """
        error_mapping = {
            -1: "系统繁忙，请开发者稍候再试",
            0: "ok",
            40013: "AppID无效错误",
            40036: "不合法的 template_id 长度",
            40037: "不合法的 template_id",
            40039: "不合法的 URL 长度",
        }
        send_url = "https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={}".format(access_token)
        req_data = {
            "touser": openid,
            "template_id": template_id,

            "data": data
        }
        if url:
            req_data["url"] = url
            req_data["miniprogram"] = {
                "appid": appid,
                # "pagepath": "pages/index"
            }
        send_response = requests.post(send_url, json=req_data)

        send_data = send_response.json()
        errcode = send_data.get("errcode", 0)
        errmsg = send_data.get("errmsg")
        assert int(errcode) == 0, error_mapping.get(errcode, errmsg)
        return send_data


class WechatPayV3:
    basedir = os.path.abspath(os.path.dirname(__file__))  # 获取当前目录

    def __init__(self,
                 app_id: str,
                 mch_id: str,
                 private_key: str,
                 api_v3_key: str,
                 serial_no: str,
                 notify_url: str,
                 private_key_password: str = None,
                 certificates_path: str = None,
                 ignore_resp_sign=False,
                 ):
        """
        :param ignore_resp_sign: 是否忽略应答验签(用于第一次缓存证书)
        """
        self.app_id = app_id
        self.mch_id = mch_id
        self.private_key = private_key
        self.private_key_password = private_key_password
        self.api_v3_key = api_v3_key
        self.serial_no = serial_no  # 证书序列号(微信支付商户平台获取)
        self.ignore_resp_sign = ignore_resp_sign
        self.notify_url = notify_url
        self.certificates_path = certificates_path or os.path.join(self.basedir, "certificates.json")

    def _auth(self, req: requests.Request):
        """
        ==构造签名串==\n
        签名串一共有5个部分,每一行为一个参数。
        结尾以\\n（换行符,ASCII编码值为0x0A）结束,包括最后一行。
        如果参数本身以\\n结束,也需要附加一个\\n。
        ```
        HTTP请求方法\\n
        URL\\n
        请求时间戳\\n
        请求随机串\\n
        请求报文主体\\n
        ```

        """
        # 1.获取HTTP请求的方法
        data = req.method + "\n"
        # 2.获取请求的绝对URL，请注意需要去除域名部分。
        parsed = urlparse(req.url)
        data += parsed.path
        if parsed.query:
            data += "?" + parsed.query
        data += "\n"
        # 3.获取请求时间戳
        timestamp = str(int(time.time()))
        data += timestamp + "\n"
        # 4.生成一个请求随机串，推荐生成随机数算法如下：调用随机数函数生成，将得到的值转换为字符串。
        nonce_str = "".join(random.sample(string.ascii_letters + string.digits, 32))
        data += nonce_str + "\n"
        # 5.获取请求报文主体
        if req.data:
            data += req.data
        data += "\n"
        # 6.构造签名串,计算签名
        signature = self.sign(data)
        # 7.构造请求头
        # ==设置HTTP头==
        authorization = ('WECHATPAY2-SHA256-RSA2048 '
                         'mchid="{0}",nonce_str="{1}",'
                         'signature="{2}",timestamp="{3}",'
                         'serial_no="{4}"').format(self.mch_id,
                                                   nonce_str,
                                                   signature,
                                                   timestamp,
                                                   self.serial_no)
        req.headers["Authorization"] = authorization
        req.headers["Content-Type"] = "application/json"
        req.headers["Accept"] = "application/json"
        req.headers["User-Agent"] = "requests " + requests.__version__
        r = req.prepare()
        s = requests.Session()
        resp = s.send(r, timeout=2)
        # 验签
        if not self.ignore_resp_sign:
            nonce = resp.headers.get("Wechatpay-Nonce")
            signature = resp.headers.get("Wechatpay-Signature")
            serial = resp.headers.get("Wechatpay-Serial")
            timestamp = resp.headers.get("Wechatpay-Timestamp")
            body = resp.text
            cer = self.getCertificateBySerialNO(serial)
            ret = self.respSign(timestamp=timestamp,
                                nonce=nonce,
                                body=body,
                                cer=cer,
                                signature=signature)
            assert ret is None, "resp sign error"

        return resp

    @classmethod
    def genOutTradeNO(cls, trade_type="jsapi", nacl=None):
        """
        生成商户订单号
        :param trade_type: 交易类型
        :param nacl: 盐
        """
        datetime.now().timestamp()
        out_trade_no = str(int(datetime.now().timestamp() * 10000)) + str(...)
        out_trade_no = str(UUID7Generator.generate(methods="hex"))
        # return out_trade_no[:32]
        return out_trade_no

    def paySign(self, prepay_id: str, nonce_str: str = None):
        package = "prepay_id=" + prepay_id
        sign_type = "RSA"
        timestamp = int(time.time())
        if not nonce_str:
            nonce_str = "".join(random.sample(string.ascii_letters + string.digits, 32))
        s = "{0}\n{1}\n{2}\n{3}\n".format(self.app_id, timestamp, nonce_str, package)
        pay_sign = self.sign(s)
        return dict(
            app_id=self.app_id,
            mch_id=self.mch_id,
            timestamp=timestamp,
            nonce_str=nonce_str,
            prepay_id=prepay_id,
            package=package,
            sign_type=sign_type,
            pay_sign=pay_sign
        )

    def sign(self, s: str):
        """
        签名串需经过SHA256withRSA签名后，再经过Base64编码
        :param s: 待签名串
        :param private_key: 私钥
        :param private_key_password: 私钥密码,如果私钥有密码，请提供
        """
        # with open("./apiclient_key.pem", "r") as f:
        #     api_client_key = f.read()
        private_key = load_pem_private_key(
            self.private_key.encode(),
            password=self.private_key_password,
            backend=default_backend()
        )
        signature = base64.b64encode(
            private_key.sign(
                s.encode(),
                padding.PKCS1v15(),
                hashes.SHA256()
            ))
        return signature.decode()

    @classmethod
    def respSign(cls, timestamp: str, nonce: str, body: str, cer: bytes, signature):
        """
        验签
        :param timestamp: 时间戳
        :param nonce: 随机字符串
        :param body: 应答内容
        """
        # 加载证书
        cert = x509.load_pem_x509_certificate(cer, default_backend())
        # 获取公钥
        public_key = cert.public_key()
        # 验签

        try:
            signature = base64.b64decode(signature)
            # s = timestamp + "\n" + nonce + "\n" + body + "\n"
            s = "{0}\n{1}\n{2}\n".format(timestamp, nonce, body)
            public_key.verify(
                signature=signature,
                data=s.encode(),
                padding=padding.PKCS1v15(),
                algorithm=hashes.SHA256()   # 指定哈希算法
            )
        except Exception as e:
            return e.__str__()
        return None

    def getCertificates(self):
        """下载证书"""
        url = "https://api.mch.weixin.qq.com/v3/certificates"
        req = requests.Request(method="GET", url=url)
        response = self._auth(req=req)
        result = response.json()
        with open(self.certificates_path, "w+") as f:
            f.write(json.dumps(result["data"], indent=4))
        return result

    def getCertificateBySerialNO(self, serial_no) -> bytes:
        """读取缓存证书"""
        if not os.path.exists(self.certificates_path):
            raise FileNotFoundError("请先下载证书进行缓存")
        with open(self.certificates_path, "r") as f:
            content = f.read()
        certificates = json.loads(content)
        nonce, ciphertext, associated_data = None, None, None
        for certificate in certificates:
            if certificate["serial_no"] == serial_no:
                nonce = certificate["encrypt_certificate"]["nonce"]
                ciphertext = certificate["encrypt_certificate"]["ciphertext"]
                associated_data = certificate["encrypt_certificate"]["associated_data"]
                break
        if ciphertext is None:
            raise ValueError("certificate not found")
        cer = self.decryptAesGcm(nonce=nonce,
                                 ciphertext=ciphertext,
                                 associated_data=associated_data)
        return cer

    def decryptAesGcm(self, nonce, ciphertext, associated_data) -> bytes:
        aes_gcm = AESGCM(self.api_v3_key.encode())
        plaintext = aes_gcm.decrypt(nonce=nonce.encode(),
                                    associated_data=associated_data.encode(),
                                    data=base64.b64decode(ciphertext))
        return plaintext

    def jsapiPay(
            self,
            openid,
            price,

            out_trade_no,
            currency="CNY",
            description="测试jsapi支付",

            attach=None
    ):
        """
        小程序支付
        :param openid: 用户openid
        :param price: 订单总金额，单位为分
        :param out_trade_no: 商户订单号
        :param description: 商品描述
        :param attach: 商户数据包
        """
        url = "https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi"
        notify_url = self.notify_url
        data = dict(appid=self.app_id,
                    mchid=self.mch_id,
                    description=description,
                    notify_url=notify_url,
                    out_trade_no=out_trade_no,
                    amount=dict(total=price,
                                currency=currency),
                    payer=dict(openid=openid))
        if attach is not None:
            data["attach"] = json.dumps(attach)
        req = requests.Request(method="POST", url=url, data=json.dumps(data))
        response = self._auth(req=req)
        result = response.json()
        # {"code": "PARAM_ERROR", "message": "无效的openid"}
        {"prepay_id": "wx20151334596424dc845862de1d70960001"}
        prepay_id = result["prepay_id"]
        return prepay_id

    def queryOrder(self, out_trade_no=None, transaction_id=None):
        if out_trade_no is None and transaction_id is None:
            raise ValueError("Param Error")
        if out_trade_no is not None:
            url = "https://api.mch.weixin.qq.com/v3/pay/transactions/out-trade-no/{0}".format(out_trade_no)
        else:
            url = "https://api.mch.weixin.qq.com/v3/pay/transactions/id/{0}".format(transaction_id)
        url += "?" + "mchid=" + self.mch_id
        req = requests.Request(method="GET", url=url)
        response = self._auth(req=req)
        result = response.json()
        return result
