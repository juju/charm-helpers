from base64 import b64encode

from mock import patch, call

from testtools import TestCase
from tests.helpers import patch_open, FakeRelation

import charmhelpers.contrib.hahelpers.apache as apache_utils

rsa_certs = {  # check for intermediate CAs?
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
    'ca_pub': '''-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAnhnAUJC+ZLlkmFZq1adb
FgzJelPtr/M5T/7ao2kbVQEaocMSTR9FLbhgfDvbNVQKB/YcsdT+Vb0CJTZ/0pQA
hF51y9TqJDII/++q+7PGwBRBv4O4I4FI/120vKu7FTu9oKRBVxsIRolyn6mpvxml
EcZXsfsuyoNrdKUdG1rOEbyRJRZY8En67UkRLnMajPod4bguZc8qktt/R0kD18U8
V9k1ROXGM8XTlgPyAmdkguo9heicZB+moXgCGveyxktIM1Lm2v2uM7MiM/Hln4cR
cxnI63saAhbQcdoRoP9YyUQ3lV5yXyrQd1vhmqSrn7lHbR8OJNAy983smPfcIv2r
8QIDAQAB
-----END PUBLIC KEY-----'''.encode(),
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

cert = '''-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAMO1fWOu8ntUMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
BAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBX
aWRnaXRzIFB0eSBMdGQwHhcNMTQwNDIyMTUzNDA0WhcNMjQwNDE5MTUzNDA0WjBF
MQswCQYDVQQGEwJBVTETMBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50
ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIB
CgKCAQEAuk6dmZnMvVxykNidNjbIwXM3ShhMpwCvUmWwpybFAIqhtNTuGJF9Ikp5
kzB+ThQV1onK8O8YarNGQx+MOISEnlJ5npj3Atp33pKGHRn69lHKGVfJvRbN4A90
1hTueYsELzfPV2YWm4c6nQiXRT6Cy0yaw/DE8fBTHzAiE9+/XGPsjn5VPv8H6Wa1
f/d5FblE+RtHP6YpRo9Jh3XAn3iC9fVr8rblS4rk7ev8LfH/yIG2wRVOEPC6lYfu
MEIwPpxKV0c3Z6lqtMOgC5dgzWjrbItnQfB0JaIzSFMMxDhNCJocQRJDQ+0jmj+K
rMGB1QRZlVLZxx0xnv38G0GyfFMv8QIDAQABo1AwTjAdBgNVHQ4EFgQUcxEj7X26
poFDa0lw40aAKIqyNp0wHwYDVR0jBBgwFoAUcxEj7X26poFDa0lw40aAKIqyNp0w
DAYDVR0TBAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAQe6RUCqTYf0Ns8fKfAEb
QSxZKqCst02oC0F3Gm0opWiUetxZqmAYTAjztmlRFIw7hgF/P95SY1ujGLZmiAlU
poOTjQ/i7MvjkXPVCo92izwXi65qRmJGbjduIirOAYtBmBmm3qS9BmoDlLQMVNYn
bwFImc9ar0h+o3/VH1hry+2vEVikXiKK5uKZI6B7ejNYfAWydq6ilzfKIh75W852
OSbKt3NB/BTZZUdCvK6+B+MoeuzQHDO0/QKBEBfaKFeJki3mdyzFlNbYio1z00rM
E2zl3kh9gkZnMuV1uzHdfKJbtTcNn4hCls5x7T21jn4joADHaVez8FloykBUABu3
qw==
-----END CERTIFICATE-----'''.encode()

IDENTITY_NEW_STYLE_CERTS = {
    'identity-service:0': {
        'keystone/0': {
            'ssl_cert_test-cn': rsa_certs['server_cert'],
            'ssl_key_test-cn': rsa_certs['server_key'],
        }
    }
}

IDENTITY_OLD_STYLE_CERTS = {
    'identity-service:0': {
        'keystone/0': {
            'ssl_cert': rsa_certs['server_cert'],
            'ssl_key': rsa_certs['server_key'],
        }
    }
}


class ApacheUtilsTests(TestCase):
    def setUp(self):
        super(ApacheUtilsTests, self).setUp()
        [self._patch(m) for m in [
            'log',
            'config_get',
            'relation_get',
            'relation_ids',
            'relation_list',
            'host',
        ]]

    def _patch(self, method):
        _m = patch.object(apache_utils, method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        setattr(self, method, mock)

    def test_get_cert_from_config(self):
        '''Ensure cert and key from charm config override relation'''
        self.config_get.side_effect = [
            rsa_certs['ca_cert'],  # config_get('ssl_cert')
            rsa_certs['ca_key'],  # config_get('ssl_key')
        ]
        result = apache_utils.get_cert('test-cn')
        self.assertEquals((rsa_certs['ca_cert'], rsa_certs['ca_key']), result)

    def test_get_ca_cert_from_config(self):
        self.config_get.return_value = rsa_certs['ca_cert']
        self.assertEquals(rsa_certs['ca_cert'], apache_utils.get_ca_cert())

    def test_get_cert_from_relation(self):
        self.config_get.return_value = None
        rel = FakeRelation(IDENTITY_NEW_STYLE_CERTS)
        self.relation_ids.side_effect = rel.relation_ids
        self.relation_list.side_effect = rel.relation_units
        self.relation_get.side_effect = rel.get
        result = apache_utils.get_cert('test-cn')
        self.assertEquals((rsa_certs['server_cert'], rsa_certs['server_key']),
                          result)

    def test_get_cert_from_relation_deprecated(self):
        self.config_get.return_value = None
        rel = FakeRelation(IDENTITY_OLD_STYLE_CERTS)
        self.relation_ids.side_effect = rel.relation_ids
        self.relation_list.side_effect = rel.relation_units
        self.relation_get.side_effect = rel.get
        result = apache_utils.get_cert()
        self.assertEquals((rsa_certs['server_cert'], rsa_certs['server_key']),
                          result)

    def test_get_ca_cert_from_relation(self):
        self.config_get.return_value = None
        self.relation_ids.side_effect = [['identity-service:0'],
                                         ['identity-credentials:1']]
        self.relation_list.return_value = 'keystone/0'
        self.relation_get.side_effect = [
            rsa_certs['ca_cert'],
        ]
        result = apache_utils.get_ca_cert()
        self.relation_ids.assert_has_calls([call('identity-service'),
                                            call('identity-credentials')])
        self.assertEquals(rsa_certs['ca_cert'], result)

    @patch.object(apache_utils.os.path, 'isfile')
    def test_retrieve_ca_cert(self, _isfile):
        _isfile.return_value = True
        with patch_open() as (_open, _file):
            _file.read.return_value = cert
            self.assertEqual(
                apache_utils.retrieve_ca_cert('mycertfile'),
                cert)
            _open.assert_called_once_with('mycertfile', 'rb')

    @patch.object(apache_utils.os.path, 'isfile')
    def test_retrieve_ca_cert_no_file(self, _isfile):
        _isfile.return_value = False
        with patch_open() as (_open, _file):
            self.assertEqual(
                apache_utils.retrieve_ca_cert('mycertfile'),
                None)
            self.assertFalse(_open.called)
