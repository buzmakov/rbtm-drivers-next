import redis
import pickle
import uuid
import time
import threading
import inspect
import functools

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
                    print(f"Error processing response: {e}")
    
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
                print(f"Initialization timed out, retrying ({retry_count}/{self.proxy.max_init_retries})...")
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
        # Check if it's a method or attribute
        return functools.partial(self._remote_call, name)
    
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
                raise Exception(response['exception'])
            
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
            print(f"Request timed out, reinitializing and retrying...")
            # Reinitialize the connection
            self.instance_id = str(uuid.uuid4())
            self._initialize()
            
            # Retry the original request with the new instance
            request_data['request_id'] = str(uuid.uuid4())
            request_data['instance_id'] = self.instance_id
            return self._send_request_and_wait(request_data, retry_on_timeout=False)
        
        raise TimeoutError(f"Request timed out after {self.proxy.timeout} seconds")


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
        
        print(f"Redis proxy server started, listening on channel {request_channel}")
        
        for message in self.pubsub.listen():
            if not self.running:
                break
                
            if message['type'] == 'message':
                try:
                    self._handle_request(message['data'])
                except Exception as e:
                    print(f"Error handling request: {e}")
    
    def stop(self):
        self.running = False
        self.pubsub.unsubscribe()
        print("Redis proxy server stopped")
    
    def _handle_request(self, data):
        request = pickle.loads(data)
        request_id = request.get('request_id')
        action = request.get('action')
        
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
                
                # Try to get the attribute
                attr = getattr(instance, method_name)
                
                # If it's callable, call it with the provided arguments
                if callable(attr):
                    result = attr(*args, **kwargs)
                else:
                    # It's a property/attribute
                    if args or kwargs:
                        # If we have args/kwargs, this is a property setter
                        setattr(instance, method_name, args[0] if args else kwargs.get('value'))
                        result = None
                    else:
                        # Otherwise it's a getter
                        result = attr
                
                response['result'] = result
                
            else:
                raise ValueError(f"Unknown action: {action}")
                
        except Exception as e:
            response['exception'] = str(e)
        
        # Send response
        response_channel = f"{self.channel_prefix}_response"
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
