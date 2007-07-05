from sbackup.util.log import getLogger

class Test:
	
	def __init__(self):
		""
	
	def logsome(self):
		l = getLogger("sbackup.log")

		l.info("Hello World")
		l.debug("Argh")
    
if __name__ == '__main__':
	t = Test()
	t.logsome()