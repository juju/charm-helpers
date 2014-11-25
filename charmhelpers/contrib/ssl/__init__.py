import subprocess
from charmhelpers.core import hookenv


def generate_selfsigned(keyfile, certfile, keysize="1024", config=None, subject=None, cn=None):
    """Generate selfsigned SSL keypair

    You must provide one of the 3 optional arguments:
    config, subject or cn
    If more than one is provided the leftmost will be used

    Arguments:
    keyfile -- (required) full path to the keyfile to be created
    certfile -- (required) full path to the certfile to be created
    keysize -- (optional) SSL key length
    config -- (optional) openssl configuration file
    subject -- (optional) dictionary with SSL subject variables
    cn -- (optional) cerfificate common name

    Required keys in subject dict:
    cn -- Common name (eq. FQDN)

    Optional keys in subject dict
    country -- Country Name (2 letter code)
    state -- State or Province Name (full name)
    locality -- Locality Name (eg, city)
    organization -- Organization Name (eg, company)
    organizational_unit -- Organizational Unit Name (eg, section)
    email -- Email Address
    """

    cmd = []
    if config:
        cmd = ["/usr/bin/openssl", "req", "-new", "-newkey",
               "rsa:{}".format(keysize), "-days", "365", "-nodes", "-x509",
               "-keyout", keyfile,
               "-out", certfile, "-config", config]
    elif subject:
        ssl_subject = ""
        if "country" in subject:
            ssl_subject = ssl_subject + "/C={}".format(subject["country"])
        if "state" in subject:
            ssl_subject = ssl_subject + "/ST={}".format(subject["state"])
        if "locality" in subject:
            ssl_subject = ssl_subject + "/L={}".format(subject["locality"])
        if "organization" in subject:
            ssl_subject = ssl_subject + "/O={}".format(subject["organization"])
        if "organizational_unit" in subject:
            ssl_subject = ssl_subject + "/OU={}".format(subject["organizational_unit"])
        if "cn" in subject:
            ssl_subject = ssl_subject + "/CN={}".format(subject["cn"])
        else:
            hookenv.log("When using \"subject\" argument you must "
                        "provide \"cn\" field at very least")
            return False
        if "email" in subject:
            ssl_subject = ssl_subject + "/emailAddress={}".format(subject["email"])

        cmd = ["/usr/bin/openssl", "req", "-new", "-newkey",
               "rsa:{}".format(keysize), "-days", "365", "-nodes", "-x509",
               "-keyout", keyfile,
               "-out", certfile, "-subj", ssl_subject]
    elif cn:
        cmd = ["/usr/bin/openssl", "req", "-new", "-newkey",
               "rsa:{}".format(keysize), "-days", "365", "-nodes", "-x509",
               "-keyout", keyfile,
               "-out", certfile, "-subj", "/CN={}".format(cn)]

    if not cmd:
        hookenv.log("No config, subject or cn provided,"
                    "unable to generate self signed SSL certificates")
        return False
    try:
        subprocess.check_call(cmd)
        return True
    except Exception as e:
        print "Execution of openssl command failed:\n{}".format(e)
        return False
