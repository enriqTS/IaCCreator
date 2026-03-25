from fastapi import FastAPI

app = FastAPI(
    title="Terraform IaC Generator",
    description="Generates modular Terraform file structures from architecture descriptions",
    version="0.1.0",
)
