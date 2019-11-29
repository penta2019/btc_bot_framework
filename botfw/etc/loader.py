import importlib
import logging
import sys
import traceback

from .util import run_forever_nonblocking, StopRunForever


class Loadable:
    def __init__(self, sleep=0, exception_sleep=5):
        super().__init__()
        self.log = logging.getLogger(self.__class__.__name__)
        self.__stop = False
        run_forever_nonblocking(
            self.__worker, self.log, sleep, exception_sleep)

    def loop(self):  # to be overrided
        pass

    def on_stop(self):  # to be overrided
        pass

    def stop(self):
        self.__stop = True

    def __worker(self):
        self.loop()
        if self.__stop:
            raise StopRunForever()


class DynamicClassLoader:
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)
        self.classes = {}
        self.class_args = {}

    def add_args(self, dict_args):
        '''Add arguments passed to loaded class'''
        if type(dict_args) is not dict:
            dict_args = dict(dict_args)
        else:
            self.class_args.update(dict_args)

    def load(self, class_name, module_name):
        '''
        Import {module_name} and launch {class_name}
        which inherits "Loadable" class
        '''
        if class_name in self.classes:
            raise Exception(f'"{class_name}" is already running.')

        sys.modules.pop(module_name, None)
        module = importlib.import_module(module_name)
        instance = getattr(module, class_name)(self.class_args)
        instance.start()
        self.classes[class_name] = {
            'module_name': module_name,
            'instance': instance,
        }
        self.log.info(f'start "{class_name}"')
        return True

    def unload(self, class_name):
        '''Stop {class_name} which is loaded by "load()"'''
        if class_name not in self.classes:
            raise Exception(f'"{class_name}" not found')

        class_ = self.classes[class_name]
        instance = class_['instance']
        instance.stop()
        try:
            instance.join(5)
            instance.on_stop()
        except Exception:
            class_.log.error(traceback.format_exc())
        del sys.modules[class_['module_name']]
        del self.classes[class_name]
        self.log.info(f'stop "{class_name}"')
        return True

    def show_classes(self):
        '''Show loaded class names'''
        return ' '.join(self.classes.keys())
