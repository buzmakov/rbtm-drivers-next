import redis
import pickle
import uuid
import time
import threading
import inspect
import functools
import logging

# Настройка логгера
logger = logging.getLogger('redis_proxy')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class RedisProxy:
    def __init__(self, target_class, redis_host='localhost', redis_port=6379, redis_db=0, 
                 channel_prefix='redis_proxy', timeout=15, max_init_retries=3):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        self.channel_prefix = channel_prefix
        self.timeout = timeout
        self.target_class = target_class
        self.response_cache = {}
        self.lock = threading.Lock()
        self.max_init_retries = max_init_retries
        
        # Subscribe to response channel
        self.pubsub = self.redis_client.pubsub()
        self.response_channel = f"{self.channel_prefix}_response"
        self.pubsub.subscribe(self.response_channel)
        
        # Start listener thread
        self.listener_thread = threading.Thread(target=self._listen_for_responses, daemon=True)
        self.listener_thread.start()
    
    def _listen_for_responses(self):
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = pickle.loads(message['data'])
                    request_id = data.get('request_id')
                    if request_id in self.response_cache:
                        with self.lock:
                            self.response_cache[request_id] = data
                except Exception as e:
                    logger.error(f"Error processing response: {e}")
    
    def __call__(self, *args, **kwargs):
        # Create a new instance of the proxy
        instance = RedisProxyInstance(self, *args, **kwargs)
        return instance


class RedisProxyInstance:
    def __init__(self, proxy, *args, **kwargs):
        self.proxy = proxy
        self.instance_id = str(uuid.uuid4())
        self.init_args = args
        self.init_kwargs = kwargs
        
        # Send initialization request with retries
        retry_count = 0
        while retry_count < self.proxy.max_init_retries:
            try:
                self._initialize()
                break  # Successful initialization
            except TimeoutError:
                retry_count += 1
                if retry_count >= self.proxy.max_init_retries:
                    raise TimeoutError(f"Failed to initialize after {self.proxy.max_init_retries} attempts")
                logger.warning(f"Initialization timed out, retrying ({retry_count}/{self.proxy.max_init_retries})...")
                self.instance_id = str(uuid.uuid4())  # Generate new instance ID for retry
    
    def _initialize(self):
        request_data = {
            'request_id': str(uuid.uuid4()),
            'action': 'create',
            'instance_id': self.instance_id,
            'class_name': self.proxy.target_class.__name__,
            'args': self.init_args,
            'kwargs': self.init_kwargs
        }
        
        # For initialization, we don't want to retry within _send_request_and_wait
        # because we're already handling retries at the initialization level
        self._send_request_and_wait(request_data, retry_on_timeout=False)
    
    def __getattr__(self, name):
        # Create a special handler that can be both called as a method
        # and accessed as an attribute
        attr_handler = AttributeMethodHandler(self, name)
        return attr_handler
    
    def _remote_call(self, name, *args, **kwargs):
        request_id = str(uuid.uuid4())
        
        request_data = {
            'request_id': request_id,
            'action': 'call',
            'instance_id': self.instance_id,
            'method_name': name,
            'args': args,
            'kwargs': kwargs
        }
        
        try:
            response = self._send_request_and_wait(request_data)
            
            if 'exception' in response:
                exception_info = response['exception']
                if isinstance(exception_info, dict) and 'type' in exception_info and 'message' in exception_info:
                    # Получаем класс исключения по имени
                    exception_type = exception_info['type']
                    exception_message = exception_info['message']
                    
                    # Пытаемся найти класс исключения в стандартных модулях
                    exception_class = None
                    for module_name in ['builtins', 'exceptions']:
                        try:
                            module = __import__(module_name, fromlist=[exception_type])
                            if hasattr(module, exception_type):
                                exception_class = getattr(module, exception_type)
                                break
                        except (ImportError, AttributeError):
                            pass
                    
                    # Если нашли класс исключения, создаем его экземпляр
                    if exception_class and issubclass(exception_class, Exception):
                        raise exception_class(exception_message)
                
                # Если не удалось воссоздать оригинальное исключение, используем общее
                raise Exception(str(exception_info))
            
            return response.get('result')
        except TimeoutError:
            # If we get here, it means the retry also failed
            raise
    
    def _send_request_and_wait(self, request_data, retry_on_timeout=True):
        request_id = request_data['request_id']
        
        # Register in response cache
        with self.proxy.lock:
            self.proxy.response_cache[request_id] = None
        
        # Serialize and send the request
        request_channel = f"{self.proxy.channel_prefix}_request"
        logger.debug(f"Sending request: {request_data}")
        self.proxy.redis_client.publish(request_channel, pickle.dumps(request_data))
        
        # Wait for response
        start_time = time.time()
        while time.time() - start_time < self.proxy.timeout:
            with self.proxy.lock:
                response = self.proxy.response_cache.get(request_id)
                if response is not None:
                    del self.proxy.response_cache[request_id]
                    return response
            time.sleep(0.01)
        
        # Timeout occurred
        with self.proxy.lock:
            if request_id in self.proxy.response_cache:
                del self.proxy.response_cache[request_id]
        
        if retry_on_timeout and request_data['action'] != 'create':
            logger.warning(f"Request timed out, reinitializing and retrying...")
            # Reinitialize the connection
            self.instance_id = str(uuid.uuid4())
            self._initialize()
            
            # Retry the original request with the new instance
            request_data['request_id'] = str(uuid.uuid4())
            request_data['instance_id'] = self.instance_id
            return self._send_request_and_wait(request_data, retry_on_timeout=False)
        
        raise TimeoutError(f"Request timed out after {self.proxy.timeout} seconds")


class AttributeMethodHandler:
    def __init__(self, proxy_instance, attr_name):
        self.proxy_instance = proxy_instance
        self.attr_name = attr_name
    
    def __call__(self, *args, **kwargs):
        # When called as a method
        return self.proxy_instance._remote_call(self.attr_name, *args, **kwargs)
    
    def __repr__(self):
        # When accessed as an attribute (get)
        return repr(self.proxy_instance._remote_call(self.attr_name))
        
    def __getattr__(self, name):
        # Support nested attribute access (e.g., obj.x.shape)
        # First get the attribute value
        attr_value = self.proxy_instance._remote_call(self.attr_name)
        # Then access the nested attribute
        return getattr(attr_value, name)


class RedisProxyServer:
    def __init__(self, classes_to_serve, redis_host='localhost', redis_port=6379, redis_db=0, 
                 channel_prefix='redis_proxy'):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        self.channel_prefix = channel_prefix
        self.classes_to_serve = {cls.__name__: cls for cls in classes_to_serve}
        self.instances = {}
        self.running = False
    
    def start(self):
        self.running = True
        self.pubsub = self.redis_client.pubsub()
        request_channel = f"{self.channel_prefix}_request"
        self.pubsub.subscribe(request_channel)
        
        logger.info(f"Redis proxy server started, listening on channel {request_channel}")
        
        for message in self.pubsub.listen():
            if not self.running:
                break
                
            if message['type'] == 'message':
                try:
                    self._handle_request(message['data'])
                except Exception as e:
                    logger.error(f"Error handling request: {e}")
    
    def stop(self):
        self.running = False
        self.pubsub.unsubscribe()
        logger.info("Redis proxy server stopped")
    
    def _handle_request(self, data):
        request = pickle.loads(data)
        request_id = request.get('request_id')
        action = request.get('action')
        
        logger.debug(f"Received request: {request}")
        response = {'request_id': request_id}
        
        try:
            if action == 'create':
                instance_id = request.get('instance_id')
                class_name = request.get('class_name')
                args = request.get('args', ())
                kwargs = request.get('kwargs', {})
                
                if class_name not in self.classes_to_serve:
                    raise ValueError(f"Class {class_name} is not available on the server")
                
                instance = self.classes_to_serve[class_name](*args, **kwargs)
                self.instances[instance_id] = instance
                response['result'] = 'instance_created'
                
            elif action == 'call':
                instance_id = request.get('instance_id')
                method_name = request.get('method_name')
                args = request.get('args', ())
                kwargs = request.get('kwargs', {})
                
                if instance_id not in self.instances:
                    raise ValueError(f"Instance {instance_id} does not exist")
                
                instance = self.instances[instance_id]
                
                # If no args and kwargs, it might be an attribute access
                if not args and not kwargs:
                    try:
                        # Try to get the attribute
                        result = getattr(instance, method_name)
                        # Make sure the result is serializable
                        try:
                            pickle.dumps(result)
                        except (pickle.PickleError, TypeError):
                            # If not serializable, convert to a string representation
                            result = str(result)
                    except AttributeError:
                        # If attribute doesn't exist, try to call a method with no args
                        method = getattr(instance, method_name)
                        result = method()
                else:
                    # Try to get the attribute
                    attr = getattr(instance, method_name)
                    
                    # If it's callable, call it with the provided arguments
                    if callable(attr):
                        result = attr(*args, **kwargs)
                    else:
                        # It's a property/attribute and we're trying to set it
                        setattr(instance, method_name, args[0] if args else kwargs.get('value'))
                        result = None
                
                # Ensure the result is serializable
                try:
                    pickle.dumps(result)
                except (pickle.PickleError, TypeError):
                    # If not serializable, convert to a string or dict representation
                    if hasattr(result, '__dict__'):
                        result = {k: str(v) for k, v in result.__dict__.items()}
                    else:
                        result = str(result)
                
                response['result'] = result
                
            else:
                raise ValueError(f"Unknown action: {action}")
                
        except Exception as e:
            # Сохраняем информацию об исключении, включая его тип
            exception_type = type(e).__name__
            exception_message = str(e)
            response['exception'] = {
                'type': exception_type,
                'message': exception_message
            }
            logger.error(f"Exception in request handler: {exception_type}: {exception_message}")
        
        # Send response
        response_channel = f"{self.channel_prefix}_response"
        logger.debug(f"Sending response: {response}")
        self.redis_client.publish(response_channel, pickle.dumps(response))


# Example usage:

# On server side:
# class MyClass:
#     def __init__(self, value):
#         self.value = value
#     
#     def add(self, x):
#         return self.value + x
#     
#     def get_value(self):
#         return self.value
#
# server = RedisProxyServer([MyClass])
# server.start()

# On client side:
# MyClassProxy = RedisProxy(MyClass)
# obj = MyClassProxy(10)
# result = obj.add(5)  # Returns 15
# value = obj.get_value()  # Returns 10
