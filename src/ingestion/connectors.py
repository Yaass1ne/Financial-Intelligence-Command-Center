"""
FINCENTER Source Connectors — Multimodal Input Adapters

Architecture block: Sources Multimodales
Covers:
  - S3 / Kafka / API / SharePoint  (streaming + cloud storage)
  - Audio / Video / Images          (media parsers — OCR, transcription)
  - IoT / Logs                      (structured time-series + log ingestion)

Status:
  - File-based sources (PDF, Excel, JSON, CSV): IMPLEMENTED in parsers/
  - Cloud/streaming connectors below: STUB — ready for production wiring.
    Replace each _connect_* method body with the real SDK calls.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Iterator
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================
# Base Connector Interface
# ============================================

class BaseSourceConnector(ABC):
    """Abstract base for all multimodal source connectors."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the source. Returns True on success."""
        ...

    @abstractmethod
    def list_documents(self) -> List[Dict[str, Any]]:
        """List available documents/messages in the source."""
        ...

    @abstractmethod
    def fetch_document(self, doc_id: str) -> Optional[bytes]:
        """Fetch raw bytes of a single document."""
        ...

    def health_check(self) -> Dict[str, Any]:
        """Return connection health status."""
        try:
            ok = self.connect()
            return {"status": "ok" if ok else "unavailable", "connector": self.__class__.__name__}
        except Exception as e:
            return {"status": "error", "connector": self.__class__.__name__, "detail": str(e)}


# ============================================
# Cloud Storage — S3
# ============================================

class S3Connector(BaseSourceConnector):
    """
    Amazon S3 connector for financial document ingestion.
    Supports: PDF, Excel, JSON, CSV stored in S3 buckets.

    Production wiring:
        pip install boto3
        Replace stub body with boto3.client('s3') calls.
    """

    def __init__(self, bucket: str, prefix: str = "", region: str = "eu-west-1"):
        self.bucket = bucket
        self.prefix = prefix
        self.region = region
        self._client = None

    def connect(self) -> bool:
        try:
            import boto3  # type: ignore
            self._client = boto3.client("s3", region_name=self.region)
            self._client.head_bucket(Bucket=self.bucket)
            return True
        except ImportError:
            logger.warning("boto3 not installed — S3Connector unavailable")
            return False
        except Exception as e:
            logger.error(f"S3 connection failed: {e}")
            return False

    def list_documents(self) -> List[Dict[str, Any]]:
        if not self._client:
            return []
        try:
            paginator = self._client.get_paginator("list_objects_v2")
            docs = []
            for page in paginator.paginate(Bucket=self.bucket, Prefix=self.prefix):
                for obj in page.get("Contents", []):
                    docs.append({
                        "doc_id": obj["Key"],
                        "size_bytes": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat(),
                        "source": "s3",
                    })
            return docs
        except Exception as e:
            logger.error(f"S3 list_documents error: {e}")
            return []

    def fetch_document(self, doc_id: str) -> Optional[bytes]:
        if not self._client:
            return None
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=doc_id)
            return response["Body"].read()
        except Exception as e:
            logger.error(f"S3 fetch error for {doc_id}: {e}")
            return None


# ============================================
# Event Streaming — Kafka
# ============================================

class KafkaConnector(BaseSourceConnector):
    """
    Apache Kafka connector for real-time financial event streaming.
    Supports: invoice events, payment notifications, ERP change feeds.

    Production wiring:
        pip install confluent-kafka
        Replace stub with Consumer.poll() loop.
    """

    def __init__(self, bootstrap_servers: str, topic: str, group_id: str = "fincenter"):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self._consumer = None

    def connect(self) -> bool:
        try:
            from confluent_kafka import Consumer, KafkaError  # type: ignore
            self._consumer = Consumer({
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": self.group_id,
                "auto.offset.reset": "earliest",
            })
            self._consumer.subscribe([self.topic])
            return True
        except ImportError:
            logger.warning("confluent-kafka not installed — KafkaConnector unavailable")
            return False
        except Exception as e:
            logger.error(f"Kafka connection failed: {e}")
            return False

    def list_documents(self) -> List[Dict[str, Any]]:
        # Kafka doesn't support listing — use poll() to consume
        return []

    def fetch_document(self, doc_id: str) -> Optional[bytes]:
        # Not applicable for Kafka — use consume_batch() instead
        return None

    def consume_batch(self, max_messages: int = 100, timeout_ms: int = 5000) -> List[Dict[str, Any]]:
        """
        Poll Kafka for a batch of messages.

        Returns:
            List of message dicts with key, value (JSON decoded), timestamp
        """
        if not self._consumer:
            return []
        messages = []
        try:
            for _ in range(max_messages):
                msg = self._consumer.poll(timeout=timeout_ms / 1000)
                if msg is None:
                    break
                if msg.error():
                    logger.warning(f"Kafka error: {msg.error()}")
                    continue
                import json
                messages.append({
                    "key": msg.key().decode("utf-8") if msg.key() else None,
                    "value": json.loads(msg.value().decode("utf-8")),
                    "timestamp": msg.timestamp()[1],
                    "offset": msg.offset(),
                    "source": "kafka",
                })
        except Exception as e:
            logger.error(f"Kafka consume error: {e}")
        return messages


# ============================================
# SharePoint Connector
# ============================================

class SharePointConnector(BaseSourceConnector):
    """
    Microsoft SharePoint connector for enterprise document libraries.
    Supports: Word, Excel, PDF documents stored in SharePoint.

    Production wiring:
        pip install Office365-REST-Python-Client
    """

    def __init__(self, site_url: str, client_id: str, client_secret: str):
        self.site_url = site_url
        self.client_id = client_id
        self.client_secret = client_secret
        self._ctx = None

    def connect(self) -> bool:
        try:
            from office365.runtime.auth.client_credential import ClientCredential  # type: ignore
            from office365.sharepoint.client_context import ClientContext  # type: ignore
            credentials = ClientCredential(self.client_id, self.client_secret)
            self._ctx = ClientContext(self.site_url).with_credentials(credentials)
            self._ctx.load(self._ctx.web)
            self._ctx.execute_query()
            return True
        except ImportError:
            logger.warning("Office365 not installed — SharePointConnector unavailable")
            return False
        except Exception as e:
            logger.error(f"SharePoint connection failed: {e}")
            return False

    def list_documents(self) -> List[Dict[str, Any]]:
        # Stub — enumerate document library files
        return []

    def fetch_document(self, doc_id: str) -> Optional[bytes]:
        # Stub — download file by server-relative URL
        return None


# ============================================
# REST API Connector (ERP / Accounting systems)
# ============================================

class APIConnector(BaseSourceConnector):
    """
    Generic REST API connector for ERP / accounting system integration.
    Supports: SAP, Sage, QuickBooks, custom REST APIs.

    Production wiring: set base_url and auth headers.
    """

    def __init__(self, base_url: str, api_key: str = "", headers: Optional[Dict] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = headers or {}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def connect(self) -> bool:
        try:
            import requests  # type: ignore
            resp = requests.get(f"{self.base_url}/health", headers=self.headers, timeout=5)
            return resp.status_code < 400
        except Exception:
            return False

    def list_documents(self) -> List[Dict[str, Any]]:
        try:
            import requests  # type: ignore
            resp = requests.get(f"{self.base_url}/documents", headers=self.headers, timeout=10)
            return resp.json() if resp.ok else []
        except Exception:
            return []

    def fetch_document(self, doc_id: str) -> Optional[bytes]:
        try:
            import requests  # type: ignore
            resp = requests.get(f"{self.base_url}/documents/{doc_id}", headers=self.headers, timeout=30)
            return resp.content if resp.ok else None
        except Exception:
            return None


# ============================================
# IoT / Logs Connector
# ============================================

class IoTLogsConnector(BaseSourceConnector):
    """
    IoT and application log ingestion connector.
    Supports: structured JSON logs, CSV telemetry, time-series data.
    Source: local log files, syslog, or log aggregators (ELK, Loki).
    """

    def __init__(self, log_directory: str = "./logs", pattern: str = "*.log"):
        self.log_directory = Path(log_directory)
        self.pattern = pattern

    def connect(self) -> bool:
        return self.log_directory.exists()

    def list_documents(self) -> List[Dict[str, Any]]:
        if not self.log_directory.exists():
            return []
        docs = []
        for f in self.log_directory.glob(self.pattern):
            docs.append({
                "doc_id": str(f),
                "size_bytes": f.stat().st_size,
                "source": "iot_logs",
                "filename": f.name,
            })
        return docs

    def fetch_document(self, doc_id: str) -> Optional[bytes]:
        try:
            return Path(doc_id).read_bytes()
        except Exception:
            return None

    def stream_lines(self, doc_id: str) -> Iterator[str]:
        """Stream log file line by line (memory-efficient for large logs)."""
        try:
            with open(doc_id, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    yield line.rstrip()
        except Exception as e:
            logger.error(f"Log stream error for {doc_id}: {e}")


# ============================================
# Media Connector (Audio / Video / Images)
# ============================================

class MediaConnector(BaseSourceConnector):
    """
    Audio / Video / Image ingestion connector.
    - Images: OCR via Tesseract (extracts text from scanned invoices)
    - Audio: Transcription via Whisper (meeting notes, call recordings)
    - Video: Frame extraction + OCR (screen recordings of financial dashboards)

    Production wiring:
        pip install pytesseract pillow openai-whisper
    """

    SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
    SUPPORTED_AUDIO = {".mp3", ".wav", ".m4a", ".ogg"}
    SUPPORTED_VIDEO = {".mp4", ".avi", ".mov", ".mkv"}

    def __init__(self, media_directory: str = "./data/media"):
        self.media_directory = Path(media_directory)

    def connect(self) -> bool:
        return self.media_directory.exists()

    def list_documents(self) -> List[Dict[str, Any]]:
        if not self.media_directory.exists():
            return []
        all_ext = self.SUPPORTED_IMAGES | self.SUPPORTED_AUDIO | self.SUPPORTED_VIDEO
        docs = []
        for f in self.media_directory.rglob("*"):
            if f.suffix.lower() in all_ext:
                media_type = (
                    "image" if f.suffix.lower() in self.SUPPORTED_IMAGES
                    else "audio" if f.suffix.lower() in self.SUPPORTED_AUDIO
                    else "video"
                )
                docs.append({
                    "doc_id": str(f),
                    "media_type": media_type,
                    "filename": f.name,
                    "source": "media",
                })
        return docs

    def fetch_document(self, doc_id: str) -> Optional[bytes]:
        try:
            return Path(doc_id).read_bytes()
        except Exception:
            return None

    def extract_text_from_image(self, image_path: str) -> str:
        """OCR an image file and return extracted text."""
        try:
            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore
            img = Image.open(image_path)
            return pytesseract.image_to_string(img, lang="fra+eng")
        except ImportError:
            logger.warning("pytesseract/Pillow not installed — image OCR unavailable")
            return ""
        except Exception as e:
            logger.error(f"OCR error for {image_path}: {e}")
            return ""

    def transcribe_audio(self, audio_path: str, model_size: str = "base") -> str:
        """Transcribe an audio file to text using Whisper."""
        try:
            import whisper  # type: ignore
            model = whisper.load_model(model_size)
            result = model.transcribe(audio_path)
            return result.get("text", "")
        except ImportError:
            logger.warning("openai-whisper not installed — audio transcription unavailable")
            return ""
        except Exception as e:
            logger.error(f"Transcription error for {audio_path}: {e}")
            return ""


# ============================================
# Connector Registry
# ============================================

CONNECTOR_REGISTRY: Dict[str, type] = {
    "s3": S3Connector,
    "kafka": KafkaConnector,
    "sharepoint": SharePointConnector,
    "api": APIConnector,
    "iot_logs": IoTLogsConnector,
    "media": MediaConnector,
}


def get_connector(source_type: str, **kwargs) -> Optional[BaseSourceConnector]:
    """
    Factory function — instantiate a connector by type name.

    Args:
        source_type: One of 's3', 'kafka', 'sharepoint', 'api', 'iot_logs', 'media'
        **kwargs:    Passed to connector constructor

    Returns:
        Connector instance or None if type unknown
    """
    cls = CONNECTOR_REGISTRY.get(source_type)
    if cls is None:
        logger.error(f"Unknown connector type: {source_type}")
        return None
    return cls(**kwargs)
