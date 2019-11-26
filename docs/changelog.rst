Changelog
---------

0.20.6
^^^^^^
Thursday 21st November 2019

 * MySQL configuration handling (#395)
 * Use juju ssh for get_ubuntu_release_from_sentry (#396)
 * Policyd library changes to support openstack-dashboard (#393)

0.20.5
^^^^^^
Monday 18th November 2019

 * ufw: add support for new keywords as well as a function to retrieve rules (#390)
 * Duplicate resource retry fix from reactive (#392)
 * Add section-placement (#389)
 * Update swift versions for train (#388)
 * Fix the py35 issue with json not accepting bytestrings (#387)
 * Fix policyd on trusty (py34 issue) (#386)
 * Add support for the action-log hook command (#385)
 * Update the policyd docstrings due to charm changes (#382)
 * Fix policyd on py35 (#384)

0.20.4
^^^^^^
Friday 4th October 2019

* Stop duplicate ops being added to CephBrokerRq (#381)
* Allow OpenStack deployments from PPA packages (#380)
* MySQL 8 features (#377)
* Fix policyd helper where when the config value is set to false (#379)

0.20.3
^^^^^^
Friday 27th September 2019

* Add policyd override helpers (#368)
* Resource parameter order is important in Eoan (#373)
* Complete Eoan Enablement (#372)
* Conditionally add port_forwarding to l3_extension_plugins (#370)
* Allow enabling the pg autoscaler when the module is enabled (#343)
* Change openstack amulet helper to use `OS_` env var format (#369)

0.20.2
^^^^^^
Tuesday 27th August 2019

* get_system_env: Search should be case sensitive (#365)
* fetch: Override apt execution environment (#360)

0.20.1
^^^^^^
Wednesday 14th August 2019

* Remove ``psutil`` from ``setup.py`` (#359)

0.20.0
^^^^^^
Tuesday 13th August 2019

* Replace ``python-apt`` functionality (#341)
* Add context with info about running host (#357)
* Use "rabbit_use_ssl" instead of "ssl" for ocata config (#355)
* Add getter helpers to contrib ovs module (#353)
* Allow the current password to be passed in. (#354)
* Optionally configure haproxy (#351)

0.19.16
^^^^^^^
Wednesday 17th July 2019

 * Use pymysql >= Queens (#348)
 * Add helper to get the percona entry for amulet (#349)
 * Adding function to check if relation has proper broker_rsp (#347)
 * Add service_{project,domain}_id keys to Ident ctxt (#346)

0.19.15
^^^^^^^
Tuesday 9rd July 2019

 * Make NRPE.add_check(shortname=...) optional again (#345)

0.19.14
^^^^^^^
Wednesday 3rd July 2019

 * Preserve old keymap entries on NRPE.write (#311)
 * Make ConfigParser not strict (#338)
 * Update tests to actually be run (#339)
 * Make XFS inode size configurable (#313)
 * ovs: Allow IPFIX configuration tuning (#335)
 * Set unit_name when requesting certificates. (#334)
 * Add relation support for firewall group logging (#333)
 * Fix vendor_data py3 issue of PR #324 (#332)
 * Fix wrong usage of relation_get in \*_broker_action_done (#327)
 * Ensure CephContext will correctly be incomplete (#329)
 * openstack: Add data for train release (#328)
 * adding newton & above release support for nuage (#305)
 * Add source keys before the apt list entry. (#326)
 * Add Contexts for Nova Vendor Metadata (#324)
 * openstack: add send_notifications_to_logs option (#323)
 * openstack: rename physical-network-mtus, global-physnet-mtu for jinja (#322)
 * openstack: add global-physnet-mtu to NeutronAPIContext  (#317)
 * Openstack port resolver should filter out non-existent ports (#320)
 * Fix typo in filter_installed_packages call (#318)
 * Fix issue with ceph-radosgw unit-tests (#316)
 * Bug/1786186 (#315)
 * Switch test runner to tox and update travis-ci definition (#301)
 * openstack: oslo messaging notification (#310)
 * Re-enable pgrep_full (#309)
 * contrib/openstack: Return status on process certificates (#308)

0.19.13
^^^^^^^
Tuesday 9th April 2019

* stein: Add swift 2.21.0 (#307)
* enable disco (#306)
* Added context generator for logrotate (#303)
* Allow specifying ownership of certificate files (#302)
* Update Keystone expectations to meet security guide (#299)
* Added an "ignore" option to sysctl_create (#300)
* Catch NoNetworkBinding for VIPs in resolve_address (#298)
* Add LUKS helpers to charmhelpers (#296)
* Adding arch method in host (#295)

0.19.12
^^^^^^^
Tuesday 5th March 2019

* Use the same gpg command (#290)
* Fix openstack-upgrade-available detection to work with new versions of apt.version_compare() (#292)

0.19.11
^^^^^^^
Thursday February 27 2019

* Add getrange command to unitdata CLI (#273)
* Fixing `cmp_pkgrevno` Ceph bug (#288)
* Update swift version for stein (#287)
* Add support for creating erasure coded pool and setting ``max_objects`` quota (#284)

0.19.10
^^^^^^^
Thursday February 27 2019

* Add OpenStack version filter to audits (#286)
* Handle new juju charm proxy settings and https keyserver URLs (#248)
* Allow an audit to be excluded via configuration (#282)
* Add section-oslo-messaging-rabbit for Ocata+ (#283)
* Catch NoNetworkBinding in addition to NotImplementedError (#281)

0.19.9
^^^^^^
Thursday February 21 2019

* Add OpenStackSecurityGuide auditing (#274)
* Add support for ``app_name`` in ``add_op_create_pool`` (#280)
* Update ceph helpers for device class support (#279)
* Remove target directory before sync (#277)
* Fix typos (#275)
* Move contrib.python to fetch.python (#272)
* Allow None state from charm_func_with_configs (#270)
* Introduce get_distrib_codename helper (#268)

0.19.8
^^^^^^
Tuesday January 29 2019

* Add get_installed_semantic_versioned_packages (#269)

0.19.7
^^^^^^
Saturday January 19 2019

* Fix ceph update keyring (#266)

0.19.6
^^^^^^
Tuesday January 15 2019

* Use default sqlalchemy driver prior to stein (#264)
* nrpe: Allow services with '@' in name (#263)
* Fix a couple of docstring typos (#262)
* Use pymysql driver for mysql sqlalchemy dialect (#261)
* Separate certificates with lineseparator in bundles (#260)

0.19.5
^^^^^^
Wednesday December 19 2018

* Spelling (#258)
* Dedicated VIP/CIDR fallback settings method. (#259)
* Add monitoring to vip resources in OpenStack (#257)
* Expose resource group names (#256)
* Add openstack series support for stein (#255)
* Charms can specify additional delete & group info (#253)
* Refactor vip resource creation for iface'less use (#250)
* Update copy_nrpe_checks() for optional c-h directory (#247)
* Extra config when generating Openstack HA settings (#249)
* Extract common code to pause/resume services (#245)
* Fix loopback devices helper for PY3 (#244)
* Add "host" option to "connect" method (#240)
* Add "proposed" to get_os_codename_install_source function (#242)
* Update amulet helper origin list for ceilometer-agent (#239)

0.19.4
^^^^^^
Wednesday November 7 2018

* Consistently render haproxy.conf (#237) (#238)
* Add helpers for extracting certs from relation. (#235)
* Make the harden and pausable_restart_on_change lazy (#234)
* core/host: fix changing permissions in write_file (#233)
* Add helpers to get expected peer and related units from goal-state (#226)
* Render perms (#231)
* Add {series} support to _add_apt_repository (#230)

0.19.3
^^^^^^
Tuesday October 9 2018

* Adding "log" support to Neutron API context (#228)
* Enable the apache audit checks to also be PY3 compatible (#227)
* Ensure auth_uri/auth_url include v3 API version (#225)
* Add OpenStack context that provides versions (#224)
* Allow glance image hypervisor type to be unset (#223)
* Allow cirros image virt type to be set (#222)
* Refactor install_ca_cert to core.host (#220)
* Generalized glance_create_image (#221)
* Remove unnecessary charm relation option (#219)
* CompareHostReleases needs cosmic series support (#216)
* fetch: add helper to determine installed packages (#215)
* Quieten down unit tests (#214)
* Write all configs on series upgrade complete (#213)
* Add helpers for common series upgrade tasks (#212)
* Adding new parameters into Neutron ctxt to make NSG logging configurable (#211)
* Fix docs rendering on RTD (#210)

0.19.2
^^^^^^
Monday September 10 2018

* Add helper for apt autoremove (#209)
* ensure max lenght of message in log func (#208)
* Add 2.19.0 to rocky swift versions (#207)
* Fix get_ceph_pools for mimic (#206)
* Use glance client v2 (#205)
* Support multiple WSGI vhosts in Openstack (#201)
* Series Upgrade Helpers (#200)
* Add functions for managing ssh assets in OpenStack (#197)
* Add unit_doomed call to inform about removed units (#199)
* Rename service_name, add helpers for model name and UUID (#196)

0.19.1
^^^^^^
Wednesday July 11 2018

* Retry importing key on failure. (#194)
* Allow a src directory passed to copy_nrpe_checks (#193)
* Don't update updatedb.conf file if not available (#191)
* Add remaining series support for rocky (#190)
* Support multi amqp or shared-db relations in ctxts (#188)
* LP: #1748433 Ansible version changed from 2.0 to 2.5 and there is sev… (#181)
* ovs: long interface names and existing wiring (#186)
* Add "select" function to "MySQLHelper" class (#185)

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
