import importlib
import logging
import traceback
import threading
import time
import ctypes


def send_execption(thread, exception):
    ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(thread.ident), ctypes.py_object(exception))


class StopThread(Exception):
    pass


class Loadable(threading.Thread):
    def __init__(self, sleep=0, exception_sleep=5):
        super().__init__()
        self.log = logging.getLogger(self.__class__.__name__)
        self._sleep = sleep
        self._exception_sleep = exception_sleep
        self.__stop = False

    def main(self):  # to be overrided
        pass

    def on_stop(self):  # to be overrided
        pass

    def stop(self):
        self.__stop = True

    def run(self):
        while True:
            try:
                self.main()
            except StopThread:
                break
            except Exception:
                self.log.error(traceback.format_exc())
                time.sleep(self._exception_sleep)

            if self.__stop:
                break

            time.sleep(self._sleep)


class ClassInfo:
    def __init__(self, module, instance):
        self.module = module
        self.instance = instance


class DynamicThreadClassLoader:
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)
        self.init_args = {}
        self.classes = {}  # {(module_name, class_name): ClassInfo}
        self.classes_cache = {}

    def set_args(self, init_args):
        '''Add arguments passed to loaded class'''
        self.init_args = init_args

    def start(self, module_name, class_name):
        '''
        Import {module_name} and start {class_name}
        which inherits "Loadable" class
        '''
        key = (module_name, class_name)
        ci = self.classes.get(key)
        if ci:
            raise Exception(f'"{class_name}" is already running.')

        ci = self.classes_cache.get(key)
        if ci:
            module = importlib.reload(ci.module)
        else:
            module = importlib.import_module(module_name)

        instance = getattr(module, class_name)(self.init_args)
        instance.start()
        ci = ClassInfo(module, instance)
        self.classes[key] = ci
        self.classes_cache[key] = ci
        self.log.info(f'start "{class_name}"')

        return True

    def stop(self, module_name, class_name):
        '''Stop {class_name} which is loaded by "load()"'''
        key = (module_name, class_name)
        ci = self.classes.get(key)
        if not ci or not ci.instance:
            raise Exception(f'"{class_name} not found"')
        instance = ci.instance

        if hasattr(instance, 'stop'):
            try:
                instance.stop()
                instance.join(3)
            except Exception:
                instance.log.error(traceback.format_exc())

        if instance.is_alive():
            self.log.warning(f'{class_name} is not responding. '
                             'Sending exception: StopThread')
            send_execption(instance, StopThread)
            instance.join(3)
            if instance.is_alive():
                self.log.error(f'failed to stop "{class_name}"')
                return False

        ci.instance = None
        del self.classes[key]

        if hasattr(instance, 'on_stop'):
            try:
                instance.on_stop()
            except Exception:
                instance.log.error(traceback.format_exc())

        self.log.info(f'stop "{class_name}"')

        return True

    def get_running_classes(self):
        return list(self.classes.keys())
