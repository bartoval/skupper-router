#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

import json
from threading import Thread, Event

from proton.handlers import MessagingHandler
from proton.reactor import Container
from test_broker import FakeBroker
from system_test import TestCase, unittest, main_module, Qdrouterd
from system_test import retry, TIMEOUT, wait_port, SkManager, Process
from system_test import CONNECTION_TYPE, PollTimeout
from vanflow_snooper import VFlowSnooperThread, ANY_VALUE


def strip_default_options(options):
    # remove default connection properties added by router to all connections
    defaults = [
        "product",
        "version",
        "qd.conn-id"]

    for key in defaults:
        del options[key]

    return options


class OpenPropertiesBroker(FakeBroker):
    """
    For obtaining open properties on connector connections
    """
    wait = False  # do not block for broker connector setup
    entity = 'connector'

    def __init__(self, router):
        self.open_properties = None
        self._router = router

    def on_connection_opened(self, event):
        self.open_properties = strip_default_options(event.connection.remote_properties)
        super(OpenPropertiesBroker, self).on_connection_opened(event)

    def run(self, host=None, port=None, pf=None):
        if port:
            if pf and pf.lower() == 'ipv6':
                addr = "amqp://[%s]:%s" % (host, port)
            else:
                addr = "amqp://%s:%s" % (host, port)
        else:
            addr = self._router.connector_addresses[0]
        super(OpenPropertiesBroker, self).__init__(url=addr)
        retry(lambda : self.open_properties is not None, delay=0.1)
        self.join()


class OpenPropertiesClient(MessagingHandler):
    """
    For obtaining open properties on listener connections
    """
    wait = True  # wait for broker setup to complete
    entity = 'listener'

    def __init__(self, router):
        super(OpenPropertiesClient, self).__init__()
        self.open_properties = None
        self._router = router

    def on_start(self, event):
        self._conn = event.container.connect(self._addr)

    def on_connection_opened(self, event):
        self.open_properties = strip_default_options(event.connection.remote_properties)
        event.connection.close()

    def run(self, host=None, port=None, pf=None):
        if port:
            wait_port(port, socket_address_family=pf)
            if pf and pf.lower() == 'ipv6':
                self._addr = "amqp://[%s]:%s" % (host, port)
            else:
                self._addr = "amqp://%s:%s" % (host, port)
        else:
            self._addr = self._router.addresses[0]
        Container(self).run()


class OpenPropertiesSender(MessagingHandler):
    """
    A test client that sends a map of test open properties to the router.
    """

    def __init__(self, router_addr, test_props):
        super(OpenPropertiesSender, self).__init__()
        self._test_props = test_props
        self._addr = router_addr
        self._shutdown = False
        self._connected = Event()  # set when TCP connection up (or error)
        self._thread = Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()
        self._connected.wait()

    def on_start(self, event):
        self._reactor = event.reactor
        self._poll_timer = event.reactor.schedule(0.5, PollTimeout(self))
        self._conn = event.container.connect(self._addr, properties=self._test_props)

    def on_connection_opened(self, event):
        self._connected.set()

    def poll_timeout(self):
        # force thread to exit if shutdown flag set
        if self._shutdown:
            self._conn.close()
        else:
            self._poll_timer = self._reactor.schedule(0.5, PollTimeout(self))

    def run(self):
        Container(self, container_id="OPSender").run()

    def join(self):
        self._shutdown = True
        self._thread.join(TIMEOUT)


class OpenPropertiesConfigTest(TestCase):
    """
    Test the openProperties configuration attribute of the Connector and
    Listener configuration entities
    """

    def _valid_properties_check(self, client_class):
        """
        Test a few different valid property maps
        """

        valid_properties = [
            {
                "simple": "string",
            },
            {
                "float": 0.0001,
            },
            {
                "int": -3,
            },
            {
                "bool": True,
            },
            {
                "Null": None,
            },
            {
                "list": [1, 2, "a", None, False, -0.01, "done"]
            },
            {
                "map": {"key": "value"},
            },
            {
                "empty1": {},
            },
            {
                "empty2": [],
            },
            {
                # empty
            },
            # compound + nested
            {
                "string": "string value",
                "integer": 999,
                "map" : {
                    "map-float": 3.14,
                    "map-list": [1, "A", 0.02],
                    "map-map": {"key1": "string",
                                "key2": 1,
                                "key3": True,
                                "key4": False,
                                "key5": None,
                                "key6": ["x", False, "z", None]
                                },
                },
                "None": None,
                "True": True,
                "False": False,
                "list": [1,
                         2,
                         {"a": 1,
                          "b": None,
                          "c": True,
                          "d": "end"},
                         "text",
                         3]
            }
        ]

        i = 0
        for op in valid_properties:
            name = "Router%d" % i
            i += 1
            config = [('router', {'id': name}),
                      (client_class.entity, {
                          'port': self.tester.get_port(),
                          'openProperties': op
                      })
                      ]

            router = self.tester.qdrouterd(name, Qdrouterd.Config(config),
                                           wait=client_class.wait)

            client = client_class(router)
            client.run()
            self.assertEqual(op, client.open_properties)
            router.teardown()

    def test_01_verify_listener_properties(self):
        self._valid_properties_check(OpenPropertiesClient)

    def test_02_verify_connector_properties(self):
        self._valid_properties_check(OpenPropertiesBroker)


class OpenPropertiesQdManageTest(TestCase):
    """
    Tests creating openProperties via skmanage tool
    """

    def _valid_properties_check(self, client_class):
        """
        Test a few different valid property maps
        """

        valid_properties = [
            {
                # empty
            },
            {
                "simple": "string",
                "int": -3,
                "bool": True,
                "Null": None,
                "list": [1, 2, "a", None, False, "done"],
                "map": {"key": "value"},
            },
            # compound + nested
            {
                "string": "string value",
                "integer": 999,
                "map" : {
                    "map-bool": False,
                    "map-list": [1, "A", None],
                    "map-map": {"key1": "string",
                                "key2": 1,
                                "key3": True,
                                "key4": False,
                                "key5": None,
                                "key6": ["x", False, "z", None]
                                },
                },
                "None": None,
                "True": True,
                "False": False,
                "list": [1,
                         2,
                         {"a": 1,
                          "b": None,
                          "c": True,
                          "d": "end"},
                         "text",
                         3]
            }
        ]

        i = 0
        for op in valid_properties:
            name = "Router%d" % i
            i += 1
            config = [('router', {'id': name}),
                      ('listener', {
                          'port': self.tester.get_port()})
                      ]

            router = self.tester.qdrouterd(name,
                                           Qdrouterd.Config(config),
                                           wait=True)
            new_port = self.tester.get_port()
            input = json.dumps({'port': new_port,
                                'name': "%s%d" % (client_class.entity, i),
                                'openProperties':
                                op})

            cmd = "CREATE --type=io.skupper.router.%s --stdin" % client_class.entity
            output = SkManager()(cmd=cmd,
                                 address=router.addresses[0],
                                 input=input,
                                 timeout=TIMEOUT)
            rc = json.loads(output)
            self.assertIn("openProperties", rc)
            self.assertEqual(op, rc["openProperties"])

            client = client_class(router)
            client.run(host=rc.get("host"), port=new_port,
                       pf=rc.get("socketAddressFamily", "IPv4"))
            router.teardown()

    def test_01_verify_listener_properties(self):
        self._valid_properties_check(OpenPropertiesClient)

    def test_02_verify_connector_properties(self):
        self._valid_properties_check(OpenPropertiesBroker)


class OpenPropertiesBadConfigTest(TestCase):
    """
    Ensure invalid open properties configurations are detected
    """

    def _find_in_output(self, filename, error_msg):
        with open(filename, 'r') as out_file:
            for line in out_file:
                if error_msg in line:
                    return True
        return False

    def test_01_invalid_properties_check(self):
        """
        Test a few different invalid property maps
        """
        invalid_properties = [
            (
                {9: "invalid key type"},
                "Expecting property name"
            ),
            (
                [1, 2, "not a map"],
                "Properties must be a map"
            ),
            (
                "I am bad",
                "Properties must be a map"
            ),
            (
                {"nonascii\u2588": 1},
                "Property keys must be ASCII encoded"
            ),
            (
                {None: None},
                "Expecting property name"
            ),
            (
                {'product': "reserved keyword"},
                "ValidationError: Reserved key 'product' not allowed in openProperties"
            ),
            (
                {'qd.FOO': "reserved prefix"},
                "ValidationError: Reserved key 'qd.FOO' not allowed in openProperties"
            ),
            (
                {'x-opt-qd.BAR': "reserved prefix"},
                "ValidationError: Reserved key 'x-opt-qd.BAR' not allowed in openProperties"
            )
        ]

        i = 0
        for op, err in invalid_properties:
            name = "Router%d" % i
            i += 1
            config = [('router', {'id': name}),
                      ('listener', {
                          'port': self.tester.get_port(),
                          'openProperties': op
                      })
                      ]

            router = self.tester.qdrouterd(name, Qdrouterd.Config(config),
                                           wait=False,
                                           expect=Process.EXIT_FAIL)
            router.wait(timeout=TIMEOUT)
            self.assertTrue(self._find_in_output(router.outfile + '.out', err))

    def test_02_invalid_role_check(self):
        """
        Ensure that attempting to set openProperties on inter-router/edge
        connections fails
        """
        for role in ['inter-router', 'edge']:
            for entity in ['listener', 'connector']:
                name = "%s-%s" % (entity, role)

                config = [('router', {'id': name,
                                      'mode': 'interior'}),
                          (entity, {
                              'role': role,
                              'port': self.tester.get_port(),
                              'openProperties': {
                                  "foo": "bar",
                              }
                          })
                          ]

                router = self.tester.qdrouterd(name, Qdrouterd.Config(config),
                                               wait=False,
                                               expect=Process.EXIT_FAIL)
                router.wait(timeout=TIMEOUT)
                err = "ValidationError: openProperties not allowed for role %s" % role
                self.assertTrue(self._find_in_output(router.outfile + '.out', err))


def get_log_line(filename, pattern):
    with open(filename, 'r') as out_file:
        for line in out_file:
            if pattern in line:
                return line
    return None


class OpenPropertiesInterRouterTest(TestCase):
    """
    Verifies Open Properties passed between routers
    """
    @classmethod
    def setUpClass(cls):
        """Start a router and a messenger"""
        super(OpenPropertiesInterRouterTest, cls).setUpClass()

        ir_port = cls.tester.get_port()
        cls.RouterA = cls.tester.qdrouterd("RouterA",
                                           Qdrouterd.Config([
                                               ('router', {'mode': 'interior',
                                                           'id': 'RouterA'}),
                                               ('listener', {'port':
                                                             cls.tester.get_port()}),
                                               ('listener', {'role':
                                                             'inter-router',
                                                             'port':
                                                             ir_port})]),
                                           wait=False)
        cls.RouterB = cls.tester.qdrouterd("RouterB",
                                           Qdrouterd.Config([
                                               ('router', {'mode': 'interior',
                                                           'id': 'RouterB'}),
                                               ('listener', {'port':
                                                             cls.tester.get_port()}),
                                               ('connector', {'role':
                                                              'inter-router',
                                                              'port':
                                                              ir_port})]),
                                           wait=True)
        cls.RouterA.wait_router_connected('RouterB')
        cls.RouterB.wait_router_connected('RouterA')

    def test_01_check_annotations(self):
        """
        Verify the router annotations version
        """
        a_logfile = self.RouterA.logfile_path
        b_logfile = self.RouterB.logfile_path
        self.RouterA.teardown()
        self.RouterB.teardown()

        log_msg = "ROUTER (debug) Remote router annotations version: 2"
        line = get_log_line(a_logfile, log_msg)
        self.assertIsNotNone(line)

        line = get_log_line(b_logfile, log_msg)
        self.assertIsNotNone(line)


class OpenPropertiesEdgeRouterTest(TestCase):
    """
    Verifies Open Properties passed between interior and edge routers
    """
    @classmethod
    def setUpClass(cls):
        """Start a router and a messenger"""
        super(OpenPropertiesEdgeRouterTest, cls).setUpClass()

        ir_port = cls.tester.get_port()
        cls.RouterA = cls.tester.qdrouterd("RouterA",
                                           Qdrouterd.Config([
                                               ('router', {'mode': 'interior',
                                                           'id': 'RouterA'}),
                                               ('listener', {'port':
                                                             cls.tester.get_port()}),
                                               ('listener', {'role':
                                                             'edge',
                                                             'port':
                                                             ir_port})]),
                                           wait=False)
        cls.RouterB = cls.tester.qdrouterd("RouterB",
                                           Qdrouterd.Config([
                                               ('router', {'mode': 'edge',
                                                           'id': 'RouterB'}),
                                               ('listener', {'port':
                                                             cls.tester.get_port()}),
                                               ('connector', {'role':
                                                              'edge',
                                                              'port':
                                                              ir_port})]),
                                           wait=True)
        cls.RouterA.wait_ready()
        mgmt = cls.RouterA.management
        while True:
            results = mgmt.query(type=CONNECTION_TYPE,
                                 attribute_names=['container']).get_dicts()
            if any(c['container'] == 'RouterB' for c in results):
                break

    def test_01_check_vflow_linkage(self):
        """
        Verify that the LINK record on the edge has the ROUTER_ACCESS id of the listener on the interior
        """
        snooper_thread = VFlowSnooperThread(self.RouterA.addresses[0], verbose=True)
        expected = {
            'RouterA': [('ROUTER_ACCESS', {'LINK_COUNT': 1,
                                           'ROLE': 'edge',
                                           'IDENTITY': ANY_VALUE})],
            'RouterB': [('LINK', {'PEER': ANY_VALUE,
                                  'OPER_STATUS': 'up',
                                  'ROLE': 'edge'})]
        }
        success = retry(lambda: snooper_thread.match_records(expected), delay=2)
        self.assertTrue(success, f"Failed to match records {snooper_thread.get_results()}")

        ##
        ## Verify that RouterB LINK's PEER references RouterA ROUTER_ACCESS
        ##
        b_links = snooper_thread.get_router_records('RouterB', record_type='LINK')
        self.assertEqual(1, len(b_links), f"Expected one LINK {b_links}")
        a_ras = snooper_thread.get_router_records('RouterA', record_type='ROUTER_ACCESS')
        self.assertEqual(1, len(a_ras), f"Expected one ROUTER_ACCESS {a_ras}")
        self.assertEqual(b_links[0]['PEER'], a_ras[0]['IDENTITY'], "Invalid peer linkage")

    def test_02_check_annotations(self):
        """
        Verify the router annotations version
        """
        a_logfile = self.RouterA.logfile_path
        b_logfile = self.RouterB.logfile_path
        self.RouterA.teardown()
        self.RouterB.teardown()

        log_msg = "ROUTER (debug) Remote router annotations version: 2"
        line = get_log_line(a_logfile, log_msg)
        self.assertIsNotNone(line)

        line = get_log_line(b_logfile, log_msg)
        self.assertIsNotNone(line)


class OpenPropertiesMgmtTest(TestCase):
    """
    Verifies that a management read of a connection has the expected open properties
    """
    @classmethod
    def setUpClass(cls):
        super(OpenPropertiesMgmtTest, cls).setUpClass()

        cls.RouterA = cls.tester.qdrouterd("RouterA",
                                           Qdrouterd.Config([
                                               ('router', {'mode': 'interior',
                                                           'id': 'RouterA'}),
                                               ('listener', {'port':
                                                             cls.tester.get_port()})
                                           ]),
                                           wait=True)

    def test_01_zero_values(self):
        """
        Verify that attributes with zero values are present in the open
        properties. See github issue #1773
        """
        mgmt = self.RouterA.management
        test_maps = [{"Attribute1": "A String",
                      "Attribute2": 1,
                      "Attribute3": 42},
                     {"Thing1": 1,
                      "Thing0": 0,
                      "Thing2": 2},
                     {"X": "",
                      "Y": 7,
                      "Z": 0}]

        for test in test_maps:
            client = OpenPropertiesSender(self.RouterA.addresses[0], test)
            conns = mgmt.query(type=CONNECTION_TYPE).get_dicts()
            for conn in conns:
                # find the test client's connection
                if conn['container'] == "OPSender":
                    self.assertEqual(test, conn['properties'])
                    break
            client.join()

    def test_02_malformed_maps(self):
        """
        Verify that maps that are not valid open properties are ignored by the
        router.
        """
        mgmt = self.RouterA.management
        test_maps = [{"Ok1": 2, "Bad": None, "Bad2": 7, "Bad3": "?"},
                     {"Ok1": 2, 7: "invalid", "Bad2": 7, "Bad3": "?"}]

        # Expect that the first entry "Ok1" is parsed but parsing stops due to
        # the next entry being invalid
        for test in test_maps:
            client = OpenPropertiesSender(self.RouterA.addresses[0], test)
            conns = mgmt.query(type=CONNECTION_TYPE).get_dicts()
            for conn in conns:
                # find the test client's connection
                if conn['container'] == "OPSender":
                    self.assertEqual({"Ok1": 2}, conn['properties'])
                    break
            client.join()


if __name__ == '__main__':
    unittest.main(main_module())
