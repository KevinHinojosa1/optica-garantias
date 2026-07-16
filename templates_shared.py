from fastapi.templating import Jinja2Templates

from config import settings

ASSET_VERSION = "2.3.1"
LOGO_OFICIAL_PATH = "static/img/logo-optica-los-andes.png"

templates = Jinja2Templates(directory="templates")
templates.env.globals["asset_version"] = ASSET_VERSION
templates.env.globals["default_asesor"] = settings.default_asesor
templates.env.globals["logo_oficial_path"] = LOGO_OFICIAL_PATH