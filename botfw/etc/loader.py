import importlib
import logging
import sys
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
        self._event = threading.Event()
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

            self._event.clear()
            self._event.wait(self._sleep)


class ClassInfo:
    def __init__(self, module_name, instance):
        self.module_name = module_name
        self.instance = instance


class DynamicThreadClassLoader:
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)
        self.loaded_classes = {}  # {'class_name': ClassInfo}
        self.init_args = {}

    def add_args(self, dict_args):
        '''Add arguments passed to loaded class'''
        self.init_args.update(dict_args)

    def load(self, module_name, class_name):
        '''
        Import {module_name} and launch {class_name}
        which inherits "Loadable" class
        '''
        if class_name in self.loaded_classes:
            raise Exception(f'"{class_name}" is already running.')

        sys.modules.pop(module_name, None)
        module = importlib.import_module(module_name)
        instance = getattr(module, class_name)(self.init_args)
        instance.start()
        self.loaded_classes[class_name] = ClassInfo(module_name, instance)
        self.log.info(f'start "{class_name}"')

        return True

    def unload(self, class_name):
        '''Stop {class_name} which is loaded by "load()"'''
        if class_name not in self.loaded_classes:
            raise Exception(f'"{class_name}" not found')

        ci = self.loaded_classes[class_name]
        instance = ci.instance
        instance.stop()
        instance.join(5)
        if instance.is_alive():
            self.log.warning(f'{class_name} is not responding. '
                             'Sending exception: StopThread')
            send_execption(instance, StopThread)
            instance.join(3)
            if instance.is_alive():
                self.log.error(f'failed to stop "{class_name}"')
                return False

        try:
            instance.on_stop()
        except Exception:
            instance.log.error(traceback.format_exc())

        del sys.modules[ci.module_name]
        del self.loaded_classes[class_name]
        self.log.info(f'stop "{class_name}"')

        return True

    def show_loaded_classes(self):
        '''Show loaded class names'''
        return ' '.join(self.loaded_classes.keys())
