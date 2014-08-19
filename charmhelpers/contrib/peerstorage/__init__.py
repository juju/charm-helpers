from charmhelpers.core.hookenv import (
    relation_ids,
    relation_get,
    local_unit,
    relation_set,
)


"""
This helper provides functions to support use of a peer relation
for basic key/value storage, with the added benefit that all storage
can be replicated across peer units.

Requirement to use:

To use this, the "peer_echo()" method has to be called form the peer
relation's relation-changed hook:

@hooks.hook("cluster-relation-changed") # Adapt the to your peer relation name
def cluster_relation_changed():
    peer_echo()

Once this is done, you can use peer storage from anywhere:

@hooks.hook("some-hook")
def some_hook():
    # You can store and retrieve key/values this way:
    if is_relation_made("cluster"):  # from charmhelpers.core.hookenv
        # There are peers available so we can work with peer storage
        peer_store("mykey", "myvalue")
        value = peer_retrieve("mykey")
        print value
    else:
        print "No peers joind the relation, cannot share key/values :("
"""


def peer_retrieve(key, relation_name='cluster'):
    """Retrieve a named key from peer relation `relation_name`."""
    cluster_rels = relation_ids(relation_name)
    if len(cluster_rels) > 0:
        cluster_rid = cluster_rels[0]
        return relation_get(attribute=key, rid=cluster_rid,
                            unit=local_unit())
    else:
        raise ValueError('Unable to detect'
                         'peer relation {}'.format(relation_name))


def peer_store(key, value, relation_name='cluster'):
    """Store the key/value pair on the named peer relation `relation_name`."""
    cluster_rels = relation_ids(relation_name)
    if len(cluster_rels) > 0:
        cluster_rid = cluster_rels[0]
        relation_set(relation_id=cluster_rid,
                     relation_settings={key: value})
    else:
        raise ValueError('Unable to detect '
                         'peer relation {}'.format(relation_name))


def peer_echo(includes=None):
    """Echo filtered attributes back onto the same relation for storage.

    This is a requirement to use the peerstorage module - it needs to be called
    from the peer relation's changed hook.
    """
    rdata = relation_get()
    echo_data = {}
    if includes is None:
        echo_data = rdata.copy()
        for ex in ['private-address', 'public-address']:
            if ex in echo_data:
                echo_data.pop(ex)
    else:
        for attribute, value in rdata.iteritems():
            for include in includes:
                if include in attribute:
                    echo_data[attribute] = value
    if len(echo_data) > 0:
        relation_set(relation_settings=echo_data)
