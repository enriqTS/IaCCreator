"""Resolved Cognito authentication for one load-balancer listener."""

from dataclasses import dataclass
from hashlib import sha256

from app.models.connection_configs.cognito_load_balancer import (
    CognitoLoadBalancerConfig,
)


@dataclass(frozen=True)
class CognitoListenerBinding:
    pool_name: str
    target_group_name: str
    config: CognitoLoadBalancerConfig

    @property
    def client_resource(self) -> str:
        return f"cognito_{self.pool_name}_{self.config.listener_port}_client"

    @property
    def callback_url(self) -> str:
        port = (
            "" if self.config.listener_port == 443 else f":{self.config.listener_port}"
        )
        return f"https://{self.config.application_hostname}{port}/oauth2/idpresponse"

    def cookie_name(self, load_balancer_name: str) -> str:
        identity = f"{load_balancer_name}:{self.pool_name}:{self.config.listener_port}"
        return f"IaCAuth{sha256(identity.encode()).hexdigest()[:20]}"
