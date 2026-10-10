IMAGE_VERSION_PATTERN = r"^([A-Za-z0-9_][A-Za-z0-9_.-]{0,127}|sha256:[0-9a-f]{64})$"
REPOSITORY_PATTERN = (
    r"^[a-z0-9]+(([.]|_|__|-+)[a-z0-9]+)*(/[a-z0-9]+(([.]|_|__|-+)[a-z0-9]+)*)*$"
)
PRIVATE_ECR_PATTERN = r"^[0-9]{12}[.]dkr[.-]ecr[.-]"
