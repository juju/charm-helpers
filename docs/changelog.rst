Changelog
---------

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
