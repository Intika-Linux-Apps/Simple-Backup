
import unittest
from nssbackup.util.log import LogFactory
from nssbackup.util.notifier import Notifier, PynotifyListener, Listener

class TestNotifier(unittest.TestCase):
	"""
	"""
	notifier = None
	
	def setUp(self):
		""
		self.notifier = Notifier()
		
	
	def testPynotify(self):
		" Test Pynotify "
		p = PynotifyListener()
		self.notifier.register(p)
		
		self.notifier.fire("Test message", Listener.PYNOTIFY)
		
	def testNoListener(self):
		"Test No Listener"
		LogFactory.getLogger("Test", level=10)
		self.notifier.fire("Test message", Listener.DEFAULT)
		
		p = PynotifyListener()
		self.notifier.register(p)
		
		self.notifier.fire("Test message", Listener.PYNOTIFY)
		
		self.notifier.unregister(p)
		
		self.notifier.fire("Test message", Listener.PYNOTIFY)
		
		
suite = unittest.TestLoader().loadTestsFromTestCase(TestNotifier)
unittest.TextTestRunner(verbosity=2).run(suite)