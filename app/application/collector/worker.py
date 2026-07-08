import asyncio
import logging
import time
from aiodocker import Docker

from app.core.config import DockerConfig
from app.domain.models import LogEntry
from app.application.collector.parser import LogParser
from app.application.collector.labels import DockerLabelsExtractor
from app.application.logs.buffer import LogBuffer

logger = logging.getLogger(__name__)


class DockerLogsCollector:
    def __init__(
        self, 
        buffer: LogBuffer,
        docker: Docker,
        parser: LogParser,
        config: DockerConfig,
    ) -> None:
        self._buffer = buffer
        self._docker = docker
        self._parser = parser
        self._config = config
        
        self._tasks: dict[str, asyncio.Task] = {}
        self._running = False
        self._events_task: asyncio.Task | None = None

    def _is_allowed(self, container_name: str) -> bool:
        if self._config.docker_containers is None:
            return True
        return container_name in self._config.docker_containers

    async def _stream_container_logs(self, container, info: dict) -> None:
        container_name = info.get("Name", "").lstrip("/")

        retries = 0
        while self._running and retries < self._config.collector_max_retries:
            try:
                logger.info(f"Подключение к логам контейнера: {container_name}")
                log_stream = container.log(stdout=True, stderr=True, follow=True)

                async for log_line in log_stream:
                    if not self._running:
                        return

                    raw_text = str(log_line)
                    stream_name = "stdout"
                    
                    if raw_text.startswith("stdout: "):
                        message_text = raw_text[8:]
                    elif raw_text.startswith("stderr: "):
                        stream_name = "stderr"
                        message_text = raw_text[8:]
                    else:
                        message_text = raw_text
                    
                    message_text = message_text.strip()
                    if not message_text:
                        continue

                    labels = DockerLabelsExtractor.extract(info, stream_name)
                    level = self._parser.parse_level(message_text)
                    entry = LogEntry(
                        timestamp=time.time_ns(),
                        level=level,
                        message=message_text,
                        labels=labels,
                        trace_id=None,
                        span_id=None,
                    )
                    await self._buffer.add(entry)

                logger.info(f"Поток логов контейнера {container_name} завершён (сервер закрыл соединение)")
                return

            except asyncio.CancelledError:
                return
            except Exception as e:
                retries += 1
                delay = min(self._config.collector_base_delay * (2 ** (retries - 1)), self._config.collector_max_delay)
                logger.warning(
                    f"Ошибка чтения логов контейнера {container_name} "
                    f"(попытка {retries}/{self._config.collector_max_retries}): {e}. "
                    f"Повтор через {delay:.1f}с"
                )
                await asyncio.sleep(delay)

        if retries >= self._config.collector_max_retries:
            logger.error(f"Контейнер {container_name}: исчерпаны попытки переподключения ({self._config.collector_max_retries})")

    async def _subscribe_container(self, container_id: str) -> None:
        if container_id in self._tasks:
            return

        try:
            container = self._docker.containers.container(container_id)
            info = await container.show()
            container_name = info.get("Name", "").lstrip("/")

            if not self._is_allowed(container_name):
                return

            task = asyncio.create_task(self._stream_container_logs(container, info))
            self._tasks[container_id] = task
            task.add_done_callback(lambda t, cid=container_id: self._on_task_done(cid, t))

        except Exception as e:
            logger.error(f"Не удалось подписаться на контейнер {container_id}: {e}")

    def _on_task_done(self, container_id: str, task: asyncio.Task) -> None:
        self._tasks.pop(container_id, None)
        if self._running and not task.cancelled():
            logger.info(f"Таск для контейнера {container_id} завершён, переподключение...")

    async def _listen_events(self) -> None:
        events = self._docker.events
        subscriber = events.subscribe()
        try:
            while self._running:
                event = await subscriber.get()
                if event is None:
                    break

                attrs = event.get("Actor", {}).get("Attributes", {})
                container_id = attrs.get("name", "")
                event_type = event.get("Type", "")
                action = event.get("Action", "")

                if event_type != "container" or not container_id:
                    continue

                if action == "start":
                    logger.info(f"Обнаружен запущенный контейнер: {container_id}")
                    await self._subscribe_container(container_id)

                elif action in ("die", "stop", "kill", "destroy"):
                    task = self._tasks.pop(container_id, None)
                    if task and not task.done():
                        task.cancel()
                        logger.info(f"Остановлен таск для контейнера {container_id} (action={action})")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Ошибка event listener: {e}")

    async def start(self) -> None:
        logger.info("Запуск встроенного Docker Collector...")
        self._running = True

        containers = await self._docker.containers.list()
        for c in containers:
            info = await c.show()
            container_id = info.get("Id", "")
            if container_id:
                await self._subscribe_container(container_id)

        self._events_task = asyncio.create_task(self._listen_events())

        logger.info(f"Collector запущен: {len(self._tasks)} потоков + event listener")
    
    async def stop(self) -> None:
        logger.info("Остановка встроенного Docker Collector...")
        self._running = False
        
        if self._events_task and not self._events_task.done():
            self._events_task.cancel()

        for task in list(self._tasks.values()):
            if not task.done():
                task.cancel()

        all_tasks = list(self._tasks.values())
        if self._events_task:
            all_tasks.append(self._events_task)

        if all_tasks:
            await asyncio.gather(*all_tasks, return_exceptions=True)
            self._tasks.clear()
            
        logger.info("Встроенный Docker Collector успешно остановлен")
