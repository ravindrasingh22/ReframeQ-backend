from pydantic import BaseModel


class LanguageOption(BaseModel):
    code: str
    name: str
    enabled: bool


class SupportedLanguagesResponse(BaseModel):
    supported_languages: list[str]
    options: list[LanguageOption]


class UpdateSupportedLanguagesRequest(BaseModel):
    supported_languages: list[str]
