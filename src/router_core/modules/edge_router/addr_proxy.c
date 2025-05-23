/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

#include "addr_proxy.h"

#include "core_events.h"
#include "core_link_endpoint.h"
#include "router_core_private.h"

#include "qpid/dispatch/amqp.h"
#include "qpid/dispatch/iterator.h"
#include "qpid/dispatch/message.h"
#include "qpid/dispatch/parse.h"

#include <inttypes.h>
#include <stdio.h>

//
// This is the Address Proxy component of the Edge Router module.
//
// Address Proxy has the following responsibilities:
//
//   Related to dynamic (topological) addresses:
//
//    1) When an edge connection becomes active, the "_edge" address is properly linked to an
//       outgoing anonymous link on the active edge connection.
//
//    2) When an edge connection becomes active, an incoming link is established over the edge
//       connection that is used to transfer deliveries to topological (dynamic) addresses
//       on the edge router.
//
//  Related to mobile addresses:
//
//    3) Ensure that if there is an active edge connection, that connection should have one incoming
//       link for every mobile address for which there is at least one local consumer.
//
//    4) Ensure that if there is an active edge connection, that connection should have one outgoing
//       link for every mobile address for which there is at least one local producer.
//
//    5) Maintain an incoming link for edge-address-tracking attached to the edge-address-tracker
//       in the connected interior router.
//
//    6) Handle address tracking updates indicating which producer-addresses have destinations
//       reachable via the edge connection.
//
//    7) For addresses that have at least one local non-proxy destination, maintain inbound links
//       on each open inter-edge connection.
//

#define INITIAL_CREDIT 32


struct qcm_edge_addr_proxy_t {
    qdr_core_t                *core;
    qdrc_event_subscription_t *event_sub;
    qdr_address_t             *edge_conn_addr;
    qdrc_endpoint_desc_t       endpoint_descriptor;

    // Connection-related state:
    qdr_connection_t          *edge_conn;
    qdr_link_t                *edge_uplink;        // anonymous link for deliveries to interior
    qdr_link_t                *edge_downlink;      // for router-addressed deliveries from interior
    qdrc_endpoint_t           *tracking_endpoint;  // for address tracking updates from interior
};


static qdr_terminus_t *qdr_terminus_edge_downlink(const char *addr)
{
    qdr_terminus_t *term = qdr_terminus(0);
    qdr_terminus_add_capability(term, QD_CAPABILITY_EDGE_DOWNLINK);
    if (addr)
        qdr_terminus_set_address(term, addr);
    return term;
}


static qdr_terminus_t *qdr_terminus_normal(const char *addr)
{
    qdr_terminus_t *term = qdr_terminus(0);
    if (addr)
        qdr_terminus_set_address(term, addr);
    return term;
}


static void add_inlink(qcm_edge_addr_proxy_t *ap, const char *key, qdr_address_t *addr)
{
    qdr_link_t *edge_inlink = safe_deref_qdr_link_t(addr->edge_inlink_sp);
    if (edge_inlink == 0) {
        qdr_terminus_t *term = qdr_terminus_normal(key + 1);

        qdr_link_t *link = qdr_create_link_CT(ap->core, ap->edge_conn, QD_LINK_ENDPOINT, QD_INCOMING,
                                              term, qdr_terminus_normal(0), QD_SSN_ENDPOINT,
                                              QDR_DEFAULT_PRIORITY);
        link->proxy = true;
        qdr_core_bind_address_link_CT(ap->core, addr, link);
        set_safe_ptr_qdr_link_t(link, &addr->edge_inlink_sp);
        qd_log(LOG_ROUTER_CORE, QD_LOG_DEBUG,
               "[C%"PRIu64"][L%"PRIu64"] creating incoming proxy link to address '%s'",
               link->conn->identity, link->identity,
               (const char*) qd_hash_key_by_handle(addr->hash_handle));
    }
}


static void del_inlink(qcm_edge_addr_proxy_t *ap, qdr_address_t *addr)
{
    qdr_link_t *link = safe_deref_qdr_link_t(addr->edge_inlink_sp);
    if (link) {
        qd_log(LOG_ROUTER_CORE, QD_LOG_DEBUG,
               "[C%"PRIu64"][L%"PRIu64"] deleting incoming proxy link to address '%s'",
               link->conn->identity, link->identity,
               (const char*) qd_hash_key_by_handle(addr->hash_handle));
        qd_nullify_safe_ptr(&addr->edge_inlink_sp);
        qdr_core_unbind_address_link_CT(ap->core, addr, link);
        qdr_link_outbound_detach_CT(ap->core, link, 0, QDR_CONDITION_NONE);
    }
}


static void add_outlink(qcm_edge_addr_proxy_t *ap, const char *key, qdr_address_t *addr)
{
    qdr_link_t *edge_outlink = safe_deref_qdr_link_t(addr->edge_outlink_sp);
    if (edge_outlink == 0 && DEQ_SIZE(addr->subscriptions) == 0) {
        //
        // Note that this link must not be bound to the address at this time.  That will
        // happen later when the interior tells us that there are upstream destinations
        // for the address (see on_transfer below).
        //
        qdr_terminus_t *term = qdr_terminus_normal(key + 1);

        qdr_link_t *link = qdr_create_link_CT(ap->core, ap->edge_conn, QD_LINK_ENDPOINT, QD_OUTGOING,
                                              qdr_terminus_normal(0), term, QD_SSN_ENDPOINT,
                                              QDR_DEFAULT_PRIORITY);
        link->proxy = true;
        set_safe_ptr_qdr_link_t(link, &addr->edge_outlink_sp);

        qd_log(LOG_ROUTER_CORE, QD_LOG_DEBUG,
               "[C%"PRIu64"][L%"PRIu64"] created outgoing proxy link to address '%s'",
               link->conn->identity, link->identity,
               (const char*) qd_hash_key_by_handle(addr->hash_handle));
    }
}


static void del_outlink(qcm_edge_addr_proxy_t *ap, qdr_address_t *addr)
{
    qdr_link_t *link = safe_deref_qdr_link_t(addr->edge_outlink_sp);
    if (link) {
        qd_log(LOG_ROUTER_CORE, QD_LOG_DEBUG,
               "[C%"PRIu64"][L%"PRIu64"] deleting outgoing proxy link to address '%s'",
               link->conn->identity, link->identity,
               (const char*) qd_hash_key_by_handle(addr->hash_handle));
        qd_nullify_safe_ptr(&addr->edge_outlink_sp);
        qdr_core_unbind_address_link_CT(ap->core, addr, link);
        qdr_link_outbound_detach_CT(ap->core, link, 0, QDR_CONDITION_NONE);
    }
}


static void proxy_addr_on_inter_edge_connection(qcm_edge_addr_proxy_t *ap, qdr_address_t *addr, qdr_connection_t *conn)
{
    const char     *key  = (const char*) qd_hash_key_by_handle(addr->hash_handle);
    qdr_terminus_t *term = qdr_terminus_normal(key + 1);

    qdr_link_t *link = qdr_create_link_CT(ap->core, conn, QD_LINK_ENDPOINT, QD_INCOMING,
                                          term, qdr_terminus_normal(0), QD_SSN_ENDPOINT,
                                          QDR_DEFAULT_PRIORITY);
    link->proxy = true;
    qdr_core_bind_address_link_CT(ap->core, addr, link);
}


static void proxy_addr_on_all_inter_edge_connections(qcm_edge_addr_proxy_t *ap, qdr_address_t *addr)
{
    qdr_edge_peer_t *edge_peer = DEQ_HEAD(ap->core->edge_peers);
    while (!!edge_peer) {
        proxy_addr_on_inter_edge_connection(ap, addr, edge_peer->primary_conn);
        edge_peer = DEQ_NEXT(edge_peer);
    }
}


static void remove_proxies_for_addr(qcm_edge_addr_proxy_t *ap, qdr_address_t *addr)
{
    qdr_link_ref_t *ref = DEQ_HEAD(addr->inlinks);
    while (!!ref) {
        qdr_link_ref_t *next = DEQ_NEXT(ref);
        qdr_link_t     *link = ref->link;
        if (link->conn && link->conn->role == QDR_ROLE_INTER_EDGE) {
            qdr_core_unbind_address_link_CT(ap->core, addr, link);
            qdr_link_outbound_detach_CT(ap->core, link, 0, QDR_CONDITION_NONE);
        }
        ref = next;
    }
}


static void on_inter_edge_connection_opened(qcm_edge_addr_proxy_t *ap, qdr_connection_t *conn)
{
    qdr_address_t *addr = DEQ_HEAD(ap->core->addrs);
    while (!!addr) {
        if (qdr_address_is_mobile_CT(addr) && DEQ_SIZE(addr->rlinks) - addr->proxy_rlink_count > 0) {
            proxy_addr_on_inter_edge_connection(ap, addr, conn);
        }
        addr = DEQ_NEXT(addr);
    }
}


static void on_link_event(void *context, qdrc_event_t event, qdr_link_t *link)
{
    if (!link || !link->conn)
        return;

    //
    // We only care if the link event is on an edge connection.
    //
    if (link->conn->role != QDR_ROLE_EDGE_CONNECTION)
            return;

    switch (event) {
        case QDRC_EVENT_LINK_OUT_DETACHED: {
            qdr_address_t *addr = link->owning_addr;
            if (addr) {
                qdr_link_t *edge_outlink = safe_deref_qdr_link_t(addr->edge_outlink_sp);
                if (link == edge_outlink) {
                    //
                    // The link is being detached. If the detaching link is the same as the link's owning_addr's edge_outlink,
                    // set the edge_outlink on the address to be zero. We do this because this link is going to be freed
                    // and we don't want anyone dereferencing the addr->edge_outlink
                    //
                    qd_nullify_safe_ptr(&addr->edge_outlink_sp);
                    qd_log(LOG_ROUTER_CORE, QD_LOG_DEBUG,
                           "[C%"PRIu64"][L%"PRIu64"] outgoing link to address '%s' detached",
                           link->conn->identity, link->identity,
                           (const char*) qd_hash_key_by_handle(addr->hash_handle));
                }
            }
            break;
        }

        case QDRC_EVENT_LINK_IN_DETACHED: {
            qdr_address_t *addr = link->owning_addr;
            if (addr) {
                qdr_link_t *edge_inlink = safe_deref_qdr_link_t(addr->edge_inlink_sp);
                if (link == edge_inlink) {
                    //
                    // The link is being detached. If the detaching link is the same as the link's owning_addr's edge_inlink,
                    // set the edge_inlink on the address to be zero. We do this because this link is going to be freed
                    // and we don't want anyone dereferencing the addr->edge_inlink
                    //
                    qd_nullify_safe_ptr(&addr->edge_inlink_sp);
                    qd_log(LOG_ROUTER_CORE, QD_LOG_DEBUG,
                           "[C%"PRIu64"][L%"PRIu64"] incoming link to address '%s' detached",
                           link->conn->identity, link->identity,
                           (const char*) qd_hash_key_by_handle(addr->hash_handle));
                }
            }
            break;
        }

        default:
            assert(false);
            break;
    }
}


// The edge connection has opened.  Setup the various control links and tracking endpoint. Run through all
// locally-terminated mobile-addressed links and create proxy links to the interior.
//
static void setup_edge_connection(qcm_edge_addr_proxy_t *ap, qdr_connection_t *conn)
{
    assert(!ap->edge_conn);
    ap->edge_conn = conn;


    //
    // Attach an anonymous sending link to the interior router.
    //
    assert(!ap->edge_uplink);
    ap->edge_uplink = qdr_create_link_CT(ap->core, conn,
                                         QD_LINK_ENDPOINT, QD_OUTGOING,
                                         qdr_terminus(0), qdr_terminus(0),
                                         QD_SSN_ENDPOINT,
                                         QDR_DEFAULT_PRIORITY);
    ap->edge_uplink->proxy = true;

    //
    // Associate the anonymous sender with the edge connection address.  This will cause
    // all deliveries destined off-edge to be sent to the interior via the edge connection.
    //
    qdr_core_bind_address_link_CT(ap->core, ap->edge_conn_addr, ap->edge_uplink);

    //
    // Attach a receiving link for edge summary.  This will cause all deliveries
    // destined for this router to be delivered via the edge connection.
    //
    assert(!ap->edge_downlink);
    ap->edge_downlink = qdr_create_link_CT(ap->core, conn,
                                           QD_LINK_ENDPOINT, QD_INCOMING,
                                           qdr_terminus_edge_downlink(ap->core->router_id),
                                           qdr_terminus_edge_downlink(0),
                                           QD_SSN_ENDPOINT, QDR_DEFAULT_PRIORITY);
    ap->edge_downlink->proxy = true;

    //
    // Attach a receiving link for edge address tracking updates.
    //
    assert(!ap->tracking_endpoint);
    ap->tracking_endpoint =
        qdrc_endpoint_create_link_CT(ap->core, conn, QD_INCOMING,
                                     qdr_terminus_normal(QD_TERMINUS_EDGE_ADDRESS_TRACKING),
                                     qdr_terminus(0), &ap->endpoint_descriptor, ap);

    //
    // Create proxy links for eligible local destinations (mobile only)
    //
    qdr_address_t *addr = DEQ_HEAD(ap->core->addrs);
    while (addr) {
        const char *key = (const char*) qd_hash_key_by_handle(addr->hash_handle);
        if (*key == QD_ITER_HASH_PREFIX_MOBILE) {
            //
            // If the address has more than zero attached destinations, create an
            // incoming link from the interior to signal the presence of local consumers.
            //
            if (DEQ_SIZE(addr->rlinks) > 0 || (DEQ_SIZE(addr->subscriptions) > 0 && addr->propagate_local)) {
                if (DEQ_SIZE(addr->rlinks) == 1) { // TODO - fix this logic
                    //
                    // If there's only one link and it's on the edge connection, ignore the address.
                    //
                    qdr_link_ref_t *ref = DEQ_HEAD(addr->rlinks);
                    if (ref->link->conn != ap->edge_conn)
                        add_inlink(ap, key, addr);
                } else
                    add_inlink(ap, key, addr);
            }

            //
            // If the address has more than zero attached sources, create an outgoing link
            // to the interior to signal the presence of local producers.
            //
            bool add = false;
            if (DEQ_SIZE(addr->inlinks) > 0 || DEQ_SIZE(addr->watches) > 0) {
                if (DEQ_SIZE(addr->inlinks) == 1 && DEQ_SIZE(addr->watches) == 0) {
                    //
                    // If there's only one link and it's on the edge connection, ignore the address.
                    //
                    qdr_link_ref_t *ref = DEQ_HEAD(addr->inlinks);
                    if (ref->link->conn != ap->edge_conn)
                        add = true;
                } else
                    add = true;

                if (add) {
                    add_outlink(ap, key, addr);
                }
            }
        }
        addr = DEQ_NEXT(addr);
    }
}


// Remove all edge control and proxy links for the current connection.
// This reverts the setup done in setup_edge_connection.
//
static void cleanup_edge_connection(qcm_edge_addr_proxy_t *ap)
{
    if (ap->tracking_endpoint) {
        qdrc_endpoint_detach_CT(ap->core, ap->tracking_endpoint, 0);
        ap->tracking_endpoint = 0;
    }

    if (ap->edge_downlink) {
        qdr_link_outbound_detach_CT(ap->core, ap->edge_downlink, 0, QDR_CONDITION_NONE);
        ap->edge_downlink = 0;
    }

    if (ap->edge_uplink) {
        qdr_core_unbind_address_link_CT(ap->core, ap->edge_conn_addr, ap->edge_uplink);
        qdr_link_outbound_detach_CT(ap->core, ap->edge_uplink, 0, QDR_CONDITION_NONE);
        ap->edge_uplink = 0;
    }

    //
    // Teardown all proxy links. NOTE WELL: this does not tear down *streaming links*!  Those are anonymous links (not
    // mobile). We do not want to tear down streaming links because we do not want to terminate active TCP flows.
    //
    qdr_address_t *addr = DEQ_HEAD(ap->core->addrs);
    while (addr) {
        qdr_link_t *link;
        if ((link = safe_deref_qdr_link_t(addr->edge_inlink_sp)) != 0) {
            assert(link->conn == ap->edge_conn);
            (void) link;
            del_inlink(ap, addr);
        } else if ((link = safe_deref_qdr_link_t(addr->edge_outlink_sp)) != 0) {
            assert(link->conn == ap->edge_conn);
            (void) link;
            del_outlink(ap, addr);
        }
        addr = DEQ_NEXT(addr);
    }

    // Leave the edge conn up - it may be used for failover
    ap->edge_conn = 0;
}


static void on_conn_event(void *context, qdrc_event_t event, qdr_connection_t *conn)
{
    qcm_edge_addr_proxy_t *ap = (qcm_edge_addr_proxy_t*) context;

    switch (event) {
    case QDRC_EVENT_CONN_OPENED :
        if (conn->role == QDR_ROLE_INTER_EDGE) {
            on_inter_edge_connection_opened(ap, conn);
        }
        break;

    case QDRC_EVENT_CONN_EDGE_ESTABLISHED : {
        //
        // The edge connection to the interior router has opened.
        //
        if (!ap->edge_conn) {
            setup_edge_connection(ap, conn);
        } else {
            // Connection manager has found a "better" connection to the interior router. Migrate to it.
            qd_log(LOG_ROUTER_CORE, QD_LOG_DEBUG,
                   "Upgrading edge-to-interior connection [C%"PRIu64"] to [C%"PRIu64"]",
                   ap->edge_conn->identity, conn->identity);
            cleanup_edge_connection(ap);
            setup_edge_connection(ap, conn);
        }
        break;
    }

    case QDRC_EVENT_CONN_EDGE_LOST :
        ap->edge_conn = 0;
        ap->edge_uplink = 0;
        ap->edge_downlink = 0;
        ap->tracking_endpoint = 0;
        break;

    default:
        assert(false);
        break;
    }
}


static void on_addr_event(void *context, qdrc_event_t event, qdr_address_t *addr)
{
    qcm_edge_addr_proxy_t *ap = (qcm_edge_addr_proxy_t*) context;

    //
    // If the address is not in the Mobile class, no further processing is needed.
    //
    if (!qdr_address_is_mobile_CT(addr))
        return;

    //
    // The following actions need to be done even if there is no established edge connection.
    //
    switch (event) {
    case QDRC_EVENT_ADDR_ADDED_LOCAL_DEST :
        if (DEQ_SIZE(addr->rlinks) - addr->proxy_rlink_count == 1) {
            proxy_addr_on_all_inter_edge_connections(ap, addr);
        }
        break;

    case QDRC_EVENT_ADDR_REMOVED_LOCAL_DEST :
        if (DEQ_SIZE(addr->rlinks) - addr->proxy_rlink_count == 0) {
            remove_proxies_for_addr(ap, addr);
        }
        break;

    default:
        break;
    }

    //
    // If we don't have an established edge connection, there is no further work to be done.
    //
    if (!ap->edge_conn)
        return;

    const char *key = (const char*) qd_hash_key_by_handle(addr->hash_handle);

    switch (event) {
    case QDRC_EVENT_ADDR_ADDED_LOCAL_DEST :
        if (DEQ_SIZE(addr->rlinks) - addr->proxy_rlink_count == 1) {
            add_inlink(ap, key, addr);
        }
        break;

    case QDRC_EVENT_ADDR_REMOVED_LOCAL_DEST :
        if (DEQ_SIZE(addr->rlinks) - addr->proxy_rlink_count == 0) {
            del_inlink(ap, addr);
        }
        break;

    case QDRC_EVENT_ADDR_BECAME_SOURCE :
        add_outlink(ap, key, addr);
        break;

    case QDRC_EVENT_ADDR_NO_LONGER_SOURCE :
        if (DEQ_SIZE(addr->watches) == 0)
            del_outlink(ap, addr);
        break;

    case QDRC_EVENT_ADDR_WATCH_ON :
        add_outlink(ap, key, addr);
        break;

    case QDRC_EVENT_ADDR_WATCH_OFF :
        if (DEQ_SIZE(addr->inlinks) == addr->proxy_inlink_count) {
            del_outlink(ap, addr);
        }
        break;

    default:
        assert(false);
        break;
    }
}


static void on_second_attach(void           *link_context,
                             qdr_terminus_t *remote_source,
                             qdr_terminus_t *remote_target)
{
    qcm_edge_addr_proxy_t *ap = (qcm_edge_addr_proxy_t*) link_context;

    qdrc_endpoint_flow_CT(ap->core, ap->tracking_endpoint, INITIAL_CREDIT, false);

    qdr_terminus_free(remote_source);
    qdr_terminus_free(remote_target);
}


static void on_transfer(void           *link_context,
                        qdr_delivery_t *dlv,
                        qd_message_t   *msg)
{
    qcm_edge_addr_proxy_t *ap = (qcm_edge_addr_proxy_t*) link_context;
    uint64_t dispo = PN_ACCEPTED;

    //
    // Validate the message
    //
    if (qd_message_check_depth(msg, QD_DEPTH_BODY) == QD_MESSAGE_DEPTH_OK) {
        //
        // Get the message body.  It must be a list with two elements.  The first is an address
        // and the second is a boolean indicating whether that address has upstream destinations.
        //
        qd_iterator_t     *iter = qd_message_field_iterator(msg, QD_FIELD_BODY);
        qd_parsed_field_t *body = qd_parse(iter);
        if (!!body && qd_parse_is_list(body) && qd_parse_sub_count(body) == 2) {
            qd_parsed_field_t *addr_field = qd_parse_sub_value(body, 0);
            qd_parsed_field_t *dest_field = qd_parse_sub_value(body, 1);

            if (qd_parse_is_scalar(addr_field) && qd_parse_is_scalar(dest_field)) {
                qd_iterator_t *addr_iter = qd_parse_raw(addr_field);
                bool           dest      = qd_parse_as_bool(dest_field);
                qdr_address_t *addr;

                qd_iterator_reset_view(addr_iter, ITER_VIEW_ALL);
                qd_hash_retrieve(ap->core->addr_hash, addr_iter, (void**) &addr);
                if (addr) {
                    qdr_link_t *link = safe_deref_qdr_link_t(addr->edge_outlink_sp);
                    if (link) {
                        if (dest) {
                            if (link->owning_addr == 0) {
                                qd_log(LOG_ROUTER_CORE, QD_LOG_DEBUG,
                                       "[C%"PRIu64"][L%"PRIu64"] binding proxy link to address '%s'",
                                       link->conn->identity, link->identity,
                                       (const char*) qd_hash_key_by_handle(addr->hash_handle));
                                qdr_core_bind_address_link_CT(ap->core, addr, link);
                            }
                        } else {
                            if (link->owning_addr == addr) {
                                qd_log(LOG_ROUTER_CORE, QD_LOG_DEBUG,
                                       "[C%"PRIu64"][L%"PRIu64"] unbinding proxy link from address '%s'",
                                       link->conn->identity, link->identity,
                                       (const char*) qd_hash_key_by_handle(addr->hash_handle));
                                qdr_core_unbind_address_link_CT(ap->core, addr, link);
                            }
                        }
                    }
                }
            }
        }

        qd_parse_free(body);
        qd_iterator_free(iter);
    } else {
        qd_log(LOG_ROUTER_CORE, QD_LOG_ERROR,
               "Edge Address Proxy: received an invalid message body, rejecting");
        dispo = PN_REJECTED;
    }

    qdrc_endpoint_settle_CT(ap->core, dlv, dispo);

    //
    // Replenish the credit for this delivery
    //
    qdrc_endpoint_flow_CT(ap->core, ap->tracking_endpoint, 1, false);
}

qdr_address_t *qcm_edge_conn_addr(void *link_context)
{
    qcm_edge_addr_proxy_t *ap = (qcm_edge_addr_proxy_t*) link_context;
    if (!ap)
        return 0;
    return ap->edge_conn_addr;
}


qcm_edge_addr_proxy_t *qcm_edge_addr_proxy(qdr_core_t *core)
{
    qcm_edge_addr_proxy_t *ap = NEW(qcm_edge_addr_proxy_t);

    ZERO(ap);
    ap->core = core;

    ap->endpoint_descriptor.label            = "Edge Address Proxy";
    ap->endpoint_descriptor.on_second_attach = on_second_attach;
    ap->endpoint_descriptor.on_transfer      = on_transfer;

    //
    // Establish the edge connection address to represent destinations reachable via the edge connection
    //
    ap->edge_conn_addr = qdr_add_local_address_CT(core, 'L', "_edge", QD_TREATMENT_ANYCAST_CLOSEST);

    //
    // Subscribe to the core events we'll need to drive this component
    //
    ap->event_sub = qdrc_event_subscribe_CT(core,
                                            QDRC_EVENT_CONN_EDGE_ESTABLISHED
                                            | QDRC_EVENT_CONN_EDGE_LOST
                                            | QDRC_EVENT_CONN_OPENED
                                            | QDRC_EVENT_ADDR_ADDED_LOCAL_DEST
                                            | QDRC_EVENT_ADDR_REMOVED_LOCAL_DEST
                                            | QDRC_EVENT_ADDR_BECAME_SOURCE
                                            | QDRC_EVENT_ADDR_NO_LONGER_SOURCE
                                            | QDRC_EVENT_ADDR_WATCH_ON
                                            | QDRC_EVENT_ADDR_WATCH_OFF
                                            | QDRC_EVENT_LINK_IN_DETACHED
                                            | QDRC_EVENT_LINK_OUT_DETACHED,
                                            on_conn_event,
                                            on_link_event,
                                            on_addr_event,
                                            0,
                                            ap);

    core->edge_conn_addr = qcm_edge_conn_addr;
    core->edge_context = ap;

    return ap;
}



void qcm_edge_addr_proxy_final(qcm_edge_addr_proxy_t *ap)
{
    qdrc_event_unsubscribe_CT(ap->core, ap->event_sub);
    free(ap);
}

