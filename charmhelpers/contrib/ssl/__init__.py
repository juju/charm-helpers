import subprocess


def generate_selfsigned(keyfile, certfile, subject=None, config=None):
    if subject:
        ssl_subject = "/C={subject[country]}/ST={subject[state]}/L={subject[locality]}" \
            "/O={subject[organization]}/OU={subject[organizational_unit]}/CN={subject[cn]}" \
            "/emailAddress={subject[email]}".format(subject=subject)
        cmd = ["/usr/bin/openssl", "req", "-new", "-newkey",
               "rsa:1024", "-days", "365", "-nodes", "-x509",
               "-keyout", keyfile,
               "-out",    certfile, "-subj", ssl_subject]
    elif config:
        cmd = ["/usr/bin/openssl", "req", "-new", "-newkey",
               "rsa:1024", "-days", "365", "-nodes", "-x509",
               "-keyout", keyfile,
               "-out",    certfile, "-config", config]

    subprocess.check_call(cmd)
