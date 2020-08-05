from threading import Thread, Event, Timer

class MyTimer(Thread):
    def __init__(self, period, event, func):
        Thread.__init__(self)
        self.period = period
        self.stopped = event
        self.func = func

    def run(self):
        while not self.stopped.wait(self.period):
            self.func()
            
