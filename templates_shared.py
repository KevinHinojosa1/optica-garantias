from fastapi.templating import Jinja2Templates

ASSET_VERSION = "1.2.4"

templates = Jinja2Templates(directory="templates")
templates.env.globals["asset_version"] = ASSET_VERSION