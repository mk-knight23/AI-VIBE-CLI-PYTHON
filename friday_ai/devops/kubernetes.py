"""Kubernetes client for DevOps operations."""

from dataclasses import dataclass
from typing import Optional, List, Dict
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class K8sConfig:
    """Kubernetes configuration."""

    kubeconfig: Optional[str] = None
    context: Optional[str] = None
    namespace: str = "default"


@dataclass
class PodInfo:
    """Information about a Kubernetes pod."""

    name: str
    namespace: str
    status: str
    ip: str
    node: str
    ready: bool
    restarts: int


@dataclass
class ServiceInfo:
    """Information about a Kubernetes service."""

    name: str
    namespace: str
    type: str
    cluster_ip: str
    ports: list[int]
    external_ip: Optional[str] = None


class K8sClient:
    """Kubernetes client for managing clusters."""

    def __init__(self, config: Optional[K8sConfig] = None):
        """Initialize the Kubernetes client.

        Args:
            config: K8s configuration.
        """
        self.config = config or K8sConfig()
        self._client = None
        self._available = False

    async def initialize(self) -> bool:
        """Initialize the Kubernetes client.

        Returns:
            True if initialization was successful.
        """
        try:
            from kubernetes import client, config

            # Load kubeconfig
            if self.config.kubeconfig:
                config.load_kube_config(self.config.kubeconfig)
            else:
                config.load_kube_config()

            self._client = client
            self._core_v1 = client.CoreV1Api()
            self._apps_v1 = client.AppsV1Api()
            self._networking_v1 = client.NetworkingV1Api()

            self._available = True
            logger.info("Kubernetes client initialized")
            return True

        except ImportError:
            logger.warning("kubernetes Python client not installed. K8s operations unavailable.")
            self._available = False
            return False
        except Exception as e:
            logger.error(f"Failed to initialize K8s client: {e}")
            self._available = False
            return False

    async def get_pods(self, namespace: Optional[str] = None) -> list[PodInfo]:
        """Get list of pods.

        Args:
            namespace: Kubernetes namespace.

        Returns:
            List of pod information.
        """
        if not self._available or not self._client:
            logger.warning("Kubernetes client not available")
            return []

        try:
            ns = namespace or self.config.namespace
            pods = self._core_v1.list_namespaced_pod(ns)

            return [
                PodInfo(
                    name=p.metadata.name,
                    namespace=p.metadata.namespace,
                    status=p.status.phase,
                    ip=p.status.pod_ip or "",
                    node=p.spec.node_name or "",
                    ready=p.status.conditions[0].status == "True" if p.status.conditions else False,
                    restarts=sum(
                        c.restart_count or 0
                        for c in p.status.container_statuses or []
                    ),
                )
                for p in pods.items
            ]

        except Exception as e:
            logger.error(f"Failed to get pods: {e}")
            return []

    async def get_services(self, namespace: Optional[str] = None) -> list[ServiceInfo]:
        """Get list of services.

        Args:
            namespace: Kubernetes namespace.

        Returns:
            List of service information.
        """
        if not self._available or not self._client:
            logger.warning("Kubernetes client not available")
            return []

        try:
            ns = namespace or self.config.namespace
            services = self._core_v1.list_namespaced_service(ns)

            return [
                ServiceInfo(
                    name=s.metadata.name,
                    namespace=s.metadata.namespace,
                    type=s.spec.type,
                    cluster_ip=s.spec.cluster_ip or "",
                    ports=[p.port for p in s.spec.ports or []],
                    external_ip=s.status.load_balancer.ingress[0].ip if s.status.load_balancer else None,
                )
                for s in services.items
            ]

        except Exception as e:
            logger.error(f"Failed to get services: {e}")
            return []

    async def scale_deployment(
        self,
        name: str,
        replicas: int,
        namespace: Optional[str] = None,
    ) -> bool:
        """Scale a deployment.

        Args:
            name: Deployment name.
            replicas: Number of replicas.
            namespace: Kubernetes namespace.

        Returns:
            True if successful.
        """
        if not self._available or not self._client:
            logger.warning("Kubernetes client not available")
            return False

        try:
            ns = namespace or self.config.namespace

            # Get the deployment
            deployment = self._apps_v1.read_namespaced_deployment(name, ns)

            # Update replicas
            deployment.spec.replicas = replicas

            # Apply the update
            self._apps_v1.patch_namespaced_deployment(name, ns, deployment)

            logger.info(f"Scaled deployment {name} to {replicas} replicas")
            return True

        except Exception as e:
            logger.error(f"Failed to scale deployment: {e}")
            return False

    async def restart_deployment(
        self,
        name: str,
        namespace: Optional[str] = None,
    ) -> bool:
        """Restart a deployment by rolling restart.

        Args:
            name: Deployment name.
            namespace: Kubernetes namespace.

        Returns:
            True if successful.
        """
        if not self._available or not self._client:
            logger.warning("Kubernetes client not available")
            return False

        try:
            ns = namespace or self.config.namespace

            # Do a rolling restart by patching with empty annotation
            body = {"spec": {"template": {"metadata": {"annotations": {"kubectl.kubernetes.io/restartedAt": str}}}}}
            self._apps_v1.patch_namespaced_deployment(name, ns, body)

            logger.info(f"Restarted deployment {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to restart deployment: {e}")
            return False

    async def get_deployments(self, namespace: Optional[str] = None) -> list[dict]:
        """Get list of deployments.

        Args:
            namespace: Kubernetes namespace.

        Returns:
            List of deployment information.
        """
        if not self._available or not self._client:
            logger.warning("Kubernetes client not available")
            return []

        try:
            ns = namespace or self.config.namespace
            deploys = self._apps_v1.list_namespaced_deployment(ns)

            return [
                {
                    "name": d.metadata.name,
                    "replicas": d.spec.replicas or 0,
                    "ready_replicas": d.status.ready_replicas or 0,
                    "available_replicas": d.status.available_replicas or 0,
                }
                for d in deploys.items
            ]

        except Exception as e:
            logger.error(f"Failed to get deployments: {e}")
            return []

    async def apply_yaml(self, yaml_content: str) -> bool:
        """Apply a YAML manifest.

        Args:
            yaml_content: YAML content to apply.

        Returns:
            True if successful.
        """
        if not self._available or not self._client:
            logger.warning("Kubernetes client not available")
            return False

        try:
            from kubernetes.client.api import core_v1_api

            # Use dynamic client for generic apply
            from kubernetes import client, config

            # Load YAML
            import yaml

            docs = list(yaml.safe_load_all(yaml_content))

            for doc in docs:
                if not doc:
                    continue

                kind = doc.get("kind")
                name = doc.get("metadata", {}).get("name")
                namespace = doc.get("metadata", {}).get("namespace", self.config.namespace)

                if kind == "Pod":
                    self._core_v1.create_namespaced_pod(namespace, doc)
                elif kind == "Service":
                    self._core_v1.create_namespaced_service(namespace, doc)
                elif kind == "Deployment":
                    self._apps_v1.create_namespaced_deployment(namespace, doc)

                logger.info(f"Applied {kind}: {name}")

            return True

        except Exception as e:
            logger.error(f"Failed to apply YAML: {e}")
            return False

    async def get_logs(
        self,
        pod_name: str,
        namespace: str = "default",
        container: Optional[str] = None,
        tail_lines: int = 100,
    ) -> str:
        """Get logs from a pod.

        Args:
            pod_name: Pod name.
            namespace: Kubernetes namespace.
            container: Container name.
            tail_lines: Number of lines to tail.

        Returns:
            Log content.
        """
        if not self._client:
            return "Kubernetes client not available"

        try:
            kwargs = {"name": pod_name, "namespace": namespace, "tail_lines": tail_lines}
            if container:
                kwargs["container"] = container

            logs = self._core_v1.read_namespaced_pod_log(**kwargs)
            return logs

        except Exception as e:
            logger.error(f"Failed to get logs: {e}")
            return f"Error getting logs: {str(e)}"

    async def describe_resource(
        self,
        resource_type: str,
        name: str,
        namespace: str = "default",
    ) -> str:
        """Describe a resource.

        Args:
            resource_type: Type of resource (pod, deployment, service, etc.).
            name: Resource name.
            namespace: Kubernetes namespace.

        Returns:
            Description string.
        """
        if not self._client:
            return "Kubernetes client not available"

        try:
            if resource_type == "pod":
                resp = self._client.read_namespaced_pod(name, namespace)
                return str(resp)
            elif resource_type == "deployment":
                resp = self._apps_v1.read_namespaced_deployment(name, namespace)
                return str(resp)
            elif resource_type == "service":
                resp = self._client.read_namespaced_service(name, namespace)
                return str(resp)
            else:
                return f"Unknown resource type: {resource_type}"

        except Exception as e:
            logger.error(f"Failed to describe resource: {e}")
            return f"Error: {str(e)}"

    def get_cluster_info(self) -> dict:
        """Get cluster information.

        Returns:
            Cluster info dictionary.
        """
        if not self._available or not self._client:
            return {"error": "Client not initialized", "available": False}

        try:
            info = self._client.ApiClient().call_api(
                "/apis/apps/v1",
                method="GET",
            )
            return {"status": "connected", "api_version": "v1"}
        except Exception as e:
            return {"error": str(e)}
