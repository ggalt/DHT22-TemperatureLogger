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
        counter = 0
        while not self.stopped.wait(self.period):
            while locked == True and counter < 10:
                sleep(0.5)
                counter += 1

            counter = 0
            if locked == False:
                locked = True
                self.func()
                locked = False
            else:
                print("################## LOCKED ##################")
            
