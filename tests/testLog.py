from nssbackup.util.log import LogFactory

class Test:
	"""
	@todo: Add tests for different log levels etc.!
	"""
	
	def __init__(self):
		""
	
	def logsome(self):
		l = LogFactory.getLogger("TestLogger", "sbackup.log")

		l.info("Hello World")
		l.debug("Argh")
		
		l = LogFactory.getLogger("TestLogger1", "sbackup.log")

		l.info("Hello World Log 1")
		l.error("Argh")

if __name__ == '__main__':
	t = Test()
	t.logsome()