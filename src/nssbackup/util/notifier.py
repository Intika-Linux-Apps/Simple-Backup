#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

# Authors :
#	Ouattara Oumar Aziz ( alias wattazoum ) <wattazoum at gmail dot com>

from nssbackup.util.exceptions import SBException, NotifyException
from nssbackup.util.log import LogFactory

class Notifier:
	"""
	""" 
	
	class __Notifier:
		"""
		Internal class to use for implementing the Singleton Design pattern
		"""		
		
		def __init__(self):
			self.listeners = []
			self.logger = LogFactory.getLogger()
		
		def fire(self, message, flag):
			"""
			Fire a message to all registered listeners.
			@param message: The message to send to the listener
			@param flag: The flag to identify the listeners to notify
			@raise NotifyException: If something went wrong
			"""
			self.logger.debug("Firing message : %s" % message)
			for listener in self.listeners :
				self.logger.debug("Trying listener : %r" % listener)
				if listener.isTargeted(flag):
					listener.notify(message)
			
		def register(self, listener):
			"""
			Register a Listener
			"""
			if not isinstance(listener,Listener) : 
				raise NotifyException(_("only object of type Listener can be registered"))
			self.logger.debug("Registering listener : %r" % listener)
			self.listeners.append(listener)
			
		def unregister(self,listener):
			"""
			Unregister a Listener
			"""
			if not isinstance(listener,Listener) : 
				raise NotifyException(_("only object of type Listener can be unregistered"))
			if listener in self.listeners:
				self.logger.debug("Unregistering listener : %r" % listener)
				self.listeners.remove(listener)
			
	__instance = None
	
	logger = None
	
	def __init__(self):
		""" Create singleton instance """
		# Check whether we already have an instance
		if Notifier.__instance is None:
			# Create and remember instance
			Notifier.__instance = Notifier.__Notifier()
			
		# Store instance reference as the only member in the handle
		self.__dict__['_Notifier__instance'] = Notifier.__instance
		
	def __getattr__(self, attr):
		""" Delegate access to implementation """
		return getattr(self.__instance, attr)
	
	def __setattr__(self, attr, value):
		""" Delegate access to implementation """
		return setattr(self.__instance, attr, value)
	
class Listener :
	"""
	"""
	DEFAULT = 1
	PYNOTIFY = 2
	
	def isTargeted(self, flag):
		"""
		@param flag: the flag to use for determining if this Listener is concerned
		@return: True or False 
		"""
		raise SBException("This method should be implemented by the subclasses")
	
	def notify(self, message):
		"""
		Do whatever is needed to do with the message.
		@param message: The message to send to all listener
		@raise NotifyException: 
		"""
		raise SBException("This method should be implemented by the subclasses")

class PynotifyListener(Listener):
	"""
	"""
	
	logger = None
	
	def __init__(self):
		self.logger = LogFactory.getLogger()
		
		self.flags =[Listener.DEFAULT, Listener.PYNOTIFY]
		
	def isTargeted(self,flag):
		if flag in self.flags:
			return True
		else :
			return False
		
	def notify(self, message):
		"""
		"""
		self.logger.debug("Notifying using message : %s" % message)
		try:
			import pynotify
		except Exception, e:
			self.logger.warning(str(e))
			pynotify = False
		
		if pynotify:
			if pynotify.init("NSsbackup"):
				n = pynotify.Notification("NSsbackup", message)
				n.show()
			else:
				self.logger.warning(_("there was a problem initializing the pynotify module"))
		else :
			self.logger.warning(_("there was a problem importing the pynotify module"))
