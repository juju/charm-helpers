from charmhelpers.core.hookenv import (
    config,
    log,
    relation_get,
    relation_ids,
    related_units,
)


class OSContextError(Exception):
    pass

def context_complete(ctxt):
    _missing = []
    for k, v in ctxt.iteritems():
        if v == None or v == '':
            _missing.append(k)
    if _missing:
        print 'Missing required data: %s' % ' '.join(_missing)
        return False
    return True

def shared_db(relation_id=None, unit_id=None):
    conf = config()
    try:
        database = conf['database']
        username = conf['database-user']
    except KeyError as e:
        log('Could not generate shared_db context. '
            'Missing required charm config options: %s.' % e)
        raise OSContextError
    ctxt = {}
    for rid in relation_ids('shared-db'):
        for unit in related_units(rid):
            ctxt = {
                'database_host': relation_get('db_host', rid=rid, unit=unit),
                'database': database,
                'database_user': username,
                'database_password': relation_get('password', rid=rid, unit=unit)
            }
    if not context_complete(ctxt):
        return {}
    return ctxt

def identity_service(relation_id=None):
    ctxt = {
        'service_port': relation_get('service_port'),
        'service_host': relation_get('service_host'),
        'auth_host': relation_get('auth_host'),
        'auth_port': relation_get('auth_port'),
        'admin_tenant_name': relation_get('service_tenant'),
        'admin_user': relation_get('service_username'),
        'admin_password': relation_get('service_password'),
        # XXX: Hard-coded http.
        'service_protocol': 'http',
        'auth_protocol': 'http',
    }
    if not context_complete(ctxt):
        return {}
    return ctxt

def amqp(relation_id=None):
    conf = config()
    try:
        username = conf['rabbit-user']
        vhost = conf['rabbit-vhost']
    except KeyError as e:
        log('Could not generate shared_db context. '
            'Missing required charm config options: %s.' % e)
        raise OSContextError

    ctxt = {}
    for rid in relation_ids('amqp'):
        for unit in related_units(rid):
            if relation_get('clustered', rid=rid, unit=unit):
                rabbitmq_host = relation_get('vip', rid=rid, unit=unit)
            else:
                rabbitmq_host = relation_get('private-address',
                                             rid=rid, unit=unit)
            ctxt = {
                'rabbitmq_host': rabbitmq_host,
                'rabbitmq_user': username,
                'rabbitmq_password': relation_get('password', rid=rid,
                                                   unit=unit),
                'rabbitmq_virtual_host': vhost,
            }
    if not context_complete(ctxt):
        return {}
    return ctxt
