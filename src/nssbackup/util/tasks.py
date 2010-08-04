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
#    Jean-Peer Lorenz <peer.loz@gmx.net>

"""This module contains definitions of classes helping to process
worker tasks within separate threads.
"""

import threading

from nssbackup.util import log


class WorkerThread(object):
    """Class that encapsulates a single (long running) thread.
    The current implementation does not support control of the task's
    progress (due to it isn't necessary for tar operations).
    """

    def __init__(self, task):
        """Default constructor.

        @param task: a callable object that actually represents the worker task
        @type task:  callable object
        
        @raise TypeError: in case of type mismatch of given parameters
        """
        self.__task = None
        self.__finish_callback = None
        self.__finish_args = None
        self.__thread = None
        self.__set_task(task)

    def __set_task(self, callback):
        """Private helper method that sets the callback function representing
        the actual worker task.
        
        @param callback: callable object representing the task to perform
        @type callback:  callable object
        
        @return: None
        
        @raise TypeError: If the given parameter is not callable
        """
        if not callable(callback):
            raise TypeError("The given task object object is not callable!")
        self.__task = callback

    def set_finish_callback(self, callback, *args):
        """Sets the given object as callback function/method that is
        invoked after finishing the worker thread. An arbitrary number of
        non-keyword parameters can be given. Since the worker task is
        performed in a separate thread one need to set a callback function
        e.g. for evaluating any results of the task.
        
        The result of the worker task is given as last parameter
        to this callback function, this is even valid for tasks that
        return 'nothing', i.e. None.

        @param callback: callable object that is called after finishing
        @type callback: callable object
        @param args: arbritrary number of parameters given to the callback
                     function
        
        @return: None

        @raise TypeError: If the given callback function is not callable
        """
        if not callable(callback):
            raise TypeError("The given callback object is not callable!")
        self.__finish_callback = callback
        self.__finish_args = args

    def __run_task(self, *args, **kwargs):
        """Private method that executes the worker task and afterwards
        calls the specified finish callback function (if any).
        
        Any exception raised within the worker task is catched and returned
        as result of the task. If no exception occurs the result of the
        worker task is returned as result. To determine if an exception was
        raised within the thread, check the type of the returned result.

        The given keyword and non-keyword parameters are given (as they are)
        to the worker task.
        
        @param args:   non-keyword parameters given to the worker task
        @param kwargs: keyword parameters given to the worker task
        
        @return: None        
        """
        try:
            result = self.__task(*args, **kwargs)
        except Exception, exc:
            # if an exception was raised, use it as the result
            log.LogFactory.getLogger().exception(exc)
            result = exc

        final_args_lst = []
        # if there is a function to call after finishing?
        if self.__finish_callback is not None:
            if self.__finish_args is not None:
                final_args_lst = [ _arg for _arg in self.__finish_args ]
            # append the worker task result to the arguments list
            final_args_lst.append(result)

            # now the final arguments list is converted into a tuple
            final_args = tuple(final_args_lst)
            self.__finish_callback(*final_args)

    def start(self, *args, **kwargs):
        """Public method that starts this worker thread. The given keyword
        and non-keyword parameters are given (as they are) to the worker task.

        @param args:   non-keyword parameters given to the worker task
        @param kwargs: keyword parameters given to the worker task
        
        @return: None
        """
        self.__thread = threading.Thread(target = self.__run_task,
                                          args = args, kwargs = kwargs)
        self.__thread.start()
