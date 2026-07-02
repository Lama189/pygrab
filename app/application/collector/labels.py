from typing import Any, Dict


class DockerLabelsExtractor:
    
    @staticmethod
    def extract(container_info: Dict[str, Any], stream_name: str) -> Dict[str, str]:
        config = container_info.get("Config", {})
        docker_labels = config.get("Labels", {})

        container_name = container_info.get("Name", "").lstrip("/")
        image_name = config.get("Image", "")

        compose_project = docker_labels.get("com.docker.compose.project", "default")
        compose_service = docker_labels.get("com.docker.compose.service", container_name)

        return {
            "container_name": container_name,
            "image": image_name,
            "compose_project": compose_project,
            "compose_service": compose_service,
            "stream": stream_name,
            "service": compose_service
        }