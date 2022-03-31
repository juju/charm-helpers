import json
import mock
import unittest

import charmhelpers.contrib.openstack.cert_utils as cert_utils

from base64 import b64decode, b64encode

rsa_certs = {
    'ca_key': b64encode('''-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAnhnAUJC+ZLlkmFZq1adbFgzJelPtr/M5T/7ao2kbVQEaocMS
TR9FLbhgfDvbNVQKB/YcsdT+Vb0CJTZ/0pQAhF51y9TqJDII/++q+7PGwBRBv4O4
I4FI/120vKu7FTu9oKRBVxsIRolyn6mpvxmlEcZXsfsuyoNrdKUdG1rOEbyRJRZY
8En67UkRLnMajPod4bguZc8qktt/R0kD18U8V9k1ROXGM8XTlgPyAmdkguo9heic
ZB+moXgCGveyxktIM1Lm2v2uM7MiM/Hln4cRcxnI63saAhbQcdoRoP9YyUQ3lV5y
XyrQd1vhmqSrn7lHbR8OJNAy983smPfcIv2r8QIDAQABAoIBAAlcLO6YIy2DbFk4
hIqxpcrgZu0/GstX8wSxafBSwLN/pTv+eI7oUwgp6kxwnsHBf/aIs5ozqfsZfY8G
cvrcmEs97Gts54/NBotgfRb5xcKJcHsOKVCwzsmPmquw3xqattdT4ipuB0dly8t4
F/ygYA11WKvI2zRSI4J8ZATCk4CpOXaUMB06Es6VUb0dDhwncCfXoOyo3CSp5/8L
SCF4xpogqos8waXUWbUTIFw/SxIkY1WcQwACEMFw6JZdH33N0DDFFEdXGfl+VXp7
Bzjru6c8raO8VsMUsazMTmdpyNrwF7Q1RBoz46F3jlPfoVS0DRZ42PjEy52Dj3FW
U4leqYECgYEA0hx9d/DHcYdSA5IisPCRhjA0FY7rrfZzZoPbXBJWNScCqzrka1jQ
2a+LzAMk8KzxqJvrWcyZE6BC8+ELnekip/xpnb/aNrWJ7V3a4/ErgI9nQ++SRZdC
XlmLpE0DUQvXI5bRQUFpza52iRkVA9a/rCCPnvbdiCTwediVsrw19A0CgYEAwKFL
5rX/GoJ1tlt4ULkSzIY/bYm0+/uLrpsYunWruWhPGu+o4laaOBc9Mzv7xH/4OGk5
ZJ6UxoBOQgCKC7KU9t94hgsUmcNJeN+OtnfLsWtUPjoQQKlqCXwzS9Q8aIzNf2OR
ZOENsJ3uVRzhIF+UrAX3dFnn0kJK6TD1oku3KnUCgYB5sXKiM1zwzlWcJ9nb7Zn7
xJOGIP80BNgV+izlCOHRa0TKdBO0cP6V9mzbvr54f1KAO752hl/q1BmzMxcNYOhn
r3Rkn6f9o+u9BW0wNJDjpytCV9G6aL9R8j9E7C4NlPQIcuPEDeT/8hpJkbNwQ8NE
KJ/GjGkG345ApEcf/I6rSQKBgGE2hYmPO4jzYdh/3P5QCE6zSXtMTcwFLH8XwqkH
DXzqSVG8tSxUrEu2XqpmkS6frnM5lz9SUJ7Ezbm9b+1rWIYmTTrIiML4rTGVEP7B
AkktczxcLSuU0/Cpf3G7UCkrNeIeK5gPg8soSMknY+3kjrEp6bIMVVPlJMz+alhX
gb6pAoGBAI/Ue1O6nXez/eCvARENo+5q86MGKj0EaO6O11AHSGpQyNOvNFAKjOv6
USJcDiGtVXjpw7Cy2FmNMtdWdbD/L6xo65Z3i9FUXvfx7i8laYjviZhsKNZNMMbE
q5pvXG3kwLYCqss381upQoKSYd4QuoVTKC19qZ12ubfiB45B/4nr
-----END RSA PRIVATE KEY-----'''.encode()),
    'ca_cert': b64encode('''-----BEGIN CERTIFICATE-----
MIIDPzCCAiegAwIBAgIUfhjNMTbE2ufAPObs8lV1RQaZ/RswDQYJKoZIhvcNAQEL
BQAwEjEQMA4GA1UEAwwHcm9vdF9jYTAeFw0yMjA0MDQxMjE0MjVaFw0yNjA0MDQx
MjE0MjVaMBIxEDAOBgNVBAMMB3Jvb3RfY2EwggEiMA0GCSqGSIb3DQEBAQUAA4IB
DwAwggEKAoIBAQCeGcBQkL5kuWSYVmrVp1sWDMl6U+2v8zlP/tqjaRtVARqhwxJN
H0UtuGB8O9s1VAoH9hyx1P5VvQIlNn/SlACEXnXL1OokMgj/76r7s8bAFEG/g7gj
gUj/XbS8q7sVO72gpEFXGwhGiXKfqam/GaURxlex+y7Kg2t0pR0bWs4RvJElFljw
SfrtSREucxqM+h3huC5lzyqS239HSQPXxTxX2TVE5cYzxdOWA/ICZ2SC6j2F6Jxk
H6aheAIa97LGS0gzUuba/a4zsyIz8eWfhxFzGcjrexoCFtBx2hGg/1jJRDeVXnJf
KtB3W+GapKufuUdtHw4k0DL3zeyY99wi/avxAgMBAAGjgYwwgYkwHQYDVR0OBBYE
FKDWfP1/EF2aAlcJyQJMPGJ9GszYME0GA1UdIwRGMESAFKDWfP1/EF2aAlcJyQJM
PGJ9GszYoRakFDASMRAwDgYDVQQDDAdyb290X2NhghR+GM0xNsTa58A85uzyVXVF
Bpn9GzAMBgNVHRMEBTADAQH/MAsGA1UdDwQEAwIBBjANBgkqhkiG9w0BAQsFAAOC
AQEAhILWfl+ldAnfRuXj3qHs6q/0zZz1uSlG8gSFlO/KuINYi6/Vp1r7BjRmTymD
J1lPY7haQ8nlraT/j3CjXcCHHeUBCjShT8oWyLFxu/2FpMbw9B7zqqoSy1LVrIKh
xfuRma2TUx3vxUpAvQIsw98si/2EH1qzUuvv47jb8Zg59EULtjT8pkN81FgXVOme
s3V7YqAUSDLechoCN+rR0iWi7zVI6LeFnlfwWwMqYW/5SiWasgQohZM9eAjXECo7
cSXGCUfL3EDAmbRxOMCOLFF5WNmGsm//a2ZEegnY/GmCNw501e3spqXzXIe5HRRR
jOm40xKhkPtObqOe2lRsRzT1ww==
-----END CERTIFICATE-----'''.encode()),
    'server_key': b64encode('''-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC3f7DzliwS5KsZ
QNSK+9Zq+qZuLO4ptwCGGcfFYV8WTziy1ORvCJk5adRlS4kEhq4KBE+l+EJVOSrx
PxUS8z/2JalxJ2fD6jrUrkEp9AAJefwpbK9qTMJ4PeuoLaPnzxtuvDesdzdSX4F1
Ubm5Wr0g3RqDwrp5lrrAQNT65rXq7Vm7BRNFcLowpP3c9mno2IW1jA2oDgBP0P5J
YICCA82E6Oz/hvp80uLUcu7Om0RaYf8Z8JwfkvK1qhrdJEMaqfdAhNJ0HlWPVnQz
Io9H8XDJkIlLL1UNCTVRoJb2OgnKvGFIU+Rwa7bG2Wq5QceH/4T+KUeWvf9VN9Ef
K0wURcrpAgMBAAECggEAJ2dDHzt7IV97IkQan/GuPHCwdm4tgkWq1iEJFehv28GN
QlGW8ATfqkWAd3P96zvkeYAtfk1OKTDKeN178ALOFFRIC2VT0e0lTvBQS+r6aw6H
yHlvPZtYEyvww79xN+DwWhoOtnkvJwAdM40mHZhPjpQMEokpM9zbI1eIpIwQOm76
N65FwyiCghumUKPLDRvTjiVPDT/RuIDMzUAUKXSkh/2wfNarGWy6jDZS03b+8uBe
ggPUSqTmtoSxL9C5aAG9CJi8SUkakw2s2fjwQxyeXC1GaWWnziFDA1Rhl1xnbehO
QgDKhcwZMmddc1fySanei9EX5zgB2M8nQGeRljlCEQKBgQDgM7ht53Z0dxGHcbgE
pJQBJQc9RScfTlU/L09DBOJI2rw5VtBXhCXEIQLxCM/A2H+e9vV8bhYbLLOB0vm8
wCEs06gfikCzOKid+gr6gV1yfURCvd7zKv7HLZY9938oeqHuKYUef4gvFy/Ivw7U
oGpkL1xlXD3FKbbAD6/S8WOxvQKBgQDRhiBTMO6eOvuiSj5YvCXMsRnicJDIOVaK
ZuhgQo9WMZoAgX238Zpm63MQmqGc1NQt/uJXnyEr83/xtf+lGeGiWDzk8CJvPNNG
fDhgAMqAtkjYUkPmVaR3xWwt9cxiMIK3edoiB9WYjuQChYP+75VqV0r85AFFoi5s
qNWlPBSSnQKBgCz4EsDwkSDRFRH+rDM6M3l7TNVsPmmYE58lxRcjLqQAQ4qYsBct
qUmKeYWRB+KdShO/YwO/LO3sbGDYyUCjpMPR/EG/QDTyY1e0ZGlUc0LYf02HueU6
NXoL2bu6HaYn2rzjVREF8XHIi8wPDlF1j4FiwnyOINGgCUjCnLiJtD5dAoGAVJ56
x55ngHgJ0I1ziJrUGUsdTRpxHqwpi1PsXZQEF6eIrtOdVoC4/v/wRLBuvMwntTvP
Zdvapcl9zrzWNnOxcMN6NGvXPF2wZjMdAYjQQBNecB8pVQkZl1WgTx+KH82/vSH1
OvE3DpoG9A3ANWHFUmFW47Oh3+GUJkY5orYVCPECgYEAya7XvUKwzsW1481+cHMw
D9gAKMxkkPw+66SFZpRXGhCmAbhOxWaMRnT/CLDYf4jRkuFp0O7uh3rtVrhZf71z
KAXlrNCq0cJotAQmfK7h4/8TgECz+h4KFfE6q3IlqbOOhCwYczRGkjGmh5qRYidu
ksQN9IhwJNVGqPMhWznB11s=
-----END PRIVATE KEY-----'''.encode()),
    'server_cert': b64encode('''-----BEGIN CERTIFICATE-----
MIIDVjCCAj6gAwIBAgIQc3/Zflj6FxtoQphOJRYFuTANBgkqhkiG9w0BAQsFADAS
MRAwDgYDVQQDDAdyb290X2NhMB4XDTIyMDQwNDEyMTQyNVoXDTI2MDQwNDEyMTQy
NVowETEPMA0GA1UEAwwGc2VydmVyMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIB
CgKCAQEAt3+w85YsEuSrGUDUivvWavqmbizuKbcAhhnHxWFfFk84stTkbwiZOWnU
ZUuJBIauCgRPpfhCVTkq8T8VEvM/9iWpcSdnw+o61K5BKfQACXn8KWyvakzCeD3r
qC2j588bbrw3rHc3Ul+BdVG5uVq9IN0ag8K6eZa6wEDU+ua16u1ZuwUTRXC6MKT9
3PZp6NiFtYwNqA4AT9D+SWCAggPNhOjs/4b6fNLi1HLuzptEWmH/GfCcH5Lytaoa
3SRDGqn3QITSdB5Vj1Z0MyKPR/FwyZCJSy9VDQk1UaCW9joJyrxhSFPkcGu2xtlq
uUHHh/+E/ilHlr3/VTfRHytMFEXK6QIDAQABo4GoMIGlMAkGA1UdEwQCMAAwHQYD
VR0OBBYEFFNUTBIAyHywQtnxLinEV0ptSQpeME0GA1UdIwRGMESAFKDWfP1/EF2a
AlcJyQJMPGJ9GszYoRakFDASMRAwDgYDVQQDDAdyb290X2NhghR+GM0xNsTa58A8
5uzyVXVFBpn9GzAdBgNVHSUEFjAUBggrBgEFBQcDAQYIKwYBBQUHAwIwCwYDVR0P
BAQDAgWgMA0GCSqGSIb3DQEBCwUAA4IBAQCI6nGhEj74Yr8hvMMBsvWsD2OqFy9c
gg+5gT9+d+mSszuJPA/oXX7xeXEw0PLezKTR4OYKcZP3m9IMDuvlWAeyosNcm/VN
rkBJD5SqbAYQPRl2uo1LlhnvpOWVI6E3ik8KcKb7D6OtPOB851kCl21bD30zr9fu
HIg8fx07p7AbtVlJB3zAy2pF4zwMuPe0IIil0op7UJNRNhYfH8uQneUw4TPv3h5d
ZKSHtCFgRce/T7PX+4/GcQEycmrTrbhkuJ5uY/9VcFi5j6pvFuGcT/rmlbLfqabX
3szYaO+M+6TVvDzadMgMDObEeH56JP3lHFwj/WgEIBInkr9P/bcA4Sm/
-----END CERTIFICATE-----'''.encode()),
    'server_pub': '''-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAt3+w85YsEuSrGUDUivvW
avqmbizuKbcAhhnHxWFfFk84stTkbwiZOWnUZUuJBIauCgRPpfhCVTkq8T8VEvM/
9iWpcSdnw+o61K5BKfQACXn8KWyvakzCeD3rqC2j588bbrw3rHc3Ul+BdVG5uVq9
IN0ag8K6eZa6wEDU+ua16u1ZuwUTRXC6MKT93PZp6NiFtYwNqA4AT9D+SWCAggPN
hOjs/4b6fNLi1HLuzptEWmH/GfCcH5Lytaoa3SRDGqn3QITSdB5Vj1Z0MyKPR/Fw
yZCJSy9VDQk1UaCW9joJyrxhSFPkcGu2xtlquUHHh/+E/ilHlr3/VTfRHytMFEXK
6QIDAQAB
-----END PUBLIC KEY-----'''.encode(),
}

ec_certs = {
    'ca_key': b64encode('''-----BEGIN EC PRIVATE KEY-----
MIGkAgEBBDBaLKFGs/6gl0qr46DOvKchCjLR/Qwa5bX0ofvHZ6XzziwPiJpNRIXr
DGn6dy0ahTSgBwYFK4EEACKhZANiAATbytPyF9NnVS5MLVHLyc22t3b3FHsH9LRt
VnRWky2uxdfmGqjjFZaCWxz2D3AsQyYEVmnkInRV0nbD1WkBCQntp/WHS8DVIt7j
vQPw90VefzGd9lN5UZKNwHlBhQb+Vxc=
-----END EC PRIVATE KEY-----'''.encode()),
    'ca_cert': b64encode('''-----BEGIN CERTIFICATE-----
MIIB7zCCAXagAwIBAgIUPdrHjpTzdGmxOhOb6PLPgz1KNP8wCgYIKoZIzj0EAwIw
EjEQMA4GA1UEAwwHcm9vdF9jYTAeFw0yMjA0MDUxNzUyMTRaFw0yNjA0MDUxNzUy
MTRaMBIxEDAOBgNVBAMMB3Jvb3RfY2EwdjAQBgcqhkjOPQIBBgUrgQQAIgNiAATb
ytPyF9NnVS5MLVHLyc22t3b3FHsH9LRtVnRWky2uxdfmGqjjFZaCWxz2D3AsQyYE
VmnkInRV0nbD1WkBCQntp/WHS8DVIt7jvQPw90VefzGd9lN5UZKNwHlBhQb+Vxej
gYwwgYkwHQYDVR0OBBYEFOtxQHpF0SK7iBjbrkmvLyzsGikEME0GA1UdIwRGMESA
FOtxQHpF0SK7iBjbrkmvLyzsGikEoRakFDASMRAwDgYDVQQDDAdyb290X2NhghQ9
2seOlPN0abE6E5vo8s+DPUo0/zAMBgNVHRMEBTADAQH/MAsGA1UdDwQEAwIBBjAK
BggqhkjOPQQDAgNnADBkAjABM001FiLLs7Bx70Qvy8norf4dvHf0o3D5ZK/sjeu6
olh0hEPuPThpbaDY23PCfv4CMHQi1mO4TYp9Wn4PVaQ+NFcgjJN/Mq2V9wxJBdwy
vhJnoYvJ7XVDjUX6iFDPjOr9Vw==
-----END CERTIFICATE-----'''.encode()),
    'ca_pub': '''-----BEGIN PUBLIC KEY-----
MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAE28rT8hfTZ1UuTC1Ry8nNtrd29xR7B/S0
bVZ0VpMtrsXX5hqo4xWWglsc9g9wLEMmBFZp5CJ0VdJ2w9VpAQkJ7af1h0vA1SLe
470D8PdFXn8xnfZTeVGSjcB5QYUG/lcX
-----END PUBLIC KEY-----''',
    'server_key': b64encode('''-----BEGIN PRIVATE KEY-----
MIG2AgEAMBAGByqGSM49AgEGBSuBBAAiBIGeMIGbAgEBBDDsO4KohkPyc6RgCup3
eBUokioiX1k9DmC8L43vzDTEn4KPVZ0wRpd/BM0Vl/zjcfShZANiAAR9yklMOLox
dmxdW2KrnfgqQ1J4dqR2ipPwK0f4OnDgx7nXujqhfWAS4XvipD+G9NYUbsXvUxQh
T03NgsoSsA+Hxz4TseasHc+lkeWRjxLbsk6gxcj581WZSAdiSK4ICiY=
-----END PRIVATE KEY-----'''.encode()),
    'server_cert': b64encode('''-----BEGIN CERTIFICATE-----
MIICCDCCAY6gAwIBAgIRAOZVMlJSudlDtvzTDG4wL9EwCgYIKoZIzj0EAwIwEjEQ
MA4GA1UEAwwHcm9vdF9jYTAeFw0yMjA0MDUxNzUyMTRaFw0yNjA0MDUxNzUyMTRa
MBExDzANBgNVBAMMBnNlcnZlcjB2MBAGByqGSM49AgEGBSuBBAAiA2IABH3KSUw4
ujF2bF1bYqud+CpDUnh2pHaKk/ArR/g6cODHude6OqF9YBLhe+KkP4b01hRuxe9T
FCFPTc2CyhKwD4fHPhOx5qwdz6WR5ZGPEtuyTqDFyPnzVZlIB2JIrggKJqOBqDCB
pTAJBgNVHRMEAjAAMB0GA1UdDgQWBBSVrhk5/QGvQZn0Csakls7OIC2x5jBNBgNV
HSMERjBEgBTrcUB6RdEiu4gY265Jry8s7BopBKEWpBQwEjEQMA4GA1UEAwwHcm9v
dF9jYYIUPdrHjpTzdGmxOhOb6PLPgz1KNP8wHQYDVR0lBBYwFAYIKwYBBQUHAwEG
CCsGAQUFBwMCMAsGA1UdDwQEAwIFoDAKBggqhkjOPQQDAgNoADBlAjBoRHrBPGNA
x5ZH0MmzG9PQHva5R59UiMTv1mZrDvTe51Ihr1XuWhxU3uzcfyZgvZICMQCsYicQ
dhuYoD4409H47k+LCUNpOEZCeVmUrKyVeyIo/+Hs87Bo2T3+4yG3slkGEds=
-----END CERTIFICATE-----'''.encode()),
    'server_pub': '''-----BEGIN PUBLIC KEY-----
MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEfcpJTDi6MXZsXVtiq534KkNSeHakdoqT
8CtH+Dpw4Me517o6oX1gEuF74qQ/hvTWFG7F71MUIU9NzYLKErAPh8c+E7HmrB3P
pZHlkY8S27JOoMXI+fNVmUgHYkiuCAom
-----END PUBLIC KEY-----''',
}

class CertUtilsTests(unittest.TestCase):

    def test_CertRequest(self):
        cr = cert_utils.CertRequest()
        self.assertEqual(cr.entries, [])
        self.assertIsNone(cr.hostname_entry)

    @mock.patch.object(cert_utils, 'local_unit', return_value='unit/2')
    def test_CertRequest_add_entry(self, local_unit):
        cr = cert_utils.CertRequest()
        cr.add_entry('admin', 'admin.openstack.local', ['10.10.10.10'])
        self.assertEqual(
            cr.get_request(),
            {'cert_requests':
                '{"admin.openstack.local": {"sans": ["10.10.10.10"]}}',
             'unit_name': 'unit_2'})

    @mock.patch.object(cert_utils, 'local_unit', return_value='unit/2')
    @mock.patch.object(cert_utils, 'resolve_network_cidr')
    @mock.patch.object(cert_utils, 'get_vip_in_network')
    @mock.patch.object(cert_utils, 'get_hostname')
    @mock.patch.object(cert_utils, 'local_address')
    def test_CertRequest_add_hostname_cn(self, local_address, get_hostname,
                                         get_vip_in_network,
                                         resolve_network_cidr, local_unit):
        resolve_network_cidr.side_effect = lambda x: x
        get_vip_in_network.return_value = '10.1.2.100'
        local_address.return_value = '10.1.2.3'
        get_hostname.return_value = 'juju-unit-2'
        cr = cert_utils.CertRequest()
        cr.add_hostname_cn()
        self.assertEqual(
            cr.get_request(),
            {'cert_requests':
                '{"juju-unit-2": {"sans": ["10.1.2.100", "10.1.2.3"]}}',
             'unit_name': 'unit_2'})

    @mock.patch.object(cert_utils, 'local_unit', return_value='unit/2')
    @mock.patch.object(cert_utils, 'resolve_network_cidr')
    @mock.patch.object(cert_utils, 'get_vip_in_network')
    @mock.patch.object(cert_utils, 'get_hostname')
    @mock.patch.object(cert_utils, 'local_address')
    def test_CertRequest_add_hostname_cn_ip(self, local_address, get_hostname,
                                            get_vip_in_network,
                                            resolve_network_cidr, local_unit):
        resolve_network_cidr.side_effect = lambda x: x
        get_vip_in_network.return_value = '10.1.2.100'
        local_address.return_value = '10.1.2.3'
        get_hostname.return_value = 'juju-unit-2'
        cr = cert_utils.CertRequest()
        cr.add_hostname_cn()
        cr.add_hostname_cn_ip(['10.1.2.4'])
        self.assertEqual(
            cr.get_request(),
            {'cert_requests':
                ('{"juju-unit-2": {"sans": ["10.1.2.100", "10.1.2.3", '
                 '"10.1.2.4"]}}'),
             'unit_name': 'unit_2'})

    @mock.patch.object(cert_utils, 'get_certificate_sans')
    @mock.patch.object(cert_utils, 'local_unit', return_value='unit/2')
    @mock.patch.object(cert_utils, 'resolve_network_cidr')
    @mock.patch.object(cert_utils, 'get_vip_in_network')
    @mock.patch.object(cert_utils, 'network_get_primary_address')
    @mock.patch.object(cert_utils, 'resolve_address')
    @mock.patch.object(cert_utils, 'config')
    @mock.patch.object(cert_utils, 'get_hostname')
    @mock.patch.object(cert_utils, 'local_address')
    def test_get_certificate_request(self, local_address, get_hostname,
                                     config, resolve_address,
                                     network_get_primary_address,
                                     get_vip_in_network, resolve_network_cidr,
                                     local_unit, get_certificate_sans):
        local_address.return_value = '10.1.2.3'
        get_hostname.return_value = 'juju-unit-2'
        _config = {
            'os-internal-hostname': 'internal.openstack.local',
            'os-admin-hostname': 'admin.openstack.local',
            'os-public-hostname': 'public.openstack.local',
        }
        _resolve_address = {
            'int': '10.0.0.2',
            'internal': '10.0.0.2',
            'admin': '10.10.0.2',
            'public': '10.20.0.2',
        }
        _npa = {
            'internal': '10.0.0.3',
            'admin': '10.10.0.3',
            'public': '10.20.0.3',
        }
        _vips = {
            '10.0.0.0/16': '10.0.0.100',
            '10.10.0.0/16': '10.10.0.100',
            '10.20.0.0/16': '10.20.0.100',
        }
        _resolve_nets = {
            '10.0.0.3': '10.0.0.0/16',
            '10.10.0.3': '10.10.0.0/16',
            '10.20.0.3': '10.20.0.0/16',
        }
        get_certificate_sans.return_value = list(set(
            list(_resolve_address.values()) +
            list(_npa.values()) +
            list(_vips.values())))
        expect = {
            'admin.openstack.local': {
                'sans': ['10.10.0.100', '10.10.0.2', '10.10.0.3']},
            'internal.openstack.local': {
                'sans': ['10.0.0.100', '10.0.0.2', '10.0.0.3']},
            'juju-unit-2': {'sans': ['10.1.2.3']},
            'public.openstack.local': {
                'sans': ['10.20.0.100', '10.20.0.2', '10.20.0.3']}}
        self.maxDiff = None
        config.side_effect = lambda x: _config.get(x)
        get_vip_in_network.side_effect = lambda x: _vips.get(x)
        resolve_network_cidr.side_effect = lambda x: _resolve_nets.get(x)
        network_get_primary_address.side_effect = lambda x: _npa.get(x)
        resolve_address.side_effect = \
            lambda endpoint_type: _resolve_address[endpoint_type]
        output = json.loads(
            cert_utils.get_certificate_request()['cert_requests'])
        self.assertEqual(
            output,
            expect)
        get_certificate_sans.assert_called_once_with(
            bindings=['internal', 'admin', 'public'])

    @mock.patch.object(cert_utils, 'get_certificate_sans')
    @mock.patch.object(cert_utils, 'local_unit', return_value='unit/2')
    @mock.patch.object(cert_utils, 'resolve_network_cidr')
    @mock.patch.object(cert_utils, 'get_vip_in_network')
    @mock.patch.object(cert_utils, 'network_get_primary_address')
    @mock.patch.object(cert_utils, 'resolve_address')
    @mock.patch.object(cert_utils, 'config')
    @mock.patch.object(cert_utils, 'get_hostname')
    @mock.patch.object(cert_utils, 'local_address')
    def test_get_certificate_request_no_hostnames(
            self, local_address, get_hostname, config, resolve_address,
            network_get_primary_address, get_vip_in_network,
            resolve_network_cidr, local_unit, get_certificate_sans):
        local_address.return_value = '10.1.2.3'
        get_hostname.return_value = 'juju-unit-2'
        _config = {
            'os-admin-hostname': 'admin.openstack.local',
            'os-public-hostname': 'public.openstack.local',
        }
        _resolve_address = {
            'int': '10.0.0.2',
            'internal': '10.0.0.2',
            'admin': '10.10.0.2',
            'public': '10.20.0.2',
        }
        _npa = {
            'internal': '10.0.0.3',
            'admin': '10.10.0.3',
            'public': '10.20.0.3',
            'mybinding': '10.30.0.3',
        }
        _vips = {
            '10.0.0.0/16': '10.0.0.100',
            '10.10.0.0/16': '10.10.0.100',
            '10.20.0.0/16': '10.20.0.100',
        }
        _resolve_nets = {
            '10.0.0.3': '10.0.0.0/16',
            '10.10.0.3': '10.10.0.0/16',
            '10.20.0.3': '10.20.0.0/16',
        }
        get_certificate_sans.return_value = list(set(
            list(_resolve_address.values()) +
            list(_npa.values()) +
            list(_vips.values())))
        expect = {
            'admin.openstack.local': {
                'sans': ['10.10.0.100', '10.10.0.2', '10.10.0.3']},
            'juju-unit-2': {'sans': [
                '10.0.0.100', '10.0.0.2', '10.0.0.3', '10.1.2.3', '10.30.0.3']},
            'public.openstack.local': {
                'sans': ['10.20.0.100', '10.20.0.2', '10.20.0.3']}}
        self.maxDiff = None
        config.side_effect = lambda x: _config.get(x)
        get_vip_in_network.side_effect = lambda x: _vips.get(x)
        resolve_network_cidr.side_effect = lambda x: _resolve_nets.get(x)
        network_get_primary_address.side_effect = lambda x: _npa.get(x)
        resolve_address.side_effect = \
            lambda endpoint_type: _resolve_address[endpoint_type]
        output = json.loads(
            cert_utils.get_certificate_request(
                bindings=['mybinding'])['cert_requests'])
        self.assertEqual(
            output,
            expect)
        get_certificate_sans.assert_called_once_with(
            bindings=['mybinding', 'internal', 'admin', 'public'])

    @mock.patch.object(cert_utils, 'get_certificate_request')
    @mock.patch.object(cert_utils, 'local_address')
    @mock.patch.object(cert_utils.os, 'symlink')
    @mock.patch.object(cert_utils.os.path, 'isfile')
    @mock.patch.object(cert_utils, 'get_hostname')
    def test_create_ip_cert_links(self, get_hostname, isfile,
                                  symlink, local_address, get_cert_request):
        cert_request = {'cert_requests': {
            'admin.openstack.local': {
                'sans': ['10.10.0.100', '10.10.0.2', '10.10.0.3']},
            'internal.openstack.local': {
                'sans': ['10.0.0.100', '10.0.0.2', '10.0.0.3']},
            'juju-unit-2': {'sans': ['10.1.2.3']},
            'public.openstack.local': {
                'sans': ['10.20.0.100', '10.20.0.2', '10.20.0.3']}}}
        get_cert_request.return_value = cert_request
        _files = {
            '/etc/ssl/cert_juju-unit-2': True,
            '/etc/ssl/cert_10.1.2.3': False,
            '/etc/ssl/cert_admin.openstack.local': True,
            '/etc/ssl/cert_10.10.0.100': False,
            '/etc/ssl/cert_10.10.0.2': False,
            '/etc/ssl/cert_10.10.0.3': False,
            '/etc/ssl/cert_internal.openstack.local': True,
            '/etc/ssl/cert_10.0.0.100': False,
            '/etc/ssl/cert_10.0.0.2': False,
            '/etc/ssl/cert_10.0.0.3': False,
            '/etc/ssl/cert_public.openstack.local': True,
            '/etc/ssl/cert_10.20.0.100': False,
            '/etc/ssl/cert_10.20.0.2': False,
            '/etc/ssl/cert_10.20.0.3': False,
            '/etc/ssl/cert_funky-name': False,
        }
        isfile.side_effect = lambda x: _files[x]
        expected = [
            mock.call('/etc/ssl/cert_admin.openstack.local', '/etc/ssl/cert_10.10.0.100'),
            mock.call('/etc/ssl/key_admin.openstack.local', '/etc/ssl/key_10.10.0.100'),
            mock.call('/etc/ssl/cert_admin.openstack.local', '/etc/ssl/cert_10.10.0.2'),
            mock.call('/etc/ssl/key_admin.openstack.local', '/etc/ssl/key_10.10.0.2'),
            mock.call('/etc/ssl/cert_admin.openstack.local', '/etc/ssl/cert_10.10.0.3'),
            mock.call('/etc/ssl/key_admin.openstack.local', '/etc/ssl/key_10.10.0.3'),
            mock.call('/etc/ssl/cert_internal.openstack.local', '/etc/ssl/cert_10.0.0.100'),
            mock.call('/etc/ssl/key_internal.openstack.local', '/etc/ssl/key_10.0.0.100'),
            mock.call('/etc/ssl/cert_internal.openstack.local', '/etc/ssl/cert_10.0.0.2'),
            mock.call('/etc/ssl/key_internal.openstack.local', '/etc/ssl/key_10.0.0.2'),
            mock.call('/etc/ssl/cert_internal.openstack.local', '/etc/ssl/cert_10.0.0.3'),
            mock.call('/etc/ssl/key_internal.openstack.local', '/etc/ssl/key_10.0.0.3'),
            mock.call('/etc/ssl/cert_juju-unit-2', '/etc/ssl/cert_10.1.2.3'),
            mock.call('/etc/ssl/key_juju-unit-2', '/etc/ssl/key_10.1.2.3'),
            mock.call('/etc/ssl/cert_public.openstack.local', '/etc/ssl/cert_10.20.0.100'),
            mock.call('/etc/ssl/key_public.openstack.local', '/etc/ssl/key_10.20.0.100'),
            mock.call('/etc/ssl/cert_public.openstack.local', '/etc/ssl/cert_10.20.0.2'),
            mock.call('/etc/ssl/key_public.openstack.local', '/etc/ssl/key_10.20.0.2'),
            mock.call('/etc/ssl/cert_public.openstack.local', '/etc/ssl/cert_10.20.0.3'),
            mock.call('/etc/ssl/key_public.openstack.local', '/etc/ssl/key_10.20.0.3')]
        cert_utils.create_ip_cert_links('/etc/ssl')
        symlink.assert_has_calls(expected, any_order=True)
        # Customer hostname
        symlink.reset_mock()
        get_hostname.return_value = 'juju-unit-2'
        cert_utils.create_ip_cert_links(
            '/etc/ssl',
            custom_hostname_link='funky-name')
        expected.extend([
            mock.call('/etc/ssl/cert_juju-unit-2', '/etc/ssl/cert_funky-name'),
            mock.call('/etc/ssl/key_juju-unit-2', '/etc/ssl/key_funky-name'),
        ])
        symlink.assert_has_calls(expected, any_order=True)
        get_cert_request.assert_called_with(
            json_encode=False, bindings=['internal', 'admin', 'public'])

    @mock.patch.object(cert_utils, 'get_certificate_request')
    @mock.patch.object(cert_utils, 'local_address')
    @mock.patch.object(cert_utils.os, 'symlink')
    @mock.patch.object(cert_utils.os.path, 'isfile')
    @mock.patch.object(cert_utils, 'get_hostname')
    def test_create_ip_cert_links_bindings(
            self, get_hostname, isfile, symlink, local_address, get_cert_request):
        cert_request = {'cert_requests': {
            'admin.openstack.local': {
                'sans': ['10.10.0.100', '10.10.0.2', '10.10.0.3']},
            'internal.openstack.local': {
                'sans': ['10.0.0.100', '10.0.0.2', '10.0.0.3']},
            'juju-unit-2': {'sans': ['10.1.2.3']},
            'public.openstack.local': {
                'sans': ['10.20.0.100', '10.20.0.2', '10.20.0.3']}}}
        get_cert_request.return_value = cert_request
        _files = {
            '/etc/ssl/cert_juju-unit-2': True,
            '/etc/ssl/cert_10.1.2.3': False,
            '/etc/ssl/cert_admin.openstack.local': True,
            '/etc/ssl/cert_10.10.0.100': False,
            '/etc/ssl/cert_10.10.0.2': False,
            '/etc/ssl/cert_10.10.0.3': False,
            '/etc/ssl/cert_internal.openstack.local': True,
            '/etc/ssl/cert_10.0.0.100': False,
            '/etc/ssl/cert_10.0.0.2': False,
            '/etc/ssl/cert_10.0.0.3': False,
            '/etc/ssl/cert_public.openstack.local': True,
            '/etc/ssl/cert_10.20.0.100': False,
            '/etc/ssl/cert_10.20.0.2': False,
            '/etc/ssl/cert_10.20.0.3': False,
            '/etc/ssl/cert_funky-name': False,
        }
        isfile.side_effect = lambda x: _files[x]
        expected = [
            mock.call('/etc/ssl/cert_admin.openstack.local', '/etc/ssl/cert_10.10.0.100'),
            mock.call('/etc/ssl/key_admin.openstack.local', '/etc/ssl/key_10.10.0.100'),
            mock.call('/etc/ssl/cert_admin.openstack.local', '/etc/ssl/cert_10.10.0.2'),
            mock.call('/etc/ssl/key_admin.openstack.local', '/etc/ssl/key_10.10.0.2'),
            mock.call('/etc/ssl/cert_admin.openstack.local', '/etc/ssl/cert_10.10.0.3'),
            mock.call('/etc/ssl/key_admin.openstack.local', '/etc/ssl/key_10.10.0.3'),
            mock.call('/etc/ssl/cert_internal.openstack.local', '/etc/ssl/cert_10.0.0.100'),
            mock.call('/etc/ssl/key_internal.openstack.local', '/etc/ssl/key_10.0.0.100'),
            mock.call('/etc/ssl/cert_internal.openstack.local', '/etc/ssl/cert_10.0.0.2'),
            mock.call('/etc/ssl/key_internal.openstack.local', '/etc/ssl/key_10.0.0.2'),
            mock.call('/etc/ssl/cert_internal.openstack.local', '/etc/ssl/cert_10.0.0.3'),
            mock.call('/etc/ssl/key_internal.openstack.local', '/etc/ssl/key_10.0.0.3'),
            mock.call('/etc/ssl/cert_juju-unit-2', '/etc/ssl/cert_10.1.2.3'),
            mock.call('/etc/ssl/key_juju-unit-2', '/etc/ssl/key_10.1.2.3'),
            mock.call('/etc/ssl/cert_public.openstack.local', '/etc/ssl/cert_10.20.0.100'),
            mock.call('/etc/ssl/key_public.openstack.local', '/etc/ssl/key_10.20.0.100'),
            mock.call('/etc/ssl/cert_public.openstack.local', '/etc/ssl/cert_10.20.0.2'),
            mock.call('/etc/ssl/key_public.openstack.local', '/etc/ssl/key_10.20.0.2'),
            mock.call('/etc/ssl/cert_public.openstack.local', '/etc/ssl/cert_10.20.0.3'),
            mock.call('/etc/ssl/key_public.openstack.local', '/etc/ssl/key_10.20.0.3')]
        cert_utils.create_ip_cert_links('/etc/ssl', bindings=['mybindings'])
        symlink.assert_has_calls(expected, any_order=True)
        # Customer hostname
        symlink.reset_mock()
        get_hostname.return_value = 'juju-unit-2'
        cert_utils.create_ip_cert_links(
            '/etc/ssl',
            custom_hostname_link='funky-name', bindings=['mybinding'])
        expected.extend([
            mock.call('/etc/ssl/cert_juju-unit-2', '/etc/ssl/cert_funky-name'),
            mock.call('/etc/ssl/key_juju-unit-2', '/etc/ssl/key_funky-name'),
        ])
        symlink.assert_has_calls(expected, any_order=True)
        get_cert_request.assert_called_with(
            json_encode=False, bindings=['mybinding', 'internal', 'admin', 'public'])

    @mock.patch.object(cert_utils, 'write_file')
    def test_install_certs(self, write_file):
        certs = {
            'admin.openstack.local': {
                'cert': 'ADMINCERT',
                'key': 'ADMINKEY'}}
        cert_utils.install_certs('/etc/ssl', certs, chain='CHAIN')
        expected = [
            mock.call(
                path='/etc/ssl/cert_admin.openstack.local',
                content='ADMINCERT\nCHAIN',
                owner='root', group='root',
                perms=0o640),
            mock.call(
                path='/etc/ssl/key_admin.openstack.local',
                content='ADMINKEY',
                owner='root', group='root',
                perms=0o640),
        ]
        write_file.assert_has_calls(expected)

    @mock.patch.object(cert_utils, 'write_file')
    def test_install_certs_ca(self, write_file):
        certs = {
            'admin.openstack.local': {
                'cert': 'ADMINCERT',
                'key': 'ADMINKEY'}}
        ca = 'MYCA'
        cert_utils.install_certs('/etc/ssl', certs, ca)
        expected = [
            mock.call(
                path='/etc/ssl/cert_admin.openstack.local',
                content='ADMINCERT\nMYCA',
                owner='root', group='root',
                perms=0o640),
            mock.call(
                path='/etc/ssl/key_admin.openstack.local',
                content='ADMINKEY',
                owner='root', group='root',
                perms=0o640),
        ]
        write_file.assert_has_calls(expected)

    @mock.patch.object(cert_utils, '_manage_ca_certs')
    @mock.patch.object(cert_utils, 'remote_service_name')
    @mock.patch.object(cert_utils, 'local_unit')
    @mock.patch.object(cert_utils, 'create_ip_cert_links')
    @mock.patch.object(cert_utils, 'install_certs')
    @mock.patch.object(cert_utils, 'install_ca_cert')
    @mock.patch.object(cert_utils, 'mkdir')
    @mock.patch.object(cert_utils, 'relation_get')
    def test_process_certificates(self, relation_get, mkdir, install_ca_cert,
                                  install_certs, create_ip_cert_links,
                                  local_unit, remote_service_name,
                                  _manage_ca_certs):
        remote_service_name.return_value = 'vault'
        local_unit.return_value = 'devnull/2'
        certs = {
            'admin.openstack.local': {
                'cert': 'ADMINCERT',
                'key': 'ADMINKEY'}}
        _relation_info = {
            'keystone_2.processed_requests': json.dumps(certs),
            'chain': 'MYCHAIN',
            'ca': 'ROOTCA',
        }
        relation_get.return_value = _relation_info
        self.assertFalse(cert_utils.process_certificates(
            'myservice',
            'certificates:2',
            'vault/0',
            custom_hostname_link='funky-name'))
        local_unit.return_value = 'keystone/2'
        self.assertTrue(cert_utils.process_certificates(
            'myservice',
            'certificates:2',
            'vault/0',
            custom_hostname_link='funky-name'))
        _manage_ca_certs.assert_called_once_with(
            'ROOTCA', 'certificates:2')
        install_certs.assert_called_once_with(
            '/etc/apache2/ssl/myservice',
            {'admin.openstack.local': {
                'key': 'ADMINKEY', 'cert': 'ADMINCERT'}},
            'MYCHAIN', user='root', group='root')
        create_ip_cert_links.assert_called_once_with(
            '/etc/apache2/ssl/myservice',
            custom_hostname_link='funky-name',
            bindings=['internal', 'admin', 'public'])

    @mock.patch.object(cert_utils, '_manage_ca_certs')
    @mock.patch.object(cert_utils, 'remote_service_name')
    @mock.patch.object(cert_utils, 'local_unit')
    @mock.patch.object(cert_utils, 'create_ip_cert_links')
    @mock.patch.object(cert_utils, 'install_certs')
    @mock.patch.object(cert_utils, 'install_ca_cert')
    @mock.patch.object(cert_utils, 'mkdir')
    @mock.patch.object(cert_utils, 'relation_get')
    def test_process_certificates_bindings(
            self, relation_get, mkdir, install_ca_cert,
            install_certs, create_ip_cert_links,
            local_unit, remote_service_name, _manage_ca_certs):
        remote_service_name.return_value = 'vault'
        local_unit.return_value = 'devnull/2'
        certs = {
            'admin.openstack.local': {
                'cert': 'ADMINCERT',
                'key': 'ADMINKEY'}}
        _relation_info = {
            'keystone_2.processed_requests': json.dumps(certs),
            'chain': 'MYCHAIN',
            'ca': 'ROOTCA',
        }
        relation_get.return_value = _relation_info
        self.assertFalse(cert_utils.process_certificates(
            'myservice',
            'certificates:2',
            'vault/0',
            custom_hostname_link='funky-name'))
        local_unit.return_value = 'keystone/2'
        self.assertTrue(cert_utils.process_certificates(
            'myservice',
            'certificates:2',
            'vault/0',
            custom_hostname_link='funky-name',
            bindings=['mybinding']))
        _manage_ca_certs.assert_called_once_with(
            'ROOTCA', 'certificates:2')
        install_certs.assert_called_once_with(
            '/etc/apache2/ssl/myservice',
            {'admin.openstack.local': {
                'key': 'ADMINKEY', 'cert': 'ADMINCERT'}},
            'MYCHAIN', user='root', group='root')
        create_ip_cert_links.assert_called_once_with(
            '/etc/apache2/ssl/myservice',
            custom_hostname_link='funky-name',
            bindings=['mybinding', 'internal', 'admin', 'public'])

    @mock.patch.object(cert_utils, 'remote_service_name')
    @mock.patch.object(cert_utils, 'relation_ids')
    def test_get_cert_relation_ca_name(self, relation_ids, remote_service_name):
        remote_service_name.return_value = 'vault'

        # Test with argument:
        self.assertEqual(cert_utils.get_cert_relation_ca_name('certificates:1'),
                         'vault_juju_ca_cert')
        remote_service_name.assert_called_once_with(relid='certificates:1')
        remote_service_name.reset_mock()

        # Test without argument:
        relation_ids.return_value = ['certificates:2']
        self.assertEqual(cert_utils.get_cert_relation_ca_name(),
                         'vault_juju_ca_cert')
        remote_service_name.assert_called_once_with(relid='certificates:2')
        remote_service_name.reset_mock()

        # Test without argument nor 'certificates' relation:
        relation_ids.return_value = []
        self.assertEqual(cert_utils.get_cert_relation_ca_name(), '')
        remote_service_name.assert_not_called()

    @mock.patch.object(cert_utils, 'log')
    @mock.patch.object(cert_utils, 'remote_service_name')
    @mock.patch.object(cert_utils.os, 'remove')
    @mock.patch.object(cert_utils.os.path, 'exists')
    @mock.patch.object(cert_utils, 'config')
    @mock.patch.object(cert_utils, 'install_ca_cert')
    def test__manage_ca_certs(self, install_ca_cert, config, os_exists,
                              os_remove, remote_service_name, _log):
        remote_service_name.return_value = 'vault'
        _config = {}
        config.side_effect = lambda x: _config.get(x)
        os_exists.return_value = False
        cert_utils._manage_ca_certs(b64decode(rsa_certs['ca_cert']).decode(), 'certificates:2')
        install_ca_cert.assert_called_once_with(
            b64decode(rsa_certs['ca_cert']),
            name='vault_juju_ca_cert')
        self.assertFalse(os_remove.called)

        # Test old cert removed.
        install_ca_cert.reset_mock()
        os_exists.reset_mock()

        os_exists.return_value = True
        cert_utils._manage_ca_certs(b64decode(rsa_certs['ca_cert']).decode(), 'certificates:2')
        install_ca_cert.assert_called_once_with(
            b64decode(rsa_certs['ca_cert']),
            name='vault_juju_ca_cert')
        os_remove.assert_called_once_with(
            '/usr/local/share/ca-certificates/keystone_juju_ca_cert.crt')

        # Test cert is installed from config
        _config['ssl_ca'] = rsa_certs['ca_cert']
        install_ca_cert.reset_mock()
        os_remove.reset_mock()
        os_exists.reset_mock()
        os_exists.return_value = True
        cert_utils._manage_ca_certs(b64decode(rsa_certs['ca_cert']).decode(), 'certificates:2')
        expected = [
            mock.call(b64decode(rsa_certs['ca_cert']), name='keystone_juju_ca_cert'),
            mock.call(b64decode(rsa_certs['ca_cert']), name='vault_juju_ca_cert')]
        install_ca_cert.assert_has_calls(expected)
        self.assertFalse(os_remove.called)

    @mock.patch.object(cert_utils, 'local_unit')
    @mock.patch.object(cert_utils, 'related_units')
    @mock.patch.object(cert_utils, 'relation_ids')
    @mock.patch.object(cert_utils, 'relation_get')
    def test_get_requests_for_local_unit(self, relation_get, relation_ids,
                                         related_units, local_unit):
        local_unit.return_value = 'rabbitmq-server/2'
        relation_ids.return_value = ['certificates:12']
        related_units.return_value = ['vault/0']
        certs = {
            'juju-cd4bb3-5.lxd': {
                'cert': 'BASECERT',
                'key': 'BASEKEY'},
            'juju-cd4bb3-5.internal': {
                'cert': 'INTERNALCERT',
                'key': 'INTERNALKEY'}}
        _relation_info = {
            'rabbitmq-server_2.processed_requests': json.dumps(certs),
            'chain': 'MYCHAIN',
            'ca': 'ROOTCA',
        }
        relation_get.return_value = _relation_info
        self.assertEqual(
            cert_utils.get_requests_for_local_unit(),
            [{
                'ca': 'ROOTCA',
                'certs': {
                    'juju-cd4bb3-5.lxd': {
                        'cert': 'BASECERT',
                        'key': 'BASEKEY'},
                    'juju-cd4bb3-5.internal': {
                        'cert': 'INTERNALCERT',
                        'key': 'INTERNALKEY'}},
                'chain': 'MYCHAIN'}]
        )

    @mock.patch.object(cert_utils, 'get_requests_for_local_unit')
    def test_get_bundle_for_cn(self, get_requests_for_local_unit):
        get_requests_for_local_unit.return_value = [{
            'ca': 'ROOTCA',
            'certs': {
                'juju-cd4bb3-5.lxd': {
                    'cert': 'BASECERT',
                    'key': 'BASEKEY'},
                'juju-cd4bb3-5.internal': {
                    'cert': 'INTERNALCERT',
                    'key': 'INTERNALKEY'}},
            'chain': 'MYCHAIN'}]
        self.assertEqual(
            cert_utils.get_bundle_for_cn('juju-cd4bb3-5.internal'),
            {
                'ca': 'ROOTCA',
                'cert': 'INTERNALCERT',
                'chain': 'MYCHAIN',
                'key': 'INTERNALKEY'})

    @mock.patch.object(cert_utils, 'local_unit', return_value='unit/2')
    @mock.patch.object(cert_utils, 'resolve_network_cidr')
    @mock.patch.object(cert_utils, 'get_vip_in_network')
    @mock.patch.object(cert_utils, 'get_relation_ip')
    @mock.patch.object(cert_utils, 'resolve_address')
    @mock.patch.object(cert_utils, 'config')
    @mock.patch.object(cert_utils, 'get_hostname')
    @mock.patch.object(cert_utils, 'local_address')
    def test_get_certificate_sans(self, local_address, get_hostname,
                                  config, resolve_address,
                                  get_relation_ip,
                                  get_vip_in_network, resolve_network_cidr,
                                  local_unit):
        local_address.return_value = '10.1.2.3'
        get_hostname.return_value = 'juju-unit-2'
        _config = {
            'os-internal-hostname': 'internal.openstack.local',
            'os-admin-hostname': 'admin.openstack.local',
            'os-public-hostname': 'public.openstack.local',
        }
        _resolve_address = {
            'int': '10.0.0.2',
            'internal': '10.0.0.2',
            'admin': '10.10.0.2',
            'public': '10.20.0.2',
        }
        _npa = {
            'internal': '10.0.0.3',
            'admin': '10.10.0.3',
            'public': '10.20.0.3',
        }
        _vips = {
            '10.0.0.0/16': '10.0.0.100',
            '10.10.0.0/16': '10.10.0.100',
            '10.20.0.0/16': '10.20.0.100',
        }
        _resolve_nets = {
            '10.0.0.3': '10.0.0.0/16',
            '10.10.0.3': '10.10.0.0/16',
            '10.20.0.3': '10.20.0.0/16',
        }
        expect = list(set([
            '10.10.0.100', '10.10.0.2', '10.10.0.3',
            '10.0.0.100', '10.0.0.2', '10.0.0.3',
            '10.1.2.3',
            '10.20.0.100', '10.20.0.2', '10.20.0.3']))
        self.maxDiff = None
        config.side_effect = lambda x: _config.get(x)
        get_vip_in_network.side_effect = lambda x: _vips.get(x)
        resolve_network_cidr.side_effect = lambda x: _resolve_nets.get(x)
        get_relation_ip.side_effect = lambda x, cidr_network: _npa.get(x)
        resolve_address.side_effect = \
            lambda endpoint_type: _resolve_address[endpoint_type]
        expected_get_relation_ip_calls = [
            mock.call('internal', cidr_network=None),
            mock.call('admin', cidr_network=None),
            mock.call('public', cidr_network=None)]
        self.assertEqual(cert_utils.get_certificate_sans().sort(),
                         expect.sort())
        get_relation_ip.assert_has_calls(
            expected_get_relation_ip_calls, any_order=True)

    @mock.patch.object(cert_utils, 'local_unit', return_value='unit/2')
    @mock.patch.object(cert_utils, 'resolve_network_cidr')
    @mock.patch.object(cert_utils, 'get_vip_in_network')
    @mock.patch.object(cert_utils, 'get_relation_ip')
    @mock.patch.object(cert_utils, 'resolve_address')
    @mock.patch.object(cert_utils, 'config')
    @mock.patch.object(cert_utils, 'get_hostname')
    @mock.patch.object(cert_utils, 'local_address')
    def test_get_certificate_sans_bindings(
            self, local_address, get_hostname, config, resolve_address,
            get_relation_ip, get_vip_in_network, resolve_network_cidr, local_unit):
        local_address.return_value = '10.1.2.3'
        get_hostname.return_value = 'juju-unit-2'
        _config = {
            'os-internal-hostname': 'internal.openstack.local',
            'os-admin-hostname': 'admin.openstack.local',
            'os-public-hostname': 'public.openstack.local',
        }
        _resolve_address = {
            'int': '10.0.0.2',
            'internal': '10.0.0.2',
            'admin': '10.10.0.2',
            'public': '10.20.0.2',
        }
        _npa = {
            'internal': '10.0.0.3',
            'admin': '10.10.0.3',
            'public': '10.20.0.3',
        }
        _vips = {
            '10.0.0.0/16': '10.0.0.100',
            '10.10.0.0/16': '10.10.0.100',
            '10.20.0.0/16': '10.20.0.100',
        }
        _resolve_nets = {
            '10.0.0.3': '10.0.0.0/16',
            '10.10.0.3': '10.10.0.0/16',
            '10.20.0.3': '10.20.0.0/16',
        }
        expect = list(set([
            '10.10.0.100', '10.10.0.2', '10.10.0.3',
            '10.0.0.100', '10.0.0.2', '10.0.0.3',
            '10.1.2.3',
            '10.20.0.100', '10.20.0.2', '10.20.0.3']))
        self.maxDiff = None
        config.side_effect = lambda x: _config.get(x)
        get_vip_in_network.side_effect = lambda x: _vips.get(x)
        resolve_network_cidr.side_effect = lambda x: _resolve_nets.get(x)
        get_relation_ip.side_effect = lambda x, cidr_network: _npa.get(x)
        resolve_address.side_effect = \
            lambda endpoint_type: _resolve_address[endpoint_type]
        expected_get_relation_ip_calls = [
            mock.call('internal', cidr_network=None),
            mock.call('admin', cidr_network=None),
            mock.call('public', cidr_network=None),
            mock.call('mybinding', cidr_network=None)]
        self.assertEqual(
            cert_utils.get_certificate_sans(bindings=['mybinding']).sort(),
            expect.sort())
        get_relation_ip.assert_has_calls(
            expected_get_relation_ip_calls, any_order=True)

    def test__x509_normalize_input(self):
        self.assertEqual(
            cert_utils._x509_normalize_input('str'), 'str'.encode())
        self.assertEqual(
            cert_utils._x509_normalize_input(b'bytes'), 'bytes'.encode())
        self.assertEqual(
            cert_utils._x509_normalize_input(None), bytes())

    def test_x509_get_pubkey(self):
        self.assertEqual(
            cert_utils.x509_get_pubkey(b64decode(rsa_certs['server_cert'])),
            rsa_certs['server_pub'])

    def test_x509_validate_cert_chain(self):
        self.assertTrue(cert_utils.x509_validate_cert_chain(
            b64decode(rsa_certs['server_cert']),
            ssl_ca=b64decode(rsa_certs['ca_cert'])))
        self.assertFalse(cert_utils.x509_validate_cert_chain(
            b64decode(rsa_certs['server_cert']),
            ssl_ca=b64decode(ec_certs['ca_cert'])))

    def test_x509_validate_cert_parity(self):
        self.assertFalse(cert_utils.x509_validate_cert_parity(
            b64decode(rsa_certs['server_cert']),
            b64decode(rsa_certs['ca_key'])))
        self.assertFalse(cert_utils.x509_validate_cert_parity(
            bytes(), b64decode(rsa_certs['ca_key'])))
        self.assertFalse(cert_utils.x509_validate_cert_parity(
            b64decode(rsa_certs['ca_cert']), bytes()))
        self.assertTrue(cert_utils.x509_validate_cert_parity(
            b64decode(rsa_certs['ca_cert']), b64decode(rsa_certs['ca_key'])))

    def test_x509_validate_cert(self):
        self.assertFalse(cert_utils.x509_validate_cert(
                            b64decode(rsa_certs['server_cert']),
                            ssl_key=b64decode(rsa_certs['ca_key']),
                            validate_chain=False))
        self.assertTrue(cert_utils.x509_validate_cert(
                            b64decode(rsa_certs['server_cert']),
                            ssl_key=b64decode(rsa_certs['server_key']),
                            validate_chain=False))
        self.assertFalse(cert_utils.x509_validate_cert(
                            b64decode(rsa_certs['server_cert']),
                            ssl_key=b64decode(rsa_certs['server_key']),
                            ssl_ca=b64decode(ec_certs['ca_cert']),
                            validate_chain=True))
        self.assertFalse(cert_utils.x509_validate_cert(
                            b64decode(rsa_certs['server_cert']),
                            ssl_key=b64decode(rsa_certs['server_key']),
                            validate_chain=True))
        self.assertFalse(cert_utils.x509_validate_cert(
                            b64decode(rsa_certs['server_cert']),
                            ssl_key=b64decode(ec_certs['server_key']),
                            ssl_ca=b64decode(rsa_certs['ca_cert']),
                            validate_chain=True))
        self.assertTrue(cert_utils.x509_validate_cert(
                            b64decode(rsa_certs['server_cert']),
                            ssl_key=b64decode(rsa_certs['server_key']),
                            ssl_ca=b64decode(rsa_certs['ca_cert']),
                            validate_chain=True))
