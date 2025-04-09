import pickle
import uuid
import time
import numpy as np
import redis
import traceback
import logging
import json
import datetime
import base64
import multiprocessing
import os

# Настройка логирования
import os

# Создаем директорию logs, если она не существует
os.makedirs('logs', exist_ok=True)

# Функция для настройки логирования
def setup_logging(process_name='main'):
    """
    Настраивает логирование для текущего процесса
    
    Args:
        process_name: имя процесса для идентификации в логах
    """
    # Создаем форматтер с указанием процесса
    formatter = logging.Formatter(
        f'%(asctime)s [{process_name}] [%(levelname)s] %(message)s'
    )
    
    # Создаем обработчики
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    file_handler = logging.FileHandler(os.path.join('logs', f'redis_proxy_{process_name}.log'))
    file_handler.setFormatter(formatter)
    
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Удаляем существующие обработчики
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Добавляем новые обработчики
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    return logging.getLogger('redis_proxy')

# Настраиваем логирование для основного процесса
logger = setup_logging('main')

# Класс для безопасной сериализации объектов
class SafeSerializer:
    """Безопасный сериализатор объектов с обработкой ошибок"""
    
    @staticmethod
    def dumps(obj):
        """
        Безопасно сериализует объект
        
        Args:
            obj: объект для сериализации
            
        Returns:
            bytes: сериализованный объект
        """
        try:
            # Пробуем использовать стандартный pickle
            return pickle.dumps(obj)
        except (pickle.PickleError, TypeError, AttributeError) as e:
            logger.warning(f"Не удалось сериализовать объект типа {type(obj).__name__}: {str(e)}")
            
            # Для numpy массивов используем специальную сериализацию
            if isinstance(obj, np.ndarray):
                return pickle.dumps({
                    "__type__": "numpy.ndarray",
                    "data": base64.b64encode(obj.tobytes()).decode('ascii'),
                    "dtype": str(obj.dtype),
                    "shape": obj.shape
                })
            
            # Для других объектов возвращаем строковое представление
            return pickle.dumps({
                "__type__": "unpicklable",
                "repr": repr(obj),
                "str": str(obj),
                "type": str(type(obj))
            })
    
    @staticmethod
    def loads(data):
        """
        Безопасно десериализует объект
        
        Args:
            data: сериализованные данные
            
        Returns:
            object: десериализованный объект
        """
        try:
            obj = pickle.loads(data)
            
            # Проверяем, является ли объект специальным типом
            if isinstance(obj, dict) and "__type__" in obj:
                if obj["__type__"] == "numpy.ndarray":
                    # Восстанавливаем numpy массив
                    array_data = base64.b64decode(obj["data"])
                    dtype = np.dtype(obj["dtype"])
                    return np.frombuffer(array_data, dtype=dtype).reshape(obj["shape"])
                
                elif obj["__type__"] == "unpicklable":
                    # Возвращаем информацию о непикализуемом объекте
                    return UnpicklableObject(obj["repr"], obj["str"], obj["type"])
            
            return obj
        except Exception as e:
            logger.error(f"Ошибка при десериализации: {str(e)}")
            return UnpicklableObject(f"ERROR: {str(e)}", f"ERROR: {str(e)}", "error")


class UnpicklableObject:
    """Представление объекта, который не удалось сериализовать"""
    
    def __init__(self, repr_str, str_str, type_str):
        self.repr_str = repr_str
        self.str_str = str_str
        self.type_str = type_str
    
    def __repr__(self):
        return f"<Непикализуемый объект типа {self.type_str}: {self.repr_str}>"
    
    def __str__(self):
        return self.str_str


class LazyProxy:
    """Прокси для ленивой загрузки объектов"""
    
    def __init__(self, proxy_instance, path):
        self._proxy_instance = proxy_instance
        self._path = path
        self._loaded = False
        self._value = None
    
    def _load(self):
        """Загружает значение с сервера при первом обращении"""
        if not self._loaded:
            self._value = self._proxy_instance._send_request(
                'getattr',
                self._proxy_instance._class_name,
                self._proxy_instance._instance_id,
                self._path,
                [],
                {}
            )
            self._loaded = True
        return self._value
    
    def __getattr__(self, name):
        """Получение атрибута"""
        # Создаем новый прокси для вложенного атрибута
        return LazyProxy(self._proxy_instance, f"{self._path}.{name}")
    
    def __call__(self, *args, **kwargs):
        """Вызов метода"""
        return self._proxy_instance._send_request(
            'call',
            self._proxy_instance._class_name,
            self._proxy_instance._instance_id,
            self._path,
            args,
            kwargs
        )
    
    def __repr__(self):
        return repr(self._load())
    
    def __str__(self):
        return str(self._load())
    
    # Другие магические методы для работы с объектом
    def __int__(self):
        return int(self._load())
    
    def __float__(self):
        return float(self._load())
    
    def __bool__(self):
        return bool(self._load())
    
    def __getitem__(self, key):
        value = self._load()
        if hasattr(value, '__getitem__'):
            return value[key]
        raise TypeError(f"Объект типа {type(value).__name__} не поддерживает индексацию")
    
    def __iter__(self):
        value = self._load()
        if hasattr(value, '__iter__'):
            return iter(value)
        raise TypeError(f"Объект типа {type(value).__name__} не является итерируемым")
    
    def __len__(self):
        value = self._load()
        if hasattr(value, '__len__'):
            return len(value)
        raise TypeError(f"Объект типа {type(value).__name__} не имеет длины")
    
    # Арифметические операции
    def __add__(self, other):
        return self._load() + other
    
    def __radd__(self, other):
        return other + self._load()
    
    def __sub__(self, other):
        return self._load() - other
    
    def __rsub__(self, other):
        return other - self._load()
    
    def __mul__(self, other):
        return self._load() * other
    
    def __rmul__(self, other):
        return other * self._load()
    
    def __truediv__(self, other):
        return self._load() / other
    
    def __rtruediv__(self, other):
        return other / self._load()
    
    # Метод для явного получения значения
    def get_value(self):
        return self._load()

class RedisProxyServer:
    """Сервер для проксирования классов через Redis"""
    
    def __init__(self, classes, redis_host='localhost', redis_port=6379, redis_db=0, auto_create_instances=True):
        """
        Инициализация сервера
        
        Args:
            classes: список классов, которые будут доступны через прокси
            redis_host: хост Redis сервера
            redis_port: порт Redis сервера
            redis_db: номер базы данных Redis
            auto_create_instances: автоматически создавать экземпляры, если они не существуют
        """
        self.classes = {cls.__name__: cls for cls in classes}
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        self.instances = {}
        self.running = False
        self.auto_create_instances = auto_create_instances
        self.run()
        
    def start(self):
        """Запуск сервера"""
        self.running = True
        logger.info("Сервер запущен и готов принимать запросы")
        
    def stop(self):
        """Остановка сервера"""
        self.running = False
        logger.info("Сервер остановлен")
        
    def process_one_request(self):
        """Обработка одного запроса"""
        if not self.running:
            return False
            
        try:
            # Получаем запрос из очереди запросов
            request = self.redis_client.blpop('request_queue', timeout=1)
            if request is None:
                return True
            
            # Распаковываем запрос
            _, request_data = request
            request_id, action, class_name, instance_id, method_name, args, kwargs = pickle.loads(request_data)
                
            # Логируем полученный запрос
            log_data = {
                'timestamp': datetime.datetime.now().isoformat(),
                'direction': 'RECEIVED',
                'request_id': request_id,
                'action': action,
                'class_name': class_name,
                'instance_id': instance_id,
                'method_name': method_name,
                'args': str(args)[:100] if args else None,  # Ограничиваем длину для логов
                'kwargs': str(kwargs)[:100] if kwargs else None
            }
            logger.info(f"SERVER RECEIVED: {json.dumps(log_data, ensure_ascii=False)}")
            
            response = None
            error = None
            
            try:
                if action == 'create':
                    # Создание нового экземпляра класса
                    if class_name not in self.classes:
                        raise ValueError(f"Класс {class_name} не зарегистрирован на сервере")
                    
                    instance = self.classes[class_name](*args, **kwargs)
                    self.instances[instance_id] = instance
                    response = True
                    
                elif action == 'call':
                    # Вызов метода экземпляра
                    if instance_id not in self.instances:
                        if self.auto_create_instances and class_name in self.classes:
                            # Автоматически создаем экземпляр, если он не существует
                            logger.warning(f"Экземпляр с ID {instance_id} не найден. Создаем новый экземпляр класса {class_name}.")
                            self.instances[instance_id] = self.classes[class_name]()
                        else:
                            raise ValueError(f"Экземпляр с ID {instance_id} не найден")
                    
                    instance = self.instances[instance_id]
                    
                    # Получаем метод или атрибут по имени
                    attr = instance
                    for part in method_name.split('.'):
                        attr = getattr(attr, part)
                    
                    # Если это вызываемый объект, вызываем его
                    if callable(attr):
                        response = attr(*args, **kwargs)
                    else:
                        response = attr
                        
                elif action == 'getattr':
                    # Получение атрибута экземпляра
                    if instance_id not in self.instances:
                        if self.auto_create_instances and class_name in self.classes:
                            # Автоматически создаем экземпляр, если он не существует
                            logger.warning(f"Экземпляр с ID {instance_id} не найден. Создаем новый экземпляр класса {class_name}.")
                            self.instances[instance_id] = self.classes[class_name]()
                        else:
                            raise ValueError(f"Экземпляр с ID {instance_id} не найден")
                    
                    instance = self.instances[instance_id]
                    
                    # Получаем атрибут по имени
                    attr = instance
                    for part in method_name.split('.'):
                        attr = getattr(attr, part)
                    
                    response = attr
                    
                elif action == 'setattr':
                    # Установка атрибута экземпляра
                    if instance_id not in self.instances:
                        if self.auto_create_instances and class_name in self.classes:
                            # Автоматически создаем экземпляр, если он не существует
                            logger.warning(f"Экземпляр с ID {instance_id} не найден. Создаем новый экземпляр класса {class_name}.")
                            self.instances[instance_id] = self.classes[class_name]()
                        else:
                            raise ValueError(f"Экземпляр с ID {instance_id} не найден")
                    
                    instance = self.instances[instance_id]
                    
                    # Разбиваем имя атрибута на части
                    parts = method_name.split('.')
                    
                    # Получаем объект, которому нужно установить атрибут
                    obj = instance
                    for part in parts[:-1]:
                        obj = getattr(obj, part)
                    
                    # Устанавливаем атрибут
                    setattr(obj, parts[-1], args[0])
                    response = True
                    
                elif action == 'delete':
                    # Удаление экземпляра
                    if instance_id in self.instances:
                        del self.instances[instance_id]
                    response = True
                    
            except Exception as e:
                error = {
                    'type': type(e).__name__,
                    'message': str(e),
                    'traceback': traceback.format_exc()
                }
            
            # Логируем ответ перед отправкой
            log_data = {
                'timestamp': datetime.datetime.now().isoformat(),
                'direction': 'SENT',
                'request_id': request_id,
                'success': error is None,
                'response_type': type(response).__name__ if response is not None else None,
                'error': error['type'] if error else None
            }
            logger.info(f"SERVER SENT: {json.dumps(log_data, ensure_ascii=False)}")
            
            # Отправляем ответ, используя безопасную сериализацию
            try:
                response_data = SafeSerializer.dumps((response, error))
                self.redis_client.rpush(f'response_{request_id}', response_data)
            except Exception as e:
                logger.error(f"Ошибка при сериализации ответа: {str(e)}")
                # Отправляем ошибку вместо ответа
                error = {
                    'type': 'SerializationError',
                    'message': f"Не удалось сериализовать ответ: {str(e)}",
                    'traceback': traceback.format_exc()
                }
                response_data = SafeSerializer.dumps((None, error))
                self.redis_client.rpush(f'response_{request_id}', response_data)
            
        except Exception as e:
            logger.error(f"Критическая ошибка в сервере: {e}")
            logger.error(traceback.format_exc())
            return True
            
    def run(self):
        """Запуск сервера в бесконечном цикле"""
        # Настраиваем логирование для серверного процесса
        global logger
        logger = setup_logging('server')
        logger.info("Настроено логирование для серверного процесса")
        
        self.start()
        try:
            while self.running:
                self.process_one_request()
        except KeyboardInterrupt:
            logger.info("Получен сигнал прерывания, останавливаем сервер")
        finally:
            self.stop()


class RedisProxy:
    """Фабрика для создания прокси-классов"""
    
    @staticmethod
    def create(cls, redis_host='localhost', redis_port=6379, redis_db=0, timeout=30, max_retries=3):
        """
        Создание прокси-класса
        
        Args:
            cls: класс, для которого создается прокси
            redis_host: хост Redis сервера
            redis_port: порт Redis сервера
            redis_db: номер базы данных Redis
            timeout: таймаут ожидания ответа от сервера (в секундах)
            max_retries: максимальное количество повторных попыток при ошибке
            
        Returns:
            Прокси-класс
        """
        # Создаем объект конфигурации
        config = {
            'class_name': cls.__name__,
            'redis_client': redis.Redis(host=redis_host, port=redis_port, db=redis_db),
            'timeout': timeout,
            'max_retries': max_retries
        }
        
        # Создаем прокси-класс
        proxy_cls = type(
            f"{cls.__name__}Proxy",
            (),
            {
                "_proxy_config": config,
                "__init__": RedisProxy._create_init(),
                "__getattr__": RedisProxy._create_getattr(),
                "__setattr__": RedisProxy._create_setattr(),
                "__del__": RedisProxy._create_del(),
            }
        )
        
        return proxy_cls
    
    @staticmethod
    def _create_init():
        """Создает метод __init__ для прокси-класса"""
        def __init__(self, *args, **kwargs):
            # Сохраняем информацию о Redis-клиенте из конфигурации класса
            self._redis_client = self.__class__._proxy_config['redis_client']
            self._timeout = self.__class__._proxy_config['timeout']
            self._max_retries = self.__class__._proxy_config['max_retries']
            self._class_name = self.__class__._proxy_config['class_name']
            
            # Генерируем уникальный ID для экземпляра
            self._instance_id = str(uuid.uuid4())
            
            # Добавляем метод _send_request к экземпляру
            self._send_request = _send_request.__get__(self, self.__class__)
            
            # Создаем экземпляр на сервере
            self._send_request('create', self._class_name, self._instance_id, '', args, kwargs)
            
            # Сохраняем имена специальных атрибутов, чтобы не проксировать их
            self._special_attrs = {
                '_redis_client', '_timeout', '_max_retries', '_instance_id', 
                '_class_name', '_special_attrs', '_send_request'
            }
        
        return __init__
    
    @staticmethod
    def _create_getattr():
        """Создает метод __getattr__ для прокси-класса"""
        def __getattr__(self, name):
            # Создаем ленивый прокси для метода или атрибута
            return LazyProxy(self, name)
        
        return __getattr__
    
    @staticmethod
    def _create_setattr():
        """Создает метод __setattr__ для прокси-класса"""
        def __setattr__(self, name, value):
            if name.startswith('_') or hasattr(self, '_special_attrs') and name in self._special_attrs:
                # Для специальных атрибутов используем обычную установку
                object.__setattr__(self, name, value)
            else:
                # Для обычных атрибутов отправляем запрос на сервер
                self._send_request('setattr', self._class_name, self._instance_id, name, [value], {})
        
        return __setattr__
    
    @staticmethod
    def _create_del():
        """Создает метод __del__ для прокси-класса"""
        def __del__(self):
            try:
                # Удаляем экземпляр на сервере
                self._send_request('delete', self._class_name, self._instance_id, '', [], {})
            except:
                pass
        
        return __del__


# Класс ProxyAttribute заменен на LazyProxy


def _send_request(self, action, class_name, instance_id, method_name, args, kwargs):
    """
    Отправка запроса на сервер и получение ответа
    
    Args:
        action: тип действия ('create', 'call', 'getattr', 'setattr', 'delete')
        class_name: имя класса
        instance_id: ID экземпляра
        method_name: имя метода или атрибута
        args: позиционные аргументы
        kwargs: именованные аргументы
        
    Returns:
        Результат выполнения запроса
    """
    request_id = str(uuid.uuid4())
    
    # Логируем запрос перед отправкой
    log_data = {
        'timestamp': datetime.datetime.now().isoformat(),
        'direction': 'SENT',
        'request_id': request_id,
        'action': action,
        'class_name': class_name,
        'instance_id': instance_id,
        'method_name': method_name,
        'args': str(args)[:100] if args else None,  # Ограничиваем длину для логов
        'kwargs': str(kwargs)[:100] if kwargs else None
    }
    logger.info(f"CLIENT SENT: {json.dumps(log_data, ensure_ascii=False)}")
    
    # Подготавливаем данные запроса, используя безопасную сериализацию
    try:
        request_data = SafeSerializer.dumps((request_id, action, class_name, instance_id, method_name, args, kwargs))
    except Exception as e:
        logger.error(f"Ошибка при сериализации запроса: {str(e)}")
        raise ValueError(f"Не удалось сериализовать запрос: {str(e)}")
    
    retries = 0
    while retries < self._max_retries:
        try:
            # Отправляем запрос
            self._redis_client.rpush('request_queue', request_data)
            
            # Ждем ответа
            response_key = f'response_{request_id}'
            response = self._redis_client.blpop(response_key, timeout=self._timeout)
            
            if response is None:
                # Таймаут - возможно, сервер был перезапущен
                retries += 1
                logger.warning(f"Таймаут при ожидании ответа. Повторная попытка {retries}/{self._max_retries}")
                continue
            
            # Распаковываем ответ, используя безопасную десериализацию
            _, response_data = response
            result, error = SafeSerializer.loads(response_data)
            
            # Логируем полученный ответ
            log_data = {
                'timestamp': datetime.datetime.now().isoformat(),
                'direction': 'RECEIVED',
                'request_id': request_id,
                'success': error is None,
                'response_type': type(result).__name__ if result is not None else None,
                'error': error['type'] if error else None
            }
            logger.info(f"CLIENT RECEIVED: {json.dumps(log_data, ensure_ascii=False)}")
            
            # Если произошла ошибка на сервере, воссоздаем ее на клиенте
            if error:
                logger.error(f"Ошибка на сервере: {error['type']}: {error['message']}")
                logger.error(error['traceback'])
                raise Exception(f"{error['type']}: {error['message']}")
            
            return result
            
        except Exception as e:
            if isinstance(e, redis.exceptions.ConnectionError):
                # Проблема с подключением к Redis
                retries += 1
                logger.error(f"Ошибка подключения к Redis: {str(e)}. Повторная попытка {retries}/{self._max_retries}")
                time.sleep(1)
            else:
                # Другая ошибка - пробрасываем ее
                raise
    
    raise TimeoutError(f"Не удалось получить ответ от сервера после {self._max_retries} попыток")


# Добавляем функции в глобальное пространство имен
init_func = RedisProxy._create_init()
init_func.__globals__['LazyProxy'] = LazyProxy
init_func.__globals__['_send_request'] = _send_request

# Добавляем метод _send_request к прокси-классу
setattr(RedisProxy, '_send_request', staticmethod(_send_request))


# Пример использования
if __name__ == "__main__":
    # Определяем тестовый класс
    class MyClass:
        def __init__(self, value):
            self.value = value
        
        def add(self, x):
            return self.value + x
        
        def get_value(self):
            return self.value
        
        def set_value(self, value):
            self.value = value
            
        def process_array(self, arr):
            if isinstance(arr, np.ndarray):
                return arr * self.value
            return None
        
        def raise_error(self):
            raise ValueError("Тестовая ошибка")
            
        class NestedClass:
            def __init__(self, parent):
                self.parent = parent
                
            def get_parent_value(self):
                return self.parent.value
                
    # Функция для запуска клиента
    def run_client():
        # Настраиваем логирование для клиентского процесса
        global logger
        logger = setup_logging('client')
        logger.info("Настроено логирование для клиентского процесса")
        
        # Создаем прокси-класс
        MyClassProxy = RedisProxy.create(MyClass)
        
        # Создаем экземпляр
        obj = MyClassProxy(10)
        
        # Вызываем методы
        print(f"obj.add(5) = {obj.add(5)}")
        print(f"obj.get_value() = {obj.get_value()}")
        
        # Устанавливаем атрибут
        obj.value = 20
        print(f"После obj.value = 20: obj.get_value() = {obj.get_value()}")
        
        # Работаем с numpy массивами
        arr = np.array([1, 2, 3, 4, 5])
        result = obj.process_array(arr)
        print(f"obj.process_array([1,2,3,4,5]) = {result}")
        
        # Вложенные атрибуты
        nested = obj.NestedClass(obj)
        print(f"nested.get_parent_value() = {nested.get_parent_value()}")
        
        # Обработка ошибок
        try:
            obj.raise_error()
        except Exception as e:
            print(f"Перехвачена ошибка: {e}")
            
    # Запускаем сервер в отдельном процессе
    import multiprocessing
    
    def start_server():
        # Эта функция будет запущена в отдельном процессе
        # Настраиваем логирование для серверного процесса
        server_logger = setup_logging('server')
        server_logger.info("Запуск серверного процесса")
        
        # Создаем сервер с автоматическим созданием экземпляров
        server = RedisProxyServer([MyClass], auto_create_instances=True)
    
    server_process = multiprocessing.Process(target=start_server)
    server_process.start()
    
    logger.info("Основной процесс: Сервер запущен в отдельном процессе")
    
    # Даем серверу время на инициализацию
    time.sleep(2)
    
    # Запускаем клиент
    logger.info("Основной процесс: Запускаем клиент")
    run_client()
    
    # Завершаем работу сервера
    logger.info("Основной процесс: Клиент завершил работу, останавливаем сервер")
    server_process.terminate()
    server_process.join()
    logger.info("Основной процесс: Сервер остановлен")
