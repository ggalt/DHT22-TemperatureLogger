from threading import Thread, Event, Timer

global locked
locked = False

class MyTimer(Thread):
    def __init__(self, period, event, func):
        Thread.__init__(self)
        self.period = period
        self.stopped = event
        self.func = func

    def run(self):
        global locked
        while not self.stopped.wait(self.period):
            if locked == False:
                locked = True
                self.func()
                locked = False
            
