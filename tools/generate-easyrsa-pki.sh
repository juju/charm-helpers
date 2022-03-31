#!/bin/sh -x
EASYRSA_LOC="${EASYRSA_LOC:-/usr/share/easy-rsa}"

case "x${1}" in
  xec)    PARAMS="--use-algo=ec --curve=secp384r1";;
  xrsa|x) PARAMS="--use-algo=rsa --keysize=2048";;
  *)      echo "Wrong algo kind, exiting."; exit 1;;
esac

export PATH="${EASYRSA_LOC}${PATH:+:${PATH}}"
easyrsa init-pki
#ln -s "${EASYRSA_LOC}/openssl-easyrsa.cnf" pki/openssl-easyrsa.cnf
#ln -s "${EASYRSA_LOC}/safessl-easyrsa.cnf" pki/safessl-easyrsa.cnf
ln -s "${EASYRSA_LOC}/x509-types"

easyrsa --req-c=GB --req-city=London --days=1461 --batch ${EC_PARAMS} \
  --req-st='' --req-email='' --req-ou='' \
  --req-org="Canonical Group Limited" --req-cn=root_ca \
  build-ca nopass

if [ -n "${SUB_CA}" ]; then
  mkdir -p sub; cd sub
  easyrsa init-pki
  easyrsa --req-c=GB --req-city=London --days=1461 --batch ${EC_PARAMS} \
    --req-st='' --req-email='' --req-ou='' \
    --req-org="Canonical UK Limited" --req-cn=sub_ca \
    build-ca nopass subca
  cd ..

  cp sub/pki/reqs/ca.req pki/reqs/sub_ca.req
  easyrsa --batch sign-req ca sub_ca nopass
  cp pki/issued/sub_ca.crt sub/pki/ca.crt
fi

#cd sub
easyrsa --req-c=GB --req-city=London --days=1461 --batch ${EC_PARAMS} \
  --req-st='' --req-email='' --req-ou='' \
  --req-org="Canonical UK Limited" \
  build-serverClient-full server nopass
#cd ..
