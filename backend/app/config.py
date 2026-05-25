from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o"
    MAX_UPLOAD_MB: int = 100

    B2_ENDPOINT: str = Field(
        default="https://s3.us-east-005.backblazeb2.com",
        validation_alias="backblazebucketendpoint",
    )
    B2_KEY_ID: str = Field(default="", validation_alias="backblazekeyid")
    B2_APP_KEY: str = Field(default="", validation_alias="backblazeapplicationkey")
    B2_BUCKET_NAME: str = Field(default="vectorlessrag", validation_alias="backblazebucketname")
    B2_REGION: str = Field(default="us-east-005", validation_alias="backblazeregion")

    CLERK_JWKS_URL: str = ""
    CLERK_SECRET_KEY: str = ""

    DATABASE_URL: str

    REDIS_URL: str = "redis://localhost:6379"

    ALLOWED_ORIGINS: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
