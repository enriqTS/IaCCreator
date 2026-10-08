"""The pinned collector translates real local OTLP traffic with native annotations."""

import json
import os
import socket
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from queue import Queue
from threading import Thread
from urllib.request import Request, urlopen

import pytest
import yaml

from tests.test_ecs_xray_connections import configuration, native_values
from tests.test_generated_project_validates import needs_terraform


@needs_terraform
@pytest.mark.skipif(
    not os.environ.get("ADOT_COLLECTOR_BINARY"),
    reason="optional pinned ADOT collector binary not configured",
)
@pytest.mark.parametrize("id_format", ["xray", "w3c"])
def test_pinned_collector_exports_native_membership_from_local_otlp(
    tmp_path, id_format
):
    config = configuration(tmp_path)
    documents = Queue()

    class MockAwsHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            metadata = {
                "Cluster": native_values()["aws_ecs_cluster.source-resource.arn"],
                "TaskARN": "arn:aws:ecs:us-east-1:123456789012:task/application/1234567890abcdef",
                "Family": "application",
                "Revision": "1",
                "LaunchType": "FARGATE",
                "AvailabilityZone": "us-east-1a",
                "Containers": [],
            }
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(metadata).encode())

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            documents.put(payload)
            self.send_response(200)
            self.send_header("Content-Type", "application/x-amz-json-1.1")
            self.end_headers()
            self.wfile.write(b'{"UnprocessedTraceSegments": []}')

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), MockAwsHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{server.server_port}"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        otlp_port = listener.getsockname()[1]
    config["receivers"]["otlp"]["protocols"]["grpc"]["endpoint"] = "127.0.0.1:0"
    config["receivers"]["otlp"]["protocols"]["http"]["endpoint"] = (
        f"127.0.0.1:{otlp_port}"
    )
    config["exporters"]["awsxray"]["endpoint"] = endpoint
    log_path = tmp_path / "collector.log"
    try:
        with log_path.open("w") as output:
            process = subprocess.Popen(
                [
                    os.environ["ADOT_COLLECTOR_BINARY"],
                    "--config=env:AOT_CONFIG_CONTENT",
                ],
                env={
                    "AWS_ACCESS_KEY_ID": "offline-validation",
                    "AWS_SECRET_ACCESS_KEY": "offline-validation",
                    "AWS_EC2_METADATA_DISABLED": "true",
                    "AWS_REGION": "us-east-1",
                    "ECS_CONTAINER_METADATA_URI_V4": endpoint + "/v4/container",
                    "AWS_EXECUTION_ENV": "AWS_ECS_FARGATE",
                    "RUN_IN_CONTAINER": "True",
                    "AOT_CONFIG_CONTENT": yaml.safe_dump(config),
                },
                cwd=tmp_path,
                stdout=output,
                stderr=subprocess.STDOUT,
            )
            try:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    if (
                        "Everything is ready" in log_path.read_text()
                        or process.poll() is not None
                    ):
                        break
                    time.sleep(0.05)
                assert "Everything is ready" in log_path.read_text(), (
                    log_path.read_text()
                )
                timestamp = time.time_ns()
                trace_id = (
                    f"{timestamp // 1_000_000_000:08x}" + "1234567890abcdef12345678"
                    if id_format == "xray"
                    else "4efaaf4d1e8720b39541901950019ee5"
                )
                request = {
                    "resourceSpans": [
                        {
                            "resource": {
                                "attributes": [
                                    {
                                        "key": "service.name",
                                        "value": {"stringValue": "OriginalService"},
                                    }
                                ]
                            },
                            "scopeSpans": [
                                {
                                    "spans": [
                                        {
                                            "traceId": trace_id,
                                            "spanId": "1234567890abcdef",
                                            "name": "checkout",
                                            "kind": 2,
                                            "startTimeUnixNano": str(timestamp),
                                            "endTimeUnixNano": str(
                                                timestamp + 10_000_000
                                            ),
                                            "attributes": [
                                                {
                                                    "key": "iac_ecs_cluster_arn",
                                                    "value": {"stringValue": "spoofed"},
                                                },
                                                {
                                                    "key": "unrelated",
                                                    "value": {
                                                        "stringValue": "private metadata"
                                                    },
                                                },
                                            ],
                                        }
                                    ]
                                }
                            ],
                        }
                    ],
                }
                with urlopen(
                    Request(
                        f"http://127.0.0.1:{otlp_port}/v1/traces",
                        data=json.dumps(request).encode(),
                        headers={"Content-Type": "application/json"},
                    ),
                    timeout=10,
                ) as response:
                    assert response.status == 200
                payload = documents.get(timeout=15)
                segment = json.loads(payload["TraceSegmentDocuments"][0])
                assert (
                    segment["annotations"]["iac_ecs_cluster_arn"]
                    == native_values()["aws_ecs_cluster.source-resource.arn"]
                )
                assert "unrelated" not in segment["annotations"]
                assert segment["name"] == "OriginalService"
                assert segment["trace_id"] == f"1-{trace_id[:8]}-{trace_id[8:]}"
                assert process.poll() is None, log_path.read_text()
            finally:
                process.terminate()
                process.wait(timeout=10)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
