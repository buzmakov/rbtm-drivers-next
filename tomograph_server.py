from drivers.Tomograph.Tomograph import HWTomograph
from experiment.redis_proxy import RedisProxyServer
# from experiment.tomologger import tomologger
import time
import sys

def main():
    print("Starting Tomograph RedisProxyServer...")
    
    # Создаем экземпляр сервера, который будет обслуживать класс HWTomograph
    server = RedisProxyServer(
        classes_to_serve=[HWTomograph],
        redis_host='redis',  # Используем имя сервиса из docker-compose
        redis_port=6379,
        redis_db=0,
        channel_prefix='tomograph_proxy'
    )
    
    try:
        # Запускаем сервер (блокирующий вызов)
        server.start()
    except KeyboardInterrupt:
        print("Shutting down server...")
        server.stop()
    except Exception as e:
        print(f"Error in server: {e}")
        # В случае ошибки завершаем процесс с кодом ошибки
        sys.exit(1)

if __name__ == "__main__":
    # В случае ошибки пытаемся перезапустить сервер
    while True:
        try:
            main()
        except Exception as e:
            print(f"Server crashed with error: {e}")
            print("Restarting in 5 seconds...")
            time.sleep(5)
