import testtools

import cuedashboard.queues.tables as tables


class FakeTest(testtools.TestCase):
    def test_foo(self):
        createCluster = tables.CreateCluster()
        self.assertTrue(createCluster.name, "create")