from fastapi.templating import Jinja2Templates

ASSET_VERSION = "2.2.0"

templates = Jinja2Templates(directory="templates")
templates.env.globals["asset_version"] = ASSET_VERSION