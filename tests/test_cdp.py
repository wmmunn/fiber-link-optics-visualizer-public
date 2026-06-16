import unittest

from fiber_optics.cdp import find_cdp_link, parse_cdp_neighbors_detail


DETAIL = """
Device ID: DIST-SW-B.example.local
Entry address(es):
  IP address: 192.0.2.20
Platform: cisco C9300, Capabilities: Switch IGMP
Interface: TenGigabitEthernet1/1/1,  Port ID (outgoing port): TwentyFiveGigE1/0/22
Holdtime : 122 sec

Device ID: ACCESS-SW-01
Platform: cisco C2960XR, Capabilities: Switch IGMP
Interface: GigabitEthernet1/0/48,  Port ID (outgoing port): GigabitEthernet1/0/1
"""

DETAIL_WITH_TRAILER = """
Device ID: edge-gw-a1.example.net(SERIAL123)
Platform: cisco Nexus9000 C93180YC-EX, Capabilities: Switch IGMP
Interface: Ethernet3/31,  Port ID (outgoing port): Ethernet1/49
"""


class CdpTests(unittest.TestCase):
    def test_parses_cdp_neighbors_detail(self) -> None:
        neighbors = parse_cdp_neighbors_detail(DETAIL)

        self.assertEqual(len(neighbors), 2)
        self.assertEqual(neighbors[0].device_id, "DIST-SW-B")
        self.assertEqual(neighbors[0].local_interface, "Te1/1/1")
        self.assertEqual(neighbors[0].remote_interface, "Twe1/0/22")

    def test_finds_expected_link_by_local_interface_and_device(self) -> None:
        neighbor = find_cdp_link(DETAIL, "Te1/1/1", "DIST-SW-B")

        self.assertEqual(neighbor.remote_interface, "Twe1/0/22")

    def test_rejects_missing_expected_neighbor(self) -> None:
        with self.assertRaises(ValueError):
            find_cdp_link(DETAIL, "Te1/1/1", "OTHER-SW")

    def test_trims_domain_and_parenthetical_trailer_from_device_id(self) -> None:
        neighbors = parse_cdp_neighbors_detail(DETAIL_WITH_TRAILER)

        self.assertEqual(len(neighbors), 1)
        self.assertEqual(neighbors[0].device_id, "edge-gw-a1")
        self.assertEqual(neighbors[0].local_interface, "Eth3/31")
        self.assertEqual(neighbors[0].remote_interface, "Eth1/49")


if __name__ == "__main__":
    unittest.main()
