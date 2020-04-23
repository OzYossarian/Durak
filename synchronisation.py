import threading


class OverwritableSlot:
    def __init__(self):
        self.value = None
        self.mutex = MultiReleaseSempahore(down=False)
        self.slotFull = MultiReleaseSempahore(down=True)

    def send(self, value):
        self.mutex.acquire()
        self.value = value
        self.slotFull.release()
        self.mutex.release()

    def receive(self):
        self.slotFull.acquire()
        result = self.value
        return result


class MultiReleaseSempahore:
    def __init__(self, down):
        self.semaphore = threading.BoundedSemaphore(value=1)
        # Set the semaphore to the initial value
        if down:
            self.semaphore.acquire()

    def release(self):
        try:
            self.semaphore.release()
        except ValueError:
            # This is fine.
            pass

    def acquire(self):
        self.semaphore.acquire()


class FoldBarrier:
    def __init__(self, parties, f, initialValue):
        self.parties = parties
        self.f = f
        self.initialValue = initialValue

        self.value = initialValue
        self.mutex = MultiReleaseSempahore(down=False)
        self.barrier = MultiReleaseSempahore(down=True)
        self.waiting = 0

    def wait(self, value):
        self.mutex.acquire()
        self.value = self.f(self.value, value)

        if self.waiting == self.parties - 1:
            # Start releasing waiting processes
            result = self.value
            self.barrier.release()
        else:
            self.waiting += 1
            self.mutex.release()
            # Wait til everyone has called wait()
            self.barrier.acquire()

            result = self.value
            self.waiting -= 1
            if self.waiting > 0:
                # Release another waiting process
                self.barrier.release()
            else:
                # Reset the barrier for the next round
                self.value = self.initialValue
                self.mutex.release()

        return result


def AndBarrier(parties):
    return FoldBarrier(parties, lambda x, y: x and y, True)








