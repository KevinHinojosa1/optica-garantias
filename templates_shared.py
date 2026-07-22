from fastapi.templating import Jinja2Templates

from config import LOGO_OFICIAL_PATH, settings

ASSET_VERSION = "2.7.3"

templates = Jinja2Templates(directory="templates")
templates.env.globals["asset_version"] = ASSET_VERSION
templates.env.globals["default_asesor"] = settings.default_asesor
templates.env.globals["logo_oficial_path"] = LOGO_OFICIAL_PATH