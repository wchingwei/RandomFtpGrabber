
import sys
from queue import Queue
from threading import Event, Thread
import better_exchook
import Persistence
import Logging

kNumWorkers = 5
kMinQueuedActions = kNumWorkers # fill workerQueue always up to N elements, via the watcher thread

if not "mainLoopQueue" in vars():
	mainLoopQueue = Queue()
if not "exitEvent" in vars():
	exitEvent = Event()


def setup():
	import Action
	if not "workerQueue" in globals():
		global workerQueue
		workerQueue = Persistence.load("workerQueue.db", Queue, env=vars(Action))
	if not "currentWork" in globals():
		global currentWork
		currentWork = Persistence.load("currentWork.db", set, env=vars(Action))

	_initWatcherThread()
	_initWorkerThreads()


def queueWork(func):
	workerQueue.put(func)
	workerQueue.save()


def mainLoop():
	while True:
		func = mainLoopQueue.get()
		func()

def workerLoop():
	better_exchook.install()
	while True:
		func = workerQueue.get()
		Logging.log("Next work item: %s" % func)
		currentWork.add(func)
		currentWork.save()
		try:
			func()
		except KeyboardInterrupt:
			return
		except Exception:
			Logging.logException("Worker", *sys.exc_info())
		finally:
			try:
				currentWork.remove(func)
			except Exception as e:
				Logging.log("Error: Dont understand: %s, %r not in %r" % (e, func, currentWork))

def watcherLoop():
	better_exchook.install()
	while not exitEvent.isSet():
		if workerQueue.qsize() >= kMinQueuedActions:
			exitEvent.wait(1)
			continue

		import Action
		func = Action.getNewAction()
		workerQueue.put(func)

if "workers" not in vars():
	workers = []
if "watcher" not in vars():
	watcher = None

def _initWorkerThreads():
	if len(workers) >= kNumWorkers: return
	assert not workers # needs fixing otherwise
	# Move all of the queued entries to the set to eliminate duplicates.
	while not workerQueue.empty():
		currentWork.add(workerQueue.get())
	# Now back to the queue.
	for func in currentWork:
		queueWork(func)
	# And cleanup.
	currentWork.clear()
	currentWork.save()
	# Now init the threads.
	for i in range(kNumWorkers - len(workers)):
		thread = Thread(target=workerLoop, name="Worker %i/%i" % (i + 1, kNumWorkers))
		workers.append(thread)
		thread.daemon = True
		thread.start()

def _initWatcherThread():
	global watcher
	if watcher: return
	watcher = Thread(target=watcherLoop, name="Watcher")
	watcher.daemon = True
	watcher.start()


