Changelog
---------

0.19.0
^^^^^^
Tuesday June 5 2018

* Add set_Open_vSwitch_column_value (#182)
* update deployment to use Amulet supported storage (#183)
* Support the goal-state command (#180)

0.18.11
^^^^^^^
Wednesday May 16 2018

* Add support for certs relation in OpenStack charms (#173)
* Explicitly set api_version in get_default_keystone_session (#177)
* Allow forcing keystone preferred-api-version (#176)
* Retry keystone_wait_for_propagation() on exception (#175)
* Revert "Adds operator.socket (#115)" (#174)
* vaultlocker: Use secret_id's (#171)
* Reload UFW (#170)
* remove escapes from enable_ipfix (#169)

0.18.9
^^^^^^
Wednesday May 2 2018

* Adds operator.socket (#115)
* Make get_os_codename_install_source() independent of the series where it's executed (#156)
* setup.py: exclude tests and tools directories (#104)
* Support python dict in sysctl_create (#15)
* Add notification_format (#145)
* Enable IPFIX monitoring on OVS bridges (#168)
* Do not parse config state file if empty (#166)
* Add misc extra bits for vaultlocker work (#165)
* Update pool creation to set app-name (#163)
* Add logging of any decode Exception in config() (#161)
* Add helpers for vaultlocker (#159)
* Add support for more arguments in EnsureDirContext (#158)
* core/services : fix handling of ports (#155)
* Enable proxy header parsing (#157)
* Cache config-get data (#147)
* add_ovsbridge_linuxbridge fails for missing `source` in e/n/i  (#153)
* Bug/1761305/ensure apache ssl (#151)

0.18.8
^^^^^^
Thursday Apr 12 2018

* Allow s390x in fetch (#150)
* Read in ca certificate as binary for PY3 (#146)
* Fix keystone_wait_for_propagation test helper (#144)
* Account for password field name change in PXC 5.7 (#99)
* Handle non-zero unit numbered leader (#138)
* storage: Add create_logical_volume helper (#141)

0.18.7
^^^^^^
Monday Mar 19 2018

* Fix network get (#118)
* Fix JSON serializable error using default (#136)
* Add egress_subnets helper to access egress-subnets on a relation (#116)
* Allow Service Manager applications to handle the ICMP protocol (#108)
* Minor fix for changelog format in docs (#134)

0.18.6
^^^^^^
Thursday Mar 15 2018

* Ensure keys in cashed func args are sorted (#132)
* Doc updates (#131)
* update amulet helper to fix cinder authentication with keystone v3 (#122)
* Update get_ca to include identity-credentials (#124)
* Update IdentityService context for service_domain_id (#121)
* Service catalogue validators to convert to v3 (#119)
* Add code to retrieve keystone session and client (#120)
* Add 2.17.0 for queens swift versions (#117)
* Allow passing of expected number of EPs (#113)
* Add Volume API Context (#65) (#111)

0.18.5
^^^^^^
Tuesday Feb 6 2018

* contrib/network: don't panic if an interface is deleted during get_address_in_network (#107)
* Add string template rendering to core/templating (#102)
* Handle no network binding exception gracefully (#97)
* Support use of HAProxy context in dashboard charm (#98)
* Add from_string template rendering capability (#87)
* add EnsureDirContext (#88)

0.18.4
^^^^^^
Friday Jan 19 2018

* Fix regression in NRPE haproxy check (#95)
* Make HAProxyContext network spaces aware (#92)
* Fix file permissions on config cache and unitdata (#94)
* Fix Swift package version check (#93)
* Add helpers for hacluster interface type (#82)
* dfs: drop venv specific parts from wsgi template (#89)
* Drop OpenStack deploy-from-source helpers (#85)
* Fix for pool_set function and validator handling of strings (#80)
* Fix presentation use of domain for identity-credentials (#79)
* Add OpenStack Context for identity-credentials interface type (#78)
* Handle profile creation in luminous (#71)
* Add support for setting object prefix permissions (#76)
* Ensure all keys checked when comparing broker obj (#75)
* Ensure json file only changed if necessary (#74)
* Update HAProxy default timeout values (#73)
* Use volumev3 for Openstack >= Pike (#65) (#66)
* Add funcs for listing & extending logical volumes (#72)
* Ceph Luminous Amulet Test Updates (#69)
* Add bionic to ubuntu host helpers (#67)
* Fix get_swift_codename() to work with PY3 (#62)
* Fix up ceph library exception logging for py3 (#64)
* Release: 0.18.3 (#61)
