import asyncio
import logging
import time
from typing import List, Optional
from aiodocker import Docker

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
        allowed_containers: Optional[List[str]] = None,
    ) -> None:
        self._buffer = buffer
        self._docker = docker
        self._parser = parser
        self._allowed_containers = allowed_containers
        
        self._tasks: List[asyncio.Task] = []
        self._running = False

    async def _stream_container_logs(self, container, info: dict) -> None:
        container_name = info.get("Name", "").lstrip("/")
        logger.info(f"Встроенный коллектор подключился к логам контейнера: {container_name}")

        try:
            log_stream = container.log(stdout=True, stderr=True, follow=True)

            async for log_line in log_stream:
                if not self._running:
                    break

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
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Ошибка чтения логов контейнера {container_name}: {e}")

    async def start(self) -> None:
        logger.info("Запуск встроенного Docker Collector...")
        self._running = True

        containers = await self._docker.containers.list()

        for c in containers:
            info = await c.show()
            container_name = info.get("Name", "").lstrip("/")

            if self._allowed_containers and container_name not in self._allowed_containers:
                continue

            task = asyncio.create_task(self._stream_container_logs(c, info))
            self._tasks.append(task)

        logger.info(f"Collector запущен: {len(self._tasks)} потоков")
    
    async def stop(self) -> None:
        logger.info("Остановка встроенного Docker Collector...")
        self._running = False
        
        for task in self._tasks:
            if not task.done():
                task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()
            
        logger.info("Встроенный Docker Collector успешно остановлен")